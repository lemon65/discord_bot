import database as db
from sqlcommands import get_user_days_in_chat
import asyncio

TROPHY_NAMES = ['Top spammer', 'Least toxic', 'Whosaidit total #1', 'Whosaidit all time high score',
                'Biggest gambling problem']
CUSTOM_TROPHY_NAMES = []


async def main():
    await get_custom_trophy_names()

async def get_custom_trophy_names():
    trophies = await db.fetch("""
        select
            trophy_name
        from 
            custom_trophies
    """)
    for trophy in trophies:
        CUSTOM_TROPHY_NAMES.append(trophy['trophy_name'])

async def get_custom_trophy_conditions(trophyname):
    trophy = await db.fetch("""
        select
            trophy_conditions
        from 
            custom_trophies
        where
            trophy_name like '{trophyname}'
    """.format(trophyname=trophyname))
    for trophy in trophy:
        return trophy['trophy_conditions']



async def custom_trophy_getter(trophyname):
    custom_trophy_conditions = await get_custom_trophy_conditions(trophyname)
    custom_trophy_id, custom_trophy_name = await random(custom_trophy_conditions.split(','))
    return custom_trophy_id, custom_trophy_name

async def get_custom_trophy_winner(filters, params):
    user_days_in_chat = await get_user_days_in_chat()
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
            WHERE 
                NOT bot AND content NOT LIKE '!%%' {filters}
            group by 
                coalesce(name, m->'author'->>'username'), user_id)
        select
            user_id,
            name,
            message_count
        from 
            message
        join 
            custommessage using (user_id)
        where 
            NOT bot AND content NOT LIKE '!%%' {filters}
        group by 
            user_id, message_count, name""".format(filters=filters), *params)
    if not items:
        return None, None
    list_with_msg_per_day = []
    for item in items:
        user_id, name, message_count = item
        msg_per_day = message_count / user_days_in_chat[user_id]
        new_item = (user_id, round(msg_per_day, 3), message_count, name)
        list_with_msg_per_day.append(new_item)
    winner = sorted(list_with_msg_per_day, key=lambda x: x[1], reverse=True)[:1]
    return winner[0][0], winner[0][3]

def make_word_filters(words):
    conditions = "content ~* $1"
    params = ["|".join(words)]
    return conditions, params

async def random(filter):
    word_filters, params = make_word_filters(filter)
    return await get_custom_trophy_winner("AND ({0})".format(word_filters), params)

async def cmd_trophycabinet(client, message, arg):
    oldmessage = await client.send_message(message.channel, 'Please wait while I check the book of winners..')
    user_id = message.author.id
    trophycabinet = await find_user_trophies(user_id)
    msg = ''
    if trophycabinet:
        for trophy in trophycabinet:
            msg += ':trophy: ' + trophy + '\n'
        await client.edit_message(oldmessage, 'Your trophies:\n' + msg + '\n')
    else:
        await client.edit_message(oldmessage, 'You have no trophies.')

async def cmd_addtrophy(client, message, arg):
    if not (arg.startswith("name=")) or ("conditions=" not in arg):
        await client.send_message(message.channel, "Correct usage, name= followed by conditions= separated by comma, for example:\n "
                                                   "!addtrophy name=Most polite people conditions=Thank you, please, you're welcome")
        return
    name, conditions = parse_award_info(arg)
    alreadyexists = name in CUSTOM_TROPHY_NAMES
    if alreadyexists:
        await client.send_message(message.channel, "There is a trophy with a similar name already.")
        return
    await add_custom_award_to_database(name, conditions, message.id)
    CUSTOM_TROPHY_NAMES.append(name)
    await client.send_message(message.channel, "Succesfully added a trophy.")

def parse_award_info(unparsed_arg):
    string = unparsed_arg.split('conditions=')
    name = str(string[0]).replace('name=', '', 1)
    conditions = string[-1]
    return name, conditions

async def add_custom_award_to_database(name, conditions, message_id):
    await db.execute("""
        INSERT INTO custom_trophies AS a
        (message_id, trophy_name, trophy_conditions)
        VALUES ($1, $2, $3)""", message_id, name, conditions)
    print('Added custom award to the database: message_id %s, trophy name: %s, conditions: %s' % (message_id, name, conditions))


async def cmd_alltrophies(client, message, arg):
    oldmessage = await client.send_message(message.channel, 'Please wait while I check the book of winners..')
    trophycabinet = await find_all_trophies()
    msg = ''
    if trophycabinet:
        for trophy in trophycabinet:
            msg += ':trophy: ' + trophy + '\n'
        await client.edit_message(oldmessage, msg + '\n')
    else:
        await client.edit_message(oldmessage, 'Nobody has won a trophy yet.')

async def find_user_trophies(user_id):
    trophycabinet = []
    for trophyname in TROPHY_NAMES:
        trophy_winner_id, trophy_winner_name = await trophies.get(trophyname)()
        if user_id == trophy_winner_id:
            trophycabinet.append(trophyname)
    for trophyname in CUSTOM_TROPHY_NAMES:
        trophy_winner_id, trophy_winner_name = await custom_trophy_getter(trophyname)
        if user_id == trophy_winner_id:
            trophycabinet.append(trophyname)
    return trophycabinet

async def find_all_trophies():
    trophycabinet = []
    for trophyname in TROPHY_NAMES:
        trophy_winner_id, trophy_winner_name = await trophies.get(trophyname)()
        if trophy_winner_name:
            trophycabinet.append(trophyname + '  -  ' + trophy_winner_name)
    for trophyname in CUSTOM_TROPHY_NAMES:
        trophy_winner_id, trophy_winner_name = await custom_trophy_getter(trophyname)
        if trophy_winner_name:
            trophycabinet.append(trophyname + '  -  ' + trophy_winner_name)
    return trophycabinet

async def get_top_spammer():
    user_days_in_chat = await get_user_days_in_chat()
    items = await db.fetch("""
        select
            user_id,
            name as username,
            count(*) as message_count
        from 
            message
        join
             discord_user using (user_id)
        where 
            NOT bot AND content NOT LIKE '!%%'
        group by 
            user_id, username
        order by 
            message_count 
        desc 
        limit 10
    """)
    if not items:
        return None, None
    list_with_msg_per_day = []
    for item in items:
        user_id, name, message_count = item
        msg_per_day = message_count / user_days_in_chat[user_id]
        new_item = (user_id, round(msg_per_day, 3), message_count, name)
        list_with_msg_per_day.append(new_item)
    winner = sorted(list_with_msg_per_day, key=lambda x: x[1], reverse=True)[:1]
    return winner[0][0], winner[0][3]

async def get_top_whosaidit():
    items = await db.fetch("""
        with score as 
            (
            select
                user_id,
                name as username,
                sum(case playeranswer when 'correct' then 1 else 0 end) as wins,
                sum(case playeranswer when 'wrong' then 1 else 0 end) as losses
            from 
                whosaidit_stats_history
            join
                discord_user using (user_id)
            group by 
                user_id,
                username
            )
        select
            user_id,
            username
        from 
            score
        join 
            discord_user using (user_id)
        where 
            (wins + losses) >= 20
        order by 
            wins::float / (wins + losses) * 100 
        desc 
        limit 1
    """)
    if not items:
        return None, None
    for item in items:
        user_id, name = item
        return user_id, name

async def get_top_whosaidit_score():
    items = await db.fetch("""
        with week_score as 
        (
          select
            date_trunc('week', time) as dateadded,
            user_id,
            name as username,
            sum(case playeranswer when 'correct' then 1 else 0 end) as wins,
            sum(case playeranswer when 'wrong' then 1 else 0 end) as losses,
            100.0 * sum(case playeranswer when 'correct' then 1 else 0 end) / count (*) as accuracy,
            least(20.0, sum(case playeranswer when 'correct' then 1 else 0 end) * 0.20) as bonus,
            100.0 * sum(case playeranswer when 'correct' then 1 else 0 end) / count(*) + least(20.0, sum(case playeranswer when 'correct' then 1 else 0 end) * 0.20) as score,
            max(100.0 * sum(case playeranswer when 'correct' then 1 else 0 end) / count (*) + least(20.0, sum(case playeranswer when 'correct' then 1 else 0 end) * 0.20)) over (partition by date_trunc('week', time)) as weeks_best_score,
            count(user_id) over (partition by date_trunc('week', time)) as players
          from 
            whosaidit_stats_history
            join 
            discord_user using (user_id)
          group by 
            user_id, 
            date_trunc('week', time),
            username
          having 
            count(*) >= 20
        )
        select 
            user_id,
            username
        from 
            week_score
        join 
            discord_user using (user_id)
        where 
            not date_trunc('week', dateadded) = date_trunc('week', current_timestamp) and score = weeks_best_score and players >= 3
        order by score 
        desc 
        limit 1
    """)
    if not items:
        return None, None
    for item in items:
        user_id, name = item
        return user_id, name

async def get_top_gambling_addict():
    items = await db.fetch("""
            select
                user_id,
                name
            from 
                message
            JOIN 
                discord_user USING (user_id)
            where 
                content like '!slots%' or content like '!blackjack%'
            group by 
                user_id, name
            having 
                count(*) >= 100
            order by 
                count(*) desc
            limit 1
    """) # this should be replaced with a query that searches from the respected casino games' tables
    if not items:
        return None, None
    for item in items:
        user_id, name = item
        return user_id, name

async def get_least_toxic():
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
            group by coalesce(name, m->'author'->>'username'), user_id
            )
        select
            user_id, 
            name
        from 
            message
        join 
            custommessage using (user_id)
        where 
            NOT bot and length(content) > 15 and message_count > 300 and name not like 'toxin'
        group by 
            user_id, message_count, name 
        order by (count(*) / message_count::float) * 100 
        desc 
        limit 1
    """)
    if not items:
        return None, None
    for item in items:
        user_id, name = item
        return user_id, name

trophies = {
    'Top spammer': get_top_spammer,
    'Least toxic': get_least_toxic,
    'Whosaidit total #1': get_top_whosaidit,
    'Whosaidit all time high score': get_top_whosaidit_score,
    'Biggest gambling problem': get_top_gambling_addict
}

def register(client):
    return {
        'trophycabinet': cmd_trophycabinet,
        'alltrophies': cmd_alltrophies,
        'addtrophy': cmd_addtrophy
    }