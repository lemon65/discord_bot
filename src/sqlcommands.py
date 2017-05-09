import discord
import re
import json
import time_util
from asyncio import sleep
import database as db
import columnmaker
import random as rand
from datetime import datetime

playinglist = []

def sanitize_message(content, mentions):
    for m in mentions:
        content = content.replace("<@%s>" % m["id"], "@%s" % m["username"])
    return content

async def send_quote(client, channel, random_message):
    content, timestamp, mentions, author = random_message
    mentions = json.loads(mentions)
    author = json.loads(author)
    sanitized = sanitize_message(content, mentions)
    avatar_url = "https://cdn.discordapp.com/avatars/{id}/{avatar}.jpg".format(**author)

    embed = discord.Embed(description=sanitized)
    embed.set_author(name=author["username"], icon_url=avatar_url)
    embed.set_footer(text=str(timestamp))
    await client.send_message(channel, embed=embed)

async def random_message_with_filter(filters, params):
    async with db.connect() as c:
        return await c.fetchrow("""
            SELECT
                content,
                ts::timestamptz AT TIME ZONE 'Europe/Helsinki',
                m->'mentions',
                m->'author'
            FROM message
            WHERE length(content) > 6 AND content NOT LIKE '!%%' AND m->'author'->>'bot' IS NULL {filters}
            ORDER BY random()
            LIMIT 1
        """.format(filters=filters), *params)

async def getblackjacktoplist():
    async with db.connect() as c:
        items = await c.fetch("""
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
        new_item = (name, rank, total, wins, losses, surrenders, ties, moneyspent, round(moneywon), round(pct, 3))
        toplist.append(new_item)
    # toplist = addsymboltolist(toplist,9,' %')
    return columnmaker.columnmaker(['NAME', 'RANK', 'TOT', 'W', 'L', 'S', 'T', '$ SPENT', '$ WON', '%'], toplist), len(toplist)

async def getslotstoplist():
    async with db.connect() as c:
        items = await c.fetch("""
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
        new_item = (name, rank, total, wins, losses, moneyspent, moneywon, round(pct, 3))
        toplist.append(new_item)
    # toplist = addsymboltolist(toplist,7,' %')
    return columnmaker.columnmaker(['NAME', 'RANK', 'TOT', 'W', 'L', '$ SPENT', '$ WON', '%'], toplist), len(toplist)

async def getquoteforquotegame(name):
    async with db.connect() as c:
        for properquote in range(0,6):
            quote = await c.fetchrow("""
            SELECT
                content,
                m->'author'->>'username',
                m->'mentions',
                message_id
            FROM message
            WHERE length(content) > 12 AND content NOT LIKE '!%%' AND content NOT LIKE '%wwww%'
             AND content NOT LIKE '%http%' AND content NOT LIKE '%.com%' AND content NOT LIKE '%.fi%'
             AND m->'author'->>'bot' IS NULL AND m->'author'->>'username' LIKE $1
            ORDER BY random()
            LIMIT 1
        """, name)
            if checkifproperquote(quote) > 6:
                return quote
        return None

def checkifproperquote(quote):
    return len(set(quote[0]))

def make_word_filters(words):
    conditions = "content ~* $1"
    params = ["|".join(words)]
    return conditions, params

async def random(filter):
    word_filters, params = make_word_filters(filter)
    return await random_message_with_filter("AND ({0})".format(word_filters), params)

async def random_quote_from_channel(channel_id):
    return await random_message_with_filter("AND m->>'channel_id' = $1", [channel_id])

async def get_user_days_in_chat(c):
    rows = await c.fetch("""
        SELECT
            m->'author'->>'id',
            extract(epoch from current_timestamp - min(ts)) / 60 / 60 / 24
        FROM message
        GROUP BY m->'author'->>'id'
    """)
    result = {}
    for row in rows:
        result[row[0]] = row[1]
# {'244610064038625280': 100.575020288113, '97767102722609152': 384.679490554317 }
    return result

async def top_message_counts(filters, params, excludecommands):
    sql_excludecommands = "AND content NOT LIKE '!%%'" if excludecommands else ""

    async with db.connect() as c:
        user_days_in_chat = await get_user_days_in_chat(c)
        items = await c.fetch("""
            select
                m->'author'->>'username' as name,
                m->'author'->>'id' as user_id,
                count(*) as messages
            from message
            WHERE m->'author'->>'bot' is null {sql_excludecommands} {filters}
            group by m->'author'->>'username', m->'author'->>'id'
        """.format(filters=filters, sql_excludecommands=sql_excludecommands), *params)
        if not items:
            return None, None
        list_with_msg_per_day = []
        for item in items:
            name, user_id, message_count = item
            msg_per_day = message_count / user_days_in_chat[user_id]
            new_item = (name, message_count, round(msg_per_day,3))
            list_with_msg_per_day.append(new_item)
        top_ten = addranktolist(sorted(list_with_msg_per_day, key=lambda x: x[2], reverse=True)[:10])
        return columnmaker.columnmaker(['NAME','RANK','TOTAL','MSG PER DAY'], top_ten), len(top_ten)

def addranktolist(listwithoutrank):
    rank = 1
    newlst = []
    for item in listwithoutrank:
        a, b, c = item
        newlst.append((a, '#' + str(rank), b, c))
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
    async with db.connect() as c:
        items = await c.fetch("""
            select
                m->'author'->>'username' as name
            from message
            WHERE m->'author'->>'bot' is null and length(content) > 12 AND content NOT LIKE '!%%' AND content NOT LIKE '%wwww%'
             AND content NOT LIKE '%http%' AND content NOT LIKE '%.com%' AND content NOT LIKE '%.fi%'
             AND m->'author'->>'bot' IS NULL AND m->'author'->>'username' not like 'toxin'
            group by m->'author'->>'username', m->'author'->>'id'
            having count(*) >= 500
            """)
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
    if input == ('spammers') or input == ('!spammers'):
        reply, amountofpeople = await top_message_counts("AND 1 = $1", [1], excludecommands)
        if not reply or not amountofpeople:
            await client.send_message(message.channel,
                                      'Not enough chat logged into the database to form a toplist.')
            return

        parameter = '(commands included)' if not excludecommands else '(commands not included)'
        header = 'Top %s spammers %s\n' % (amountofpeople, parameter)
        await client.send_message(message.channel, '```' + header + reply + '```')
        return

    if input[0:6] == ('custom') or input[0:7] == ('!custom'):
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

    if input == ('whosaidit'):
        ranking, amountofpeople = await getwhosaiditranking()
        if not ranking or not amountofpeople:
            await client.send_message(message.channel,
                                      'Not enough players to form a toplist.')
            return

        title = 'Top %s players of !whosaidit (need 20 games to qualify):' % (amountofpeople)
        await client.send_message(message.channel,
                                  ('```%s \n' % title + ranking + '```'))
        return

    if input == ('blackjack') or input == ('bj'):
        reply, amountofpeople = await getblackjacktoplist()
        if not reply or not amountofpeople:
            await client.send_message(message.channel,
                                      'Not enough players to form a toplist. (need 20 games to qualify).')
            return

        header = 'Top %s blackjack players (need 20 games to qualify)\n' % (amountofpeople)
        await client.send_message(message.channel, '```' + header + reply + '```')
        return

    if input == ('slots'):
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

    else:
        await client.send_message(message.channel, 'Unknown list. Available lists: spammers, whosaidit, blackjack, slots, custom <words separated by comma>')
        return


async def get_jackpot():
    async with db.connect() as c:
        return await c.fetchrow("""
            SELECT jackpot from casino_jackpot
            """)

async def getwhosaiditranking():
    async with db.connect(readonly = True) as c:
        items = await c.fetch("""
            SELECT
                (correct / (correct + wrong)) * 100,
                correct,
                correct + wrong,
                name,
                concat('#', row_number() OVER (ORDER BY  (correct / (correct + wrong)) * 100 desc)) AS rank
            FROM whosaidit_stats
            JOIN discord_user USING (user_id)
            WHERE (correct + wrong) > 19
            ORDER BY rank ASC
            LIMIT 10
        """)
        if len(items) == 0:
            return None, None
        toplist = []
        for item in items:
            pct, correct, total, name, rank = item
            new_item = (name, rank, correct, total, round(pct,3))
            toplist.append(new_item)
        return columnmaker.columnmaker(['NAME','RANK','TOTAL','CORRECT', 'ACCURACY'], toplist), len(toplist)

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
    if input is not None and 'custom' in input.lower()[0:6]:
        channel = themessage.channel
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

async def getemojis(emojilist):
    emojiswithusage = []
    for emoji in emojilist:
        async with db.connect() as c:
            count = await c.fetchval("""
            select count(*)
             from message
             where content ~ $1 AND m->'author'->>'bot' IS NULL""", emoji)
            emojiswithusage.append((emoji, count))
    if not emojiswithusage:
        return None
    leastusedtopten = sorted(emojiswithusage, key=lambda x: x[1])[:25]
    return leastusedtopten

async def showleastusedemojis(client, message):
    emojilist = await getserveremojis(client)
    if not emojilist:
        await client.send_message(message.channel, 'No emoji found.')
        return
    leastusedtopten = await getemojis(emojilist)
    if not leastusedtopten:
        await client.send_message(message.channel, 'No emoji has been used.')
        return
    await client.send_message(message.channel, 'Top 25 least used emoji:'
                                               '\n'+'\n'.join(map(''.join, [ (x[0].ljust(3), ',' + str(x[1]).rjust(3)) for x in leastusedtopten ]))
                              + '\n(emoji, number of times used)')



async def cmd_emojicommands(client, message, arg):
    if arg.lower() == 'leastused':
        await showleastusedemojis(client, message)
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
    if answer[0] == 'correct':
        await client.send_message(message.channel, "%s: Correct! It was %s" % (message.author.name, correctname))
    elif answer[0] == 'wrong':
        await client.send_message(message.channel, "%s: Wrong! It was %s" % (message.author.name, correctname))
    else:
        await client.send_message(message.channel, "%s: Time is up! The answer was %s" % (message.author.name, correctname))
    await save_stats(message.author.id, answer=answer[0])
    await save_stats_history(message.author.id, message_id, sanitizedquestion, correctname, answer[0])
    playinglist.remove(message.author)
    return

async def getresponse(client, name, options, message):
    def is_response(message):
        return message.content.lower() == name.lower() or message.content.lower() in options

    answer = await client.wait_for_message(timeout=15, channel=message.channel, author=message.author, check=is_response)
    if answer:
        theanswer = answer.content.lower()
        if theanswer == name.lower():
            return 'correct', theanswer
        return 'wrong', theanswer

# redundant
async def save_stats(userid, answer=None):
    if answer == 'correct':
        async with db.connect() as c:
            await c.execute("""
                INSERT INTO whosaidit_stats AS a
                (user_id, correct)
                VALUES ($1, 1)
                ON CONFLICT (user_id) DO UPDATE
                SET correct = GREATEST(0, a.correct + EXCLUDED.correct)
            """, userid)
    else:
        async with db.connect() as c:
            await c.execute("""
                INSERT INTO whosaidit_stats AS a
                (user_id, wrong)
                VALUES ($1, 1)
                ON CONFLICT (user_id) DO UPDATE
                SET wrong = GREATEST(0, a.wrong + EXCLUDED.wrong)
            """, userid)

async def save_stats_history(userid, message_id, sanitizedquestion, correctname, answer):
    correct = correctname == answer
    async with db.connect() as c:
        await c.execute("""
            INSERT INTO whosaidit_stats_history AS a
            (user_id, message_id, quote, correctname, playeranswer, correct, time, week)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, userid, message_id, sanitizedquestion, correctname, answer, 1 if correct else 0, datetime.today(), datetime.today().isocalendar()[1])
    print("save_stats_history: saved game result for user {0}: {1}".format(userid, correct))

def register(client):
    return {
        'randomquote': cmd_randomquote,
        'whosaidit': cmd_whosaidit,
        'top': cmd_top,
        'emoji': cmd_emojicommands
    }
