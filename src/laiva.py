from datetime import datetime, timedelta
from math import floor

from time_util import as_helsinki, as_utc, to_utc

def register(client):
    return {
        "laiva": cmd_laiva,
        "laivalle": cmd_laiva,
    }

def delta_to_tuple(delta):
    days = delta.days
    s = delta.seconds
    seconds = s % 60
    m = floor((s - seconds) / 60)
    minutes = m % 60
    h = floor((m - minutes) / 60)
    hours = h
    return (days, hours, minutes, seconds)

async def cmd_laiva(client, message, query):
    laiva = to_utc(as_helsinki(datetime(2017, 6, 16, 17, 0)))
    laivaover = to_utc(as_helsinki(datetime(2017, 6, 18, 10, 0)))
    now = as_utc(datetime.now())
    now_to_last_laivaover = now - laivaover

    if (laiva < now) and (laivaover > now):
        await client.send_message(message.channel, "Laiva is currently happening!!")
        return

    if ((laivaover + timedelta(days=1)) < now) and laiva < now:
        await client.send_message(message.channel, ("**Last laiva ended:** {0} days, {1} hours, {2} minutes, {3} seconds ago, **next laiva:** TBA.")
                                  .format(*delta_to_tuple(now_to_last_laivaover)))
        return

    if laivaover < now:
        await client.send_message(message.channel, "Laiva is already over, but paha olo remains.")
        return

    delta = laiva - now
    template = "Time left until laiva: {0} days, {1} hours, {2} minutes, {3} seconds!!"
    msg = template.format(*delta_to_tuple(delta))
    await client.send_message(message.channel, msg)

