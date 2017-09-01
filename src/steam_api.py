# TODO REMOVE

import os
import http_util as http
import redis
import json

HOUR_IN_SECONDS = 60 * 60
WEEK_IN_SECONDS = 7 * 24 * HOUR_IN_SECONDS

class Game:
    def __init__(self, json):
        self.name = json.get("gameName", "N/A")

class OwnedGame:
    def __init__(self, json):
        self.appid = json.get("appid")
        self.playtime_forever = json.get("playtime_forever", 0)
        self.playtime_2weeks = json.get("playtime_2weeks", 0)

    @property
    async def details(self):
        return await game(self.appid)

def make_query_string(params):
    return "?" + "&".join(map(lambda x: "=".join(map(str, x)), params.items()))

async def call_api(endpoint, params):
    url = "https://api.steampowered.com/%s%s" % (endpoint, make_query_string(params))
    r = await http.get(url)
    return await r.json()

async def owned_games(steamid):
    cache_key = "steam:owned_games:{steamid}".format(steamid=steamid)

    cached = await redis.get(cache_key)
    if cached is not None:
        return map(OwnedGame, json.loads(cached)["response"]["games"])

    raw = await call_api("IPlayerService/GetOwnedGames/v0001/", {
        "key": os.environ["STEAM_API_KEY"],
        "steamid": steamid,
        "format": "json",
    })

    await redis.set(cache_key, json.dumps(raw), expire=HOUR_IN_SECONDS)

    return map(OwnedGame, raw["response"]["games"])

async def game(appid):
    cache_key = "steam:game:{appid}".format(appid=appid)

    cached = await redis.get(cache_key)
    if cached is not None:
        return Game(json.loads(cached)["game"])

    raw = await call_api("ISteamUserStats/GetSchemaForGame/v2/", {
        "key": os.environ["STEAM_API_KEY"],
        "appid": appid,
    })

    await redis.set(cache_key, json.dumps(raw), expire=WEEK_IN_SECONDS)

    return Game(raw["game"])

async def steamid(username):
    username = username.lower()

    def parse(raw):
        return raw["response"].get("steamid", None)

    cache_key = "steam:steamid:{username}".format(username=username)

    cached = await redis.get(cache_key)
    if cached is not None:
        return parse(json.loads(cached))

    raw = await call_api("ISteamUser/ResolveVanityURL/v0001/", {
        "key": os.environ["STEAM_API_KEY"],
        "vanityurl": username,
        "format": "json",
    })

    await redis.set(cache_key, json.dumps(raw), expire=WEEK_IN_SECONDS)
    return parse(raw)

async def call_appdetails(appid):
    url = "http://store.steampowered.com/api/appdetails?appids={appid}".format(appid=appid)
    r = await http.get(url)
    return await r.json()

async def appdetails(appid):
    def parse(raw):
        return raw[str(appid)].get("data", {"name": "pls report error to thomaxius"})

    cache_key = "steam:appdetails:{appid}".format(appid=appid)

    cached = await redis.get(cache_key)

    if cached is not None:
        return parse(json.loads(cached))

    raw = await call_appdetails(appid)

    await redis.set(cache_key, json.dumps(raw))

    return parse(raw)
