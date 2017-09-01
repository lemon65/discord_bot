import asyncio
import json
import os
import sys
import threading
import traceback
import http_util as http

webhook_url = os.environ.get("ERROR_CHANNEL_WEBHOOK", None)

async def log_exception():
    err_str = traceback.format_exc()
    print("ERROR: {0}".format(err_str))
    if webhook_url is not None:
        await post_exception(err_str)

    # If the error is 'Event loop is closed' we crash the bot and let it restart
    # A retarded solution to a retarded issue
    error_message = str(sys.exc_info()[1])
    if error_message == 'Event loop is closed':
        msg = "Snipety snap! Event loop is closed! Committing sudoku in 3.. 2.. 1.."
        print("util: {0}".format(msg))
        if webhook_url is not None:
            await post_exception(msg)
        os._exit(0)

async def post_exception(err_str):
    data = {
        "username": "Errors",
        "icon_url": "https://rce.fi/error.png",
        "text": "```" + err_str + "```",
    }

    r = await http.post(webhook_url + "/slack", data=json.dumps(data))
    if r.status != 200:
        print("util: unknown webhook response {0}".format(r))
        return

    print("util: posted error on channel")


# Run discord.py coroutines from antoher thread
def threadsafe(client, coroutine):
    return asyncio.run_coroutine_threadsafe(coroutine, client.loop).result()

# Start a coroutine task in new thread
def start_task_thread(coroutine):
    def thread_func(coroutine):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(coroutine)
    threading.Thread(target=thread_func, args=(coroutine,)).start()
