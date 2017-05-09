import os
import json
import aiohttp

import command
import osu_api as api

async def cmd_osu(client, message, user):
    user_info = next(await api.user(user), None)

    if not user_info:
        await client.send_message(message.channel, "User %s not found" % user)
        return

    user_line = "{user.username} (#{user.rank}) has {user.pp_rounded} pp and {user.accuracy_rounded}% acc".format(user=user_info)

    scores = await api.user_best(user, 5)
    if not scores:
        await client.send_message(message.channel, "No scores found for user %s" % user)
        return

    plays = []
    for i, play in enumerate(scores):
        bm = await play.beatmap()

        template = "\n".join([
            "{index}. {bm.artist} - {bm.title} [{bm.version}] (★{bm.stars_rounded})",
            "   {mods}{play.rank} {play.accuracy_rounded}% {play.combo}x{full_combo} {play.pp_rounded}pp, {play.score_formatted} score ({play.date})",
        ])
        plays.append(template.format(
            index = i+1,
            bm = bm,
            play = play,
            full_combo = " FC" if play.full_combo else "",
            mods = (play.mods + " ").lstrip(" "),
        ))

    reply = "**{user_line}**\n```{plays}```".format(user_line=user_line, plays="\n".join(plays))
    await client.send_message(message.channel, reply)

def register(client):
    return {
        "osu": cmd_osu,
    }
