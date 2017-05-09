# a Thing that resets certain tables at certain times, such as 'whosaidit' gets resetted weekly.

import database as db
import datetime
import asyncio
import util

async def main():
    resetdate = await get_reset_date_from_db()
    if resetdate['max']:
        print('Next reset date:', resetdate['max'])
        await scheduleareset(resetdate['max'])
    if not resetdate['max']:
        date = await generatenewdate()
        await set_reset_date_to_db(date)
        print('No reset date in database, generating one..')

async def get_reset_date_from_db():
    async with db.connect() as c:
        return await c.fetchrow("""
            SELECT max(nextresetdate) from resetdate
            """)

async def set_reset_date_to_db(date):
    async with db.connect() as c:
        await c.execute("""
            INSERT INTO resetdate (nextresetdate) VALUES ($1);
            """, date)
        print('Reset date set:',date)

async def generatenewdate():
    date = (datetime.datetime.today() + datetime.timedelta(days=7)).replace(hour=12, minute=0, second=0, microsecond=0)
    return date

async def scheduleareset(resetdate):
    diffinseconds = (resetdate - datetime.datetime.today()).total_seconds()
    #diffinseconds = diffinseconds + 60 - diffinseconds # debug
    print('Falling asleep for %s seconds' % (diffinseconds))
    await asyncio.sleep(diffinseconds)
    newdate = await generatenewdate()
    await set_reset_date_to_db(newdate)
    await doawardceremony()

async def getwinner():
    async with db.connect() as c:
        topthree = await c.fetchrow("""
        with score as (
          select
            user_id,
            sum(case playeranswer when 'correct' then 1 else 0 end) as wins,
            sum(case playeranswer when 'wrong' then 1 else 0 end) as losses
          from whosaidit_stats_history where date_trunc('week', time) = date_trunc('week', current_timestamp - interval
           '12 hours')
          group by user_id
        )
        select user_id, name, wins, losses,  wins + losses  as total, wins::float / (wins + losses) * 100 as pct
        from score
        join discord_user using (user_id)
        where (wins + losses) > 20
        order by pct desc""")
        if not topthree or (len(topthree) < 3):
            return None
        return topthree[0]


async def doawardceremony():
    winner = await getwinner()
    if not winner:
        print('Not enough players have played whosaidit to conduct an awards ceremony, trying again next week..)')
        return


def register(client):
    print("Tableresetter: registering")
    util.start_task_thread(main())
    return {
    }