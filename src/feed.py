import asyncio
from datetime import datetime
import time
import discord
import feedparser

import database as db
import command
import emoji
import util

def time_to_datetime(struct_time):
    return datetime.fromtimestamp(time.mktime(struct_time))

def get_date(entry):
    if hasattr(entry, "published_parsed"):
        sturct_time = entry.published_parsed
    elif hasattr(entry, "created_parsed"):
        sturct_time = entry.created_parsed
    elif hasattr(entry, "updated_parsed"):
        sturct_time = entry.updated_parsed
    elif hasattr(entry, "expred_parsed"):
        sturct_time = entry.expred_parsed

    return time_to_datetime(sturct_time)

async def check_feeds(client):
    feeds = await db.fetch("SELECT feed_id, url, last_entry, channel_id FROM feed")

    for id, url, last_entry, channel_id in feeds:
        await process_feed(client, id, url, last_entry, channel_id)

def get_new_items(url, since):
    def parse_entry(e):
        return {
            "title": e.title,
            "url": e.links[0].href,
            "date": get_date(e),
        }
    d = feedparser.parse(url)
    if not hasattr(d.feed, 'title'):
      return None

    feed_url = getattr(d.feed, 'link', None)

    new_items = [e for e in map(parse_entry, d.entries) if e["date"] > since]
    return d.feed.title, feed_url, sorted(new_items, key=lambda i: i["date"])

def make_embed(item):
    embed = discord.Embed(title = item["title"], url = item["url"])
    embed.set_footer(text=str(item["date"]))
    return embed

async def process_feed(client, id, url, last_entry, channel_id):
    print("feed: processing feed '{0}'".format(url))
    parsed = get_new_items(url, last_entry)
    if parsed is None:
      print("feed: feed missing title")
      return

    feed_title, feed_url, new_items = parsed
    if len(new_items) > 0:
        # Send messages
        for item in new_items:
            embed = make_embed(item)
            if feed_url is None:
              embed.set_author(name=feed_title)
            else:
              embed.set_author(name=feed_title, url=feed_url)

            util.threadsafe(client, client.send_message(discord.Object(id=channel_id), embed=embed))

        # Update last entry
        max_timestamp = max(map(lambda i: i["date"], new_items))
        await db.execute("""
            UPDATE feed
            SET last_entry = $1
            WHERE feed_id = $2
        """, max_timestamp, id)

async def task(client):
    # Wait until the client is ready
    util.threadsafe(client, client.wait_until_ready())

    # Check feeds every minute
    fetch_interval = 60

    while True:
        await asyncio.sleep(fetch_interval)
        try:
            print("feed: checking feeds")
            await check_feeds(client)
            print("feed: feeds checked")
        except Exception:
            await util.log_exception()

async def cmd_feed(client, message, arg):
    if arg is None:
        await client.add_reaction(message, emoji.CROSS_MARK)
        return

    subcommands = {
        "list": cmd_feed_list,
        "add": cmd_feed_add,
        "remove": cmd_feed_remove,
    }

    cmd, arg = command.parse(arg, prefix="")
    handler = subcommands.get(cmd, None)
    if handler is None:
        await client.add_reaction(message, emoji.CROSS_MARK)
        return
    await handler(client, message, arg)

async def cmd_feed_list(client, message, _):
    feeds = await db.fetch("SELECT url FROM feed WHERE channel_id = $1 ORDER BY feed_id", message.channel.id)
    msg = "Feeds in this channel:\n" + "\n".join(map(lambda f: f[0], feeds))
    await client.send_message(message.channel, msg)

async def cmd_feed_add(client, message, url):
    # TODO: Check the feed is valid
    # TODO: Find feeds from linked url

    await db.execute("INSERT INTO feed (url, channel_id) VALUES ($1, $2)", url, message.channel.id)

    print("feed: added feed '{0}'".format(url))
    await client.add_reaction(message, emoji.WHITE_HEAVY_CHECK_MARK)


async def cmd_feed_remove(client, message, url):
    if url is None:
        await client.add_reaction(message, emoji.CROSS_MARK)
        return

    await db.execute("DELETE FROM feed WHERE url = $1", url)

    print("feed: removed feed '{0}'".format(url))
    await client.add_reaction(message, emoji.WHITE_HEAVY_CHECK_MARK)

def register(client):
    print("feed: registering")
    util.start_task_thread(task(client))
    return {
        "feed": cmd_feed,
    }
