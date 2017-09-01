import discord
import re
import json
import database as db
import columnmaker
import emoji
import random as rand
from datetime import datetime, timedelta
from lan import delta_to_tuple
from time_util import as_helsinki, as_utc, to_utc, to_helsinki
from awards import CUSTOM_TROPHY_NAMES, get_custom_trophy_conditions

playinglist = []

def sanitize_message(content, mentions):
    for m in mentions:
        content = content.replace("<@%s>" % m["id"], "@%s" % m["username"])
    return content

async def send_quote(client, channel, random_message):
    content, timestamp, mentions, user_id, name, avatar = random_message
    mentions = json.loads(mentions)
    sanitized = sanitize_message(content, mentions)
    avatar_url = "https://cdn.discordapp.com/avatars/{user_id}/{avatar}.jpg".format(user_id=user_id, avatar=avatar)

    embed = discord.Embed(description=sanitized)
    embed.set_author(name=name, icon_url=avatar_url)
    embed.set_footer(text=str(timestamp))
    await client.send_message(channel, embed=embed)

async def random_message_with_filter(filters, params):
    return await db.fetchrow("""
        SELECT
            content,
            ts::timestamptz AT TIME ZONE 'Europe/Helsinki',
            m->'mentions',
            user_id,
            name,
            m->'author'->>'avatar' as avatar
        FROM 
            message 
        JOIN 
            discord_user USING (user_id)
        WHERE 
            length(content) > 6 
            AND content NOT LIKE '!%%' 
            AND NOT bot 
            {filters} 
            AND NOT EXISTS (SELECT * FROM excluded_users WHERE excluded_user_id = user_id)
        ORDER BY 
            random() LIMIT 1
    """.format(filters=filters), *params)


async def getblackjacktoplist():
    items = await db.fetch("""
        SELECT
            (wins_bj / (wins_bj + losses_bj)) * 100,
            wins_bj,
            wins_bj + losses_bj,
            name,
            losses_bj,
            surrenders,
            ties,
            moneyspent_bj,
            moneywon_bj,
            concat('#', row_number() OVER (ORDER BY  (wins_bj / (wins_bj + losses_bj)) * 100 desc)) AS rank
        FROM casino_stats
        JOIN discord_user USING (user_id)
        WHERE (wins_bj + losses_bj) > 1
        ORDER BY (wins_bj / (wins_bj + losses_bj)) * 100 DESC
        LIMIT 10
    """)
    if len(items) == 0:
        return None, None
    toplist = []
    for item in items:
        pct, wins, total, name, losses, surrenders, ties, moneyspent, moneywon, rank = item
        new_item = (name[0:10], rank, total, wins, losses, surrenders, ties, moneyspent, round(moneywon), round(pct, 3))
        toplist.append(new_item)
    # toplist = addsymboltolist(toplist,9,' %')
    return columnmaker.columnmaker(['NAME', 'RANK', 'TOT', 'W', 'L', 'S', 'T', '$ SPENT', '$ WON', '%'], toplist), len(toplist)

async def getslotstoplist():
    items = await db.fetch("""
        SELECT
            name,
            concat('#', row_number() OVER (ORDER BY  (wins_slots / (wins_slots + losses_slots)) * 100 desc)) AS rank,
            wins_slots + losses_slots,
            wins_slots,
            losses_slots,
            moneyspent_slots,
            moneywon_slots,
            (wins_slots / (wins_slots + losses_slots)) * 100
        FROM casino_stats
        JOIN discord_user USING (user_id)
        WHERE (wins_slots + losses_slots) > 100
        ORDER BY (wins_slots / (wins_slots + losses_slots)) * 100 DESC
        LIMIT 10
    """)
    if len(items) == 0:
        return None, None
    toplist = []
    for item in items:
        name, rank, total, wins, losses, moneyspent, moneywon, pct = item
        new_item = (name[0:10], rank, total, wins, losses, moneyspent, moneywon, round(pct, 3))
        toplist.append(new_item)
    # toplist = addsymboltolist(toplist,7,' %')
    return columnmaker.columnmaker(['NAME', 'RANK', 'TOT', 'W', 'L', '$ SPENT', '$ WON', '%'], toplist), len(toplist)

async def getquoteforquotegame(name):
    for properquote in range(0,10):
        quote = await db.fetchrow("""
        SELECT
            content,
            coalesce(name, m->'author'->>'username'),
            m->'mentions',
            message_id
        FROM 
            message 
        JOIN 
            discord_user USING (user_id)
        WHERE 
            length(content) > 12 
            AND length(content) < 1000 
            AND content NOT LIKE '!%%' 
            AND content NOT LIKE '%wwww%'
            AND content NOT LIKE '%http%' 
            AND content NOT LIKE '%.com%' 
            AND content NOT LIKE '%.fi%'
            AND content ~* '^[A-ZÅÄÖ]'
            AND NOT bot 
            AND coalesce(name, m->'author'->>'username') LIKE $1
        ORDER BY 
            random()
        LIMIT 
            1
    """, name)
        if not invalid_quote(quote['content']):
            print('This quote is good', quote['content'].encode("utf-8"))
            return quote
        else:
            print('This quote is bad, fetching a new one..', quote['content'].encode("utf-8"))
    return None




def invalid_quote(quote):
    def is_custom_emoji(quote): #checks if quote is an emoji (ends and begins in :)
        return quote.startswith('<:') and quote.endswith('>')

    def is_emoji(quote): #checks if quote is an emoji (ends and begins in :)
        return quote.startswith(":") and quote.endswith(":")

    def is_gibberish(quote): #checks if quote consists of 6 different letters
        return len(set(quote)) < 6

    return is_gibberish(quote) or is_emoji(str(quote)) or is_custom_emoji(str(quote))

def make_word_filters(words):
    conditions = "content ~* $1"
    params = ["|".join(words)]
    return conditions, params

async def random(filter):
    word_filters, params = make_word_filters(filter)
    return await random_message_with_filter("AND ({0})".format(word_filters), params)

async def random_quote_from_channel(channel_id):
    return await random_message_with_filter("AND m->>'channel_id' = $1", [channel_id])

async def get_user_days_in_chat():
    rows = await db.fetch("""
        SELECT
            user_id,
            extract(epoch from current_timestamp - min(ts)) / 60 / 60 / 24
        FROM message
        GROUP BY user_id
    """)
    result = {}
    for row in rows:
        result[row[0]] = row[1]
# {'244610064038625280': 100.575020288113, '97767102722609152': 384.679490554317 }
    return result

async def get_least_toxic():
    items = await db.fetch("""
        with custommessage as (
            select
            coalesce(name, m->'author'->>'username') as name,
            user_id,
            count(*) as message_count
            from message
            join discord_user using (user_id)
            where NOT bot 
            group by coalesce(name, m->'author'->>'username'), user_id)
        select
        name,
        user_id,
        message_count,
        count(*) as count,
        100 - (count(*) / message_count::float) * 100 as pctoftotal
         from message
        join custommessage using (user_id)
        where NOT bot and length(content) > 15 and message_count > 300 and name not like 'toxin'
        group by user_id, message_count, name order by pctoftotal ASC
    """)
    if not items:
        return None, None
    toplist = []
    for item in items:
        name, user_id, message_count, good_messages, bs_percentage = item
        new_item = (name[0:10], message_count, good_messages, round(bs_percentage,3))
        toplist.append(new_item)
    top_ten = addranktolist(sorted(toplist, key=lambda x: x[3])[:10])
    return columnmaker.columnmaker(['NAME','RANK', 'TOTAL MSGS','GOOD MSGS', 'BS PERCENTAGE', emoji.FIRST_PLACE_MEDAL +
                                    emoji.SECOND_PLACE_MEDAL + emoji.THIRD_PLACE_MEDAL], top_ten), len(top_ten)

async def get_best_grammar():
    items = await db.fetch("""
    with custommessage as (
            select
                coalesce(name, m->'author'->>'username') as name,
                user_id,
                count(*) as message_count
            from 
                message
            join 
                discord_user using (user_id)
            where 
                NOT bot 
                AND content not LIKE '!%%'
                AND content not like '%http%'
                AND content not like '%www%'
                AND content ~* '^[A-ZÅÄÖ]'
                AND NOT EXISTS (SELECT * FROM excluded_users WHERE excluded_user_id = user_id)
            group by 
                coalesce(name, m->'author'->>'username'), user_id)
        select
            name,
            user_id,
                message_count,
                count(*) as count,
                (count(*) / message_count::float) * 100 as pctoftotal
         from 
            message
        join 
            custommessage using (user_id)
        where 
            NOT bot
            and message_count > 300
            AND content NOT LIKE '!%%'
            AND content ~ '^[A-ZÅÄÖ][a-zöäå]'            
            AND content NOT LIKE '%www%'
            AND content NOT LIKE '%http%'
            or content ~* '[A-ZÅÄÖ]\?$'
            or content ~* '[A-ZÅÄÖ]\.$'
            or content ~* '[A-ZÅÄÖ]!$'
            or (length(content) > 25 
            and content like '%,%')
            AND NOT EXISTS (SELECT * FROM excluded_users WHERE excluded_user_id = user_id)
        group by 
            user_id, message_count, name
        HAVING
            count(*) > 300
        order by 
            pctoftotal desc
    """)
    if not items:
        return None, None
    toplist = []
    for item in items:
        name, user_id, message_count, good_messages, bs_percentage = item
        new_item = (name[0:10], message_count, good_messages, round(bs_percentage,3))
        toplist.append(new_item)
    top_ten = addranktolist(sorted(toplist, key=lambda x: x[3], reverse=True)[:10])
    return columnmaker.columnmaker(['NAME','RANK', 'TOTAL MSGS','GOOD MSGS', 'GOOD GRAMMAR %', emoji.FIRST_PLACE_MEDAL +
                                    emoji.SECOND_PLACE_MEDAL + emoji.THIRD_PLACE_MEDAL], top_ten), len(top_ten)


async def get_worst_grammar():
    items = await db.fetch("""
    with custommessage as (
            select
                coalesce(name, m->'author'->>'username') as name,
                user_id,
                count(*) as message_count
            from 
                message
            join 
                discord_user using (user_id)
            where 
                NOT bot 
                AND content not LIKE '!%%'
                AND content not like '%http%'
               AND content not like '%www%'
                AND content ~* '^[A-ZÅÄÖ]'
                AND NOT EXISTS (SELECT * FROM excluded_users WHERE excluded_user_id = user_id)
            group by 
                coalesce(name, m->'author'->>'username'), user_id)
        select
            name,
            user_id,
                message_count,
                message_count - count(*) as bad_messages,
                100 - (count(*) / message_count::float) * 100 as pctoftotal
         from 
            message
        join 
            custommessage using (user_id)
        where 
            NOT bot
            and message_count > 300
            AND NOT EXISTS (SELECT * FROM excluded_users WHERE excluded_user_id = user_id)
            AND content NOT LIKE '!%%'
            AND content ~ '^[A-ZÅÄÖ][a-zöäå]'            
            AND content NOT LIKE '%www%'
            AND content NOT LIKE '%http%'
            or content ~* '[A-ZÅÄÖ]\?$'
            or content ~* '[A-ZÅÄÖ]\.$'
            or content ~* '[A-ZÅÄÖ]!$'
            or (length(content) > 25 
            and content like '%,%')
        group by 
            user_id, message_count, name
        HAVING
            count(*) > 300
        order by 
            pctoftotal desc
    """)
    if not items:
        return None, None
    toplist = []
    for item in items:
        name, user_id, message_count, bad_messages, bs_percentage = item
        new_item = (name[0:10], message_count, bad_messages, round(bs_percentage, 3))
        toplist.append(new_item)
    top_ten = addranktolist(sorted(toplist, key=lambda x: x[3], reverse=True)[:10])
    return columnmaker.columnmaker(
        ['NAME', 'RANK', 'TOTAL MSGS', 'BAD MSGS', 'BAD GRAMMAR %', emoji.FIRST_PLACE_MEDAL +
         emoji.SECOND_PLACE_MEDAL + emoji.THIRD_PLACE_MEDAL], top_ten), len(top_ten)

async def top_message_counts(filters, params, excludecommands):
    sql_excludecommands = "AND content NOT LIKE '!%%'" if excludecommands else ""
    user_days_in_chat = await get_user_days_in_chat()
    items = await db.fetch("""
        with custommessage as (
            SELECT
                coalesce(name, m->'author'->>'username') as name,
                user_id,
                count(*) as message_count
            FROM 
                message
            JOIN 
                discord_user using (user_id)
            WHERE 
                NOT bot 
                AND NOT EXISTS (SELECT * FROM excluded_users WHERE excluded_user_id = user_id) 
                {sql_excludecommands} 
                {filters}
            GROUP BY 
                coalesce(name, m->'author'->>'username'), user_id)
        SELECT
            name,
            user_id,
            message_count,
            (message_count /  sum(count(*)) over()) * 100 as pctoftotal
        FROM 
            message
        JOIN  
            custommessage using (user_id)
        WHERE 
            NOT bot
            AND NOT EXISTS (SELECT * FROM excluded_users WHERE excluded_user_id = user_id)
            {sql_excludecommands} 
            {filters}
        GROUP BY 
            user_id, message_count, name 
        ORDER BY 
            pctoftotal DESC
    """.format(filters=filters, sql_excludecommands=sql_excludecommands), *params)
    if not items:
        return None, None
    list_with_msg_per_day = []
    for item in items:
        name, user_id, message_count, pct_of_total = item
        msg_per_day = message_count / user_days_in_chat[user_id]
        new_item = (name, message_count, round(msg_per_day,3), round(pct_of_total,3))
        list_with_msg_per_day.append(new_item)
    top_ten = addranktolist(sorted(list_with_msg_per_day, key=lambda x: x[2], reverse=True)[:10])
    return columnmaker.columnmaker(['NAME','RANK', 'TOTAL','MSG PER DAY', '% OF TOTAL', emoji.FIRST_PLACE_MEDAL +
                                    emoji.SECOND_PLACE_MEDAL + emoji.THIRD_PLACE_MEDAL], top_ten), len(top_ten)

def addranktolist(listwithoutrankandmedal): #todo: get rid of this shit
    rank = 1
    newlst = []
    for item in listwithoutrankandmedal:
        if rank == 1:
            medal = '  ' + emoji.FIRST_PLACE_MEDAL
        elif rank == 2:
            medal = '  ' + emoji.SECOND_PLACE_MEDAL
        elif rank == 3:
            medal = '  ' + emoji.THIRD_PLACE_MEDAL
        else:
            medal = ''
        a, b, c, d = item
        newlst.append((a, '#' + str(rank), b, c, d, medal))
        rank += 1
    return newlst

def addsymboltolist(lst, position, symbol):
    newlst = []
    for item in lst:
        olditem = list(item)
        singleitem = olditem[position]
        newitem = str(singleitem) + symbol
        olditem.remove(singleitem)
        olditem.append(newitem)
        newlst.append(tuple(olditem))
    return newlst

async def checkifenoughmsgstoplay():
    items = await db.fetch("""
        SELECT
            coalesce(name, m->'author'->>'username') AS name
        FROM 
            message 
        JOIN 
            discord_user USING (user_id)
        WHERE 
            NOT bot 
            AND length(content) > 12 
            AND content NOT LIKE '!%%' 
            AND content NOT LIKE '%wwww%'
            AND content NOT LIKE '%http%' 
            AND content NOT LIKE '%.com%' 
            AND content NOT LIKE '%.fi%'
            AND content ~* '^[A-ZÅÄÖ]'
            AND NOT EXISTS (SELECT * FROM excluded_users WHERE excluded_user_id = user_id)
        GROUP BY 
            coalesce(name, m->'author'->>'username'), user_id
        HAVING 
            count(*) >= 500""")
    return [item['name'] for item in items]

def check_length(x,i):
    return len(str(x[i]))

async def cmd_top(client, message, input):
    if not input:
        await client.send_message(message.channel, 'You need to specify a toplist. Available toplists: spammers,'
                                                   ' custom <words separated by comma>')
        return

    excludecommands = input[0] != '!'

    input = input.lower()
    if input == 'spammers' or input == '!spammers':
        reply, amountofpeople = await top_message_counts("AND 1 = $1", [1], excludecommands)
        if not reply or not amountofpeople:
            await client.send_message(message.channel,
                                      'Not enough chat logged into the database to form a toplist.')
            return

        parameter = '(commands included)' if not excludecommands else '(commands not included)'
        header = 'Top %s spammers %s\n' % (amountofpeople, parameter)
        await client.send_message(message.channel, '```' + header + reply + '```')
        return

    elif input == 'leasttoxic':
        reply, amountofpeople = await get_least_toxic()
        if not reply or not amountofpeople:
            await client.send_message(message.channel,
                                      'Not enough chat logged into the database to form a toplist.')
            return

        header = 'Top %s least toxic (most "informative" messages)\n' % (amountofpeople)
        await client.send_message(message.channel, '```' + header + reply + '```')
        return

    elif input == 'bestgrammar':
        reply, amountofpeople = await get_best_grammar()
        if not reply or not amountofpeople:
            await client.send_message(message.channel,
                                      'Not enough chat logged into the database to form a toplist.')
            return

        header = 'Top %s people with the best grammar (most messages written with proper grammar)\n' % (amountofpeople)
        await client.send_message(message.channel, '```' + header + reply + '```')
        return

    elif input == 'worstgrammar':
        reply, amountofpeople = await get_worst_grammar()
        if not reply or not amountofpeople:
            await client.send_message(message.channel,
                                      'Not enough chat logged into the database to form a toplist.')
            return

        header = 'Top %s people with the worst grammar (most messages written with bad grammar)\n' % (amountofpeople)
        await client.send_message(message.channel, '```' + header + reply + '```')
        return

    elif input[0:6] == 'custom' or input[0:7] == '!custom':
        customwords = await getcustomwords(input, message, client)
        if not customwords:
            return
        filters, params = make_word_filters(customwords)
        custom_filter = "AND ({0})".format(filters)
        reply, amountofpeople = await top_message_counts(custom_filter, params, excludecommands)
        if not reply or not amountofpeople:
            await client.send_message(message.channel,
                                      'Not enough chat logged into the database to form a toplist.')
            return

        word = 'word' if len(customwords) == 1 else 'words'
        parameter = '(commands not included)' if excludecommands else '(commands included)'

        title = 'Top %s users of the %s: %s %s' % (amountofpeople, word, ', '.join(customwords), parameter)

        await client.send_message(message.channel, ('```%s \n' % title + reply + '```'))
        return

    elif input == 'whosaidit':
        ranking, amountofpeople = await getwhosaiditranking()
        if not ranking or not amountofpeople:
            await client.send_message(message.channel,
                                      'Not enough players to form a toplist.')
            return

        title = 'Top %s players of !whosaidit (need 20 games to qualify):' % (amountofpeople)
        msg = await get_time_until_reset()
        await client.send_message(message.channel,
                                  ('```%s \n' % title + ranking + '\n' + msg + '```'))
        return

    elif input == 'whosaidit weekly':
        weekly_winners_list = await get_whosaidit_weekly_ranking()
        if not weekly_winners_list:
            await client.send_message(message.channel,
                                      'Not enough players to form a weekly toplist.')
            return

        title = 'Weekly whosaidit winners:'
        await client.send_message(message.channel,
                                  (title + '\n' + '```' + weekly_winners_list + '```'))
        return
    elif input == 'blackjack' or input == 'bj':
        reply, amountofpeople = await getblackjacktoplist()
        if not reply or not amountofpeople:
            await client.send_message(message.channel,
                                      'Not enough players to form a toplist. (need 20 games to qualify).')
            return

        header = 'Top %s blackjack players (need 20 games to qualify)\n' % (amountofpeople)
        await client.send_message(message.channel, '```' + header + reply + '```')
        return

    elif input == 'slots':
        reply, amountofpeople = await getslotstoplist()
        jackpot = await get_jackpot()
        if not reply or not amountofpeople:
            await client.send_message(message.channel,
                                      'Not enough players to form a toplist. (need 100 games to qualify')
            return

        header = 'Top %s slots players (need 100 games to qualify)\n' % (amountofpeople)
        jackpot = '\nCurrent jackpot: %s$' % (jackpot['jackpot'])
        await client.send_message(message.channel, '```' + header + reply + jackpot + '```')
        return

    for trophy in CUSTOM_TROPHY_NAMES:
        trophylower = trophy.lower()
        if input == trophylower:
            customwords = await get_custom_trophy_conditions(trophy)
            customwords = await getcustomwords(customwords, message, client)
            if not customwords:
                return
            filters, params = make_word_filters(customwords)
            custom_filter = "AND ({0})".format(filters)
            reply, amountofpeople = await top_message_counts(custom_filter, params, excludecommands)
            if not reply or not amountofpeople:
                await client.send_message(message.channel,
                                          'Nobody has this trophy.')
                return

            word = 'word' if len(customwords) == 1 else 'words'
            parameter = '(commands not included)' if excludecommands else '(commands included)'

            title = 'Leaderboard of trophy %s (top %s users of the %s: %s %s)' % (trophy, amountofpeople, word, ', '.join(customwords), parameter)

            await client.send_message(message.channel, ('```%s \n' % title + reply + '```'))
            return

    else:
        await client.send_message(message.channel, 'Unknown list. Available lists: spammers, whosaidit, blackjack, slots, leasttoxic, bestgrammar, custom <words separated by comma>')
        return


async def get_jackpot():
    return await db.fetchrow("SELECT jackpot from casino_jackpot")

async def getwhosaiditranking():
    items = await db.fetch("""
    with score as (
            select
                user_id,
                sum(case playeranswer when 'correct' then 1 else 0 end) as wins,
                sum(case playeranswer when 'wrong' then 1 else 0 end) as losses
              from whosaidit_stats_history
              where date_trunc('week', time) = date_trunc('week', current_timestamp)
              group by user_id)
            select
                wins::float / (wins + losses) * 100 as ratio,
                least(0.20 * wins, 20) as bonuspct,
                wins,
                wins + losses as total,
                name,
                concat('#', row_number() OVER (ORDER BY (wins::float / (wins + losses) * 100)+ least(0.20* wins, 20) desc)) AS rank
            from score
            join discord_user using (user_id)
            where (wins + losses) >= 20
            order by rank asc""")
    if len(items) == 0:
        return None, None
    toplist = []
    for item in items:
        pct, bonuspct, correct,  total, name, rank = item
        new_item = (name, rank, correct, total, round(pct,3), bonuspct)
        toplist.append(new_item)
    return columnmaker.columnmaker(['NAME', 'RANK', 'CORRECT', 'TOTAL', 'ACCURACY', 'BONUS PCT'], toplist), len(toplist)

async def get_whosaidit_weekly_ranking():
    items = await db.fetch("""
    -- week_score = score per pelaaja per viikko
        with week_score as (
          select
            date_trunc('week', time) as dateadded,
            user_id,
            sum(case playeranswer when 'correct' then 1 else 0 end) as wins,
            sum(case playeranswer when 'wrong' then 1 else 0 end) as losses,
            -- accuracy
            100.0 * sum(case playeranswer when 'correct' then 1 else 0 end) / count (*) as accuracy,
            -- bonus
            least(20.0, sum(case playeranswer when 'correct' then 1 else 0 end) * 0.20) as bonus,
            -- score = accuracy + bonus
            100.0 * sum(case playeranswer when 'correct' then 1 else 0 end) / count(*) + least(20.0, sum(case playeranswer when 'correct' then 1 else 0 end) * 0.20) as score,
            -- MAGIC! weeks_best_score on kyseisen viikon paras score
            max(100.0 * sum(case playeranswer when 'correct' then 1 else 0 end) / count (*) + least(20.0, sum(case playeranswer when 'correct' then 1 else 0 end) * 0.20)) over (partition by date_trunc('week', time)) as weeks_best_score,
            -- more magic
            count(user_id) over (partition by date_trunc('week', time)) as players
          from whosaidit_stats_history
          group by user_id, date_trunc('week', time)
          having count(*) >= 20
        )

        select dateadded, name, score, wins, losses, accuracy, bonus, players, wins + losses as total
        from week_score
        join discord_user using (user_id)
        -- Valitaan vain rivit, joilla score on viikon paras score, eli voittajat
          where not date_trunc('week', dateadded) = date_trunc('week', current_timestamp) and score = weeks_best_score and players >= 3
        order by dateadded desc""")
    if len(items) == 0:
        return None, None
    toplist = []
    for item in items:
        dateadded, name, score, wins, losses, accuracy, bonus, players, total = item
        new_item = (get_week_with_year(dateadded), name, round(score, 3), wins, losses, total)
        toplist.append(new_item)
    return columnmaker.columnmaker(['WEEK', 'NAME', 'SCORE', 'WINS', 'LOSSES', 'TOTAL'], toplist)

def get_week_with_year(datetimeobject):
    return datetimeobject.strftime("%V") + '/' + datetimeobject.strftime("%Y") #Week number/year todo: fix the issue of last year's days being problematic

async def getcustomwords(input, message, client):
    # Remove empty words from search, which occured when user typed a comma without text (!top custom test,)
    customwords = list(map(lambda x: x.strip(), re.sub('!?custom', '', input).split(',')))
    def checkifsmall(value):
        return len(value) > 0
    customwords = [word for word in customwords if checkifsmall(word)]
    if len(customwords) == 0:
        await client.send_message(message.channel,"You need to specify custom words to search for.")
        return
    return customwords

async def cmd_randomquote(client, themessage, input):
    channel = themessage.channel
    if themessage.author in playinglist:
        await client.send_message(channel, "Sorry, cheating is not allowed. (You are playing whosaidit.)")
        return
    if input is not None and 'custom' in input.lower()[0:6]:
        customwords = await getcustomwords(input, themessage, client)
        if not customwords:
            return
        random_message = await random(customwords)
        if random_message is None:
            await client.send_message(channel, "Sorry, no messages could be found")
            return
        await send_quote(client, channel, random_message)
        return
    channel = None
    if input is None:
        channel = themessage.channel
    else:
        server = themessage.channel.server
        for c in server.channels:
            if c.name == input:
                channel = c
                break

        if channel is None:
            await client.send_message(themessage.channel, "Sorry, I couldn't find such channel")
            return

    random_message = await random_quote_from_channel(channel.id)
    if random_message is None:
        await client.send_message(themessage.channel, "Sorry, no messages could be found")
    else:
        await send_quote(client, themessage.channel, random_message)

async def doemojilist(client, message):
    emojilist = []
    x = 1
    for emoji in client.get_all_emojis():
        if emoji:
            rankandemoji = str(x) + ': ' + str(emoji)
            emojiname = ' :' + emoji.name + ': '
            created_at = emoji.created_at.date() # Waiting for brother Henry to implement converttoguildtimezone(time)
            emojilist.append((rankandemoji, emojiname, str(created_at)+'\n'))
            x += 1
    if not emojilist:
        await client.send_message(message.channel, 'No emoji found.')
        return
    else:
        msg = ''
        for item in emojilist:
            if (len(msg) + len(''.join(map(''.join, item)))) > 1999:
                await client.send_message(message.channel, msg)
                msg = ''
            msg += ''.join(map(''.join, item))
            if item == emojilist[-1]:
                await client.send_message(message.channel, msg)


async def getserveremojis(client):
    emojilist = []
    for emoji in client.get_all_emojis():
        if emoji:
            emojilist.append(str(emoji))
    return emojilist

async def get_least_used_emojis(emojilist):
    emojiswithusage = []
    for emoji in emojilist:
        count = await db.fetchval("select count(*) from message where content ~ $1 AND NOT bot", emoji)
        emojiswithusage.append((emoji, count))
    if not emojiswithusage:
        return None
    least_used_top_twentyfive = sorted(emojiswithusage, key=lambda x: x[1])[:25]
    return least_used_top_twentyfive

async def get_most_used_emojis(emojilist):
    emojiswithusage = []
    for emoji in emojilist:
        count = await db.fetchval("select count(*) from message where content ~ $1 AND NOT bot", emoji)
        emojiswithusage.append((emoji, count))
    if not emojiswithusage:
        return None
    most_used_top_twentyfive = sorted(emojiswithusage, key=lambda x: x[1], reverse=True)[:25]
    return most_used_top_twentyfive

async def showleastusedemojis(client, message):
    emojilist = await getserveremojis(client)
    if not emojilist:
        await client.send_message(message.channel, 'No emoji found.')
        return
    least_used_top_twentyfive = await get_least_used_emojis(emojilist)
    if not least_used_top_twentyfive:
        await client.send_message(message.channel, 'No emoji has been used.')
        return
    await client.send_message(message.channel, 'Top 25 least used emoji:'
                                               '\n'+'\n'.join(map(''.join, [ (x[0].ljust(3), ',' + str(x[1]).rjust(3)) for x in least_used_top_twentyfive ]))
                              + '\n(emoji, number of times used)')

async def showmostusedemojis(client, message):
    emojilist = await getserveremojis(client)
    if not emojilist:
        await client.send_message(message.channel, 'No emoji found.')
        return
    most_used_top_twentyfive = await get_most_used_emojis(emojilist)
    if not most_used_top_twentyfive:
        await client.send_message(message.channel, 'No emoji has been used.')
        return
    await client.send_message(message.channel, 'Top 25 most used emoji:'
                                               '\n'+'\n'.join(map(''.join, [ (x[0].ljust(3), ',' + str(x[1]).rjust(3)) for x in most_used_top_twentyfive ]))
                              + '\n(emoji, number of times used)')

async def cmd_emojicommands(client, message, arg):
    if arg.lower() == 'leastused':
        await showleastusedemojis(client, message)
        return
    if arg.lower() == 'mostused':
        await showmostusedemojis(client, message)
        return
    if arg.lower() == 'list':
        await doemojilist(client, message)
    else:
        await client.send_message(message.channel, 'Usage: !emoji <list> or <leastused>')  # obv more features will be added later
        return



async def cmd_whosaidit(client, message, _):
    if message.author not in playinglist:
        playinglist.append(message.author)
    else:
        await client.send_message(message.channel,
                                  '%s: Cannot play: You already have an unfinished game.' % message.author.name)
        return
    await dowhosaidit(client, message, _)


async def dowhosaidit(client, message, _):
    channel = message.channel
    listofspammers = await checkifenoughmsgstoplay()
    if not listofspammers or len(listofspammers) < 5:
        await client.send_message(channel,
                                  'Not enough chat logged to play.')
        playinglist.remove(message.author)
        return
    rand.shuffle(listofspammers)
    name = rand.choice(listofspammers)
    listofspammers.remove(name)
    quote = await getquoteforquotegame(name)
    if not quote:
        await client.send_message(channel,
                                  'Not enough chat logged to play.') # I guess this is a pretty
        #  rare occasion, # but just in case
        playinglist.remove(message.author)
        return
    await send_question(client, message, listofspammers, quote)

async def send_question(client, message, listofspammers, thequote):
    correctname = thequote[1]
    message_id = thequote[3]
    sanitizedquestion = sanitize_message(thequote[0], json.loads(thequote[2]))
    options = [listofspammers[0].lower(), listofspammers[1].lower(), listofspammers[2].lower(), listofspammers[3].lower(),
               correctname.lower()]
    rand.shuffle(options)
    await client.send_message(message.channel,
                    "It's time to play 'Who said it?' !\n %s, who"
                    " said the following:\n ""*%s*""\n Options: %s. You have 15 seconds to answer!"
                              % (message.author.name, sanitizedquestion, ', '.join(options)))

    answer = await getresponse(client, correctname, options, message)
    if answer and answer == 'correct':
        await client.send_message(message.channel, "%s: Correct! It was %s" % (message.author.name, correctname))
    elif answer and answer == 'wrong':
        await client.send_message(message.channel, "%s: Wrong! It was %s" % (message.author.name, correctname))
    else:
        answer = 'wrong'
        await client.send_message(message.channel, "%s: Time is up! The answer was %s" % (message.author.name, correctname))
    await save_stats_history(message.author.id, message_id, sanitizedquestion, correctname, answer)
    playinglist.remove(message.author)
    return

async def getresponse(client, name, options, message):
    def is_response(message):
        return message.content.lower() == name.lower() or message.content.lower() in options

    answer = await client.wait_for_message(timeout=15, channel=message.channel, author=message.author, check=is_response)
    if answer:
        theanswer = answer.content.lower()
        if theanswer == name.lower():
            return 'correct'
        return 'wrong'

async def save_stats_history(userid, message_id, sanitizedquestion, correctname, answer):
    correct = correctname == answer
    await db.execute("""
        INSERT INTO whosaidit_stats_history AS a
        (user_id, message_id, quote, correctname, playeranswer, correct, time, week)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    """, userid, message_id, sanitizedquestion, correctname, answer, 1 if correct else 0, datetime.today(), datetime.today().isocalendar()[1])
    print("save_stats_history: saved game result for user {0}: {1}".format(userid, correct))

async def cmd_add_excluded_user(client, message, input):
    if not input:
        await client.send_message(message.channel, 'Usage: !addexcludeduser <userID>. '
                                                   'or highlight someone: !addexcludeduser @Thomaxius')
        return
    input = input[:-1].lstrip('<@')
    if not input.isdigit():
        await client.send_message(message.channel, 'UserID has to be numeric.')
        return
    excluded_users = await get_excluded_users()
    if input in excluded_users:
        await client.send_message(message.channel, 'UserID is already in the database.')
        return
    member = discord.utils.get(message.server.members, id=input)
    if not member:
        await client.send_message(message.channel, 'UserID not found in the server.')
        return
    await add_excluded_user_into_database(input, message.author.id)
    await client.send_message(message.channel, 'Added **%s** into the database.' % member.name)

async def cmd_delete_excluded_user(client, message, input):
    if not input:
        await client.send_message(message.channel, 'Usage: !delexcludedduser <userID>. '
                                                   'or highlight someone: !delexcludedduser @Thomaxius')
        return
    input = input[:-1].lstrip('<@')
    if not input.isdigit():
        await client.send_message(message.channel, 'UserID has to be numeric.')
        return
    excluded_users = await get_excluded_users()
    if input not in excluded_users:
        await client.send_message(message.channel, 'UserID not found in the database')
        return
    member = discord.utils.get(message.server.members, id=input)
    await del_excluded_user_from_database(input)
    await client.send_message(message.channel, 'Removed **%s** from the database.' % member.name)

async def get_excluded_users():
    results = await db.fetch("""
        SELECT
            excluded_user_id
        FROM
            excluded_users
        """)
    return [item['excluded_user_id'] for item in results]

async def add_excluded_user_into_database(excluded_user_id, adder_user_id):
    await db.execute("""
        INSERT INTO excluded_users AS a
        (excluded_user_id, added_by_id)
        VALUES ($1, $2)""",excluded_user_id, adder_user_id)
    print('Added an excluded user into the database:', excluded_user_id)

async def del_excluded_user_from_database(excluded_user_id):
    await db.execute("""
        DELETE
        FROM
            excluded_users
        WHERE
            excluded_user_id like $1
        """,excluded_user_id)
    print('Removed an excluded user from the database:', excluded_user_id)

async def get_time_until_reset():
    datenow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    while datenow.weekday() != 0:
        datenow += timedelta(1)
    timeuntilreset = to_helsinki(as_utc(datenow))
    now = as_utc(datetime.now())
    delta = timeuntilreset - now
    template = "Time until this week's stats will be reset: {0} days, {1} hours, {2} minutes, {3} seconds"
    msg = template.format(*delta_to_tuple(delta))
    return msg

def register(client):
    return {
        'randomquote': cmd_randomquote,
        'whosaidit': cmd_whosaidit,
        'top': cmd_top,
        'emoji': cmd_emojicommands,
        'addexcludeduser': cmd_add_excluded_user,
        'delexcludeduser': cmd_delete_excluded_user
    }
