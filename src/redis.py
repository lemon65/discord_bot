import aioredis
import os
import threading


_pool_holder = threading.local()

def connection_details():
    return (os.environ["REDIS_HOST"], int(os.environ["REDIS_PORT"]))

async def get_pool():
    global _pool_holder
    pool = getattr(_pool_holder, "pool", None)
    if pool is None:
        pool = await aioredis.create_redis_pool(connection_details())
        setattr(_pool_holder, "pool", pool)
    return pool

async def close_pool():
    global _pool_holder
    pool = getattr(_pool_holder, "pool", None)
    if pool is not None:
        pool.close()
        await pool.wait_closed()
        setattr(_pool_holder, "pool", None)

async def get(key, encoding="utf-8"):
    pool = await get_pool()
    await pool.get(key, encoding=encoding)

async def set(key, data, expire=None):
    pool = await get_pool()
    await pool.set(key, data, expire=expire)
