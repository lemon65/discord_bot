import asyncio
import traceback

import discord
import parsedatetime
from datetime import datetime
from time_util import to_utc, to_helsinki, as_utc, as_helsinki

import emoji
import database as db
import util

def register(client):
    print("reminder: registering")
    util.start_task_thread(task(client))
    return {
        "remind": cmd_reminder,
        "remindme": cmd_reminder,
        "todo": cmd_reminder,
    }

async def cmd_reminder(client, message, text):
    reminder = parse_reminder(text)
    if reminder is None:
        reply = "Sorry {message.author.mention}, I couldn't figure out the time for your reminder.".format(message=message)
        await client.send_message(message.channel, reply)
        await client.add_reaction(message, emoji.CROSS_MARK)
        return

    await add_reminder(message.author.id, reminder.time, reminder.text, reminder.original_text)

    reply = "\n".join([
        "Hello, {message.author.mention}!",
        "I'll remind you about `{reminder.text}` at time `{reminder.time_text}`!",
        "I interpreted that as `{helsinki_time}`.",
    ]).format(message=message, reminder=reminder, helsinki_time=to_helsinki(reminder.time))
    await client.send_message(message.channel, reply)
    await client.add_reaction(message, emoji.WHITE_HEAVY_CHECK_MARK)

async def add_reminder(user_id, time, text, original_text):
    await db.execute("""
        INSERT INTO reminder(user_id, ts, text, original_text)
        VALUES ($1, $2, $3, $4)
    """, user_id, time.replace(tzinfo=None), text, original_text)

async def task(client):
    # Wait until the client is ready
    util.threadsafe(client, client.wait_until_ready())

    while True:
        await asyncio.sleep(1)
        try:
            await process_next_reminder(client)
        except Exception as e:
            await util.log_exception()

async def process_next_reminder(client):
    async with db.transaction() as tx:
        reminders = await tx.fetch("""
            SELECT reminder_id, user_id, text
            FROM reminder
            WHERE ts < current_timestamp AND reminded = false
            ORDER BY ts ASC
        """)
        if len(reminders) == 0:
            return

        print("reminder: sending {0} reminders".format(len(reminders)))

        for id, user_id, text in reminders:
            msg = "Hello! I'm here to remind you about `{0}`".format(text)
            user = util.threadsafe(client, client.get_user_info(user_id))
            util.threadsafe(client, client.send_message(user, msg))

            await tx.execute("""
                UPDATE reminder
                SET reminded = true
                WHERE reminder_id = $1
            """, id)

def parse_reminder(text):
    cal = parsedatetime.Calendar()

    source_time = to_helsinki(as_utc(datetime.now()))
    time_expressions = cal.nlp(text, source_time)
    time_expressions = time_expressions if time_expressions else []

    reminders = map(lambda p: Reminder(text, p), time_expressions)
    reminders_in_priority_order = sorted(reminders, key=lambda r: r.priorty)
    return next(iter(reminders_in_priority_order), None)

class Reminder:
    def __init__(self, original_text, time_expression):
        time, flags, start, end, time_text = time_expression

        self.original_text = original_text
        self.time_text = time_text
        self.time = to_utc(as_helsinki(time))

        self.text = self.strip_middle(original_text, start, end)

        prefix = start == 0
        postfix = end == len(original_text)
        self.priorty = 1 if postfix else (2 if prefix else 3)

    def strip_middle(self, text, start, end):
        return text[:start].strip() + " " + text[end:].strip()
