import aiohttp

async def get(url, headers=None):
    return await aiohttp.request("GET", url, headers=headers)

async def post(url, data=None):
    return await aiohttp.request("POST", url, data=data)
