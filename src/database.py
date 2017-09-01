import os
from contextlib import contextmanager

import threading
import asyncpg

schema_migrations = {
    # Initial DB
    1: """
        -- Bot internals
        CREATE TABLE IF NOT EXISTS schema_version (
            version NUMERIC NOT NULL,
            upgraded TIMESTAMP NOT NULL DEFAULT current_timestamp
        );

        CREATE TABLE IF NOT EXISTS start_times (
            ts timestamp NOT NULL,
            message TEXT
        );


        -- Casino
        CREATE TABLE IF NOT EXISTS casino_account (
            discriminator TEXT NOT NULL,
            balance NUMERIC NOT NULL,
            PRIMARY KEY (discriminator)
        );

        CREATE TABLE IF NOT EXISTS casino_bet (
            discriminator TEXT NOT NULL,
            bet NUMERIC NOT NULL,
            PRIMARY KEY (discriminator)
        );


        -- Archiver
        CREATE TABLE IF NOT EXISTS channel_archiver_status (
            channel_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            PRIMARY KEY (channel_id)
        );
        CREATE TABLE IF NOT EXISTS message (
            message_id TEXT NOT NULL,
            m JSONB NOT NULL,
            PRIMARY KEY (message_id)
        );


        -- Feed
        CREATE TABLE IF NOT EXISTS feed (
            feed_id SERIAL PRIMARY KEY,
            url TEXT NOT NULL,
            last_entry TIMESTAMP DEFAULT current_timestamp,
            channel_id TEXT NOT NULL,
            UNIQUE (url)
        );
    """,

    # Extract message timestamps and content to columns
    2: """
        ALTER TABLE message ADD COLUMN ts TIMESTAMP;
        UPDATE message SET ts = (m->>'timestamp')::timestamp;
        ALTER TABLE message ALTER COLUMN ts SET NOT NULL;

        ALTER TABLE message ADD COLUMN content TEXT;
        UPDATE message SET content = m->>'content';
        ALTER TABLE message ALTER COLUMN content SET NOT NULL;
    """,

    # Remove old and unused start_times table
    3: """
        DROP TABLE start_times;
    """,

    # Add index for faster message content searches
    4: """
        CREATE INDEX message_content_trgm_idx ON message USING GIN (content gin_trgm_ops);
    """,

    # Add table for reminders
    5: """
        CREATE TABLE reminder (
            reminder_id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            ts TIMESTAMP NOT NULL,
            text TEXT NOT NULL,
            original_text TEXT NOT NULL,
            reminded BOOL NOT NULL DEFAULT FALSE
        );
    """,

    # Add index for message date to make statistics queries faster
    6: """
        CREATE INDEX message_ts_date_idx ON message ((ts::date));
    """,

    7: """

        -- Casino
        CREATE TABLE IF NOT EXISTS casino_account (
            user_id TEXT NOT NULL,
            balance NUMERIC NOT NULL,
            PRIMARY KEY (user_id)
        );

        CREATE TABLE IF NOT EXISTS casino_bet (
            user_id TEXT NOT NULL,
            bet NUMERIC NOT NULL,
            PRIMARY KEY (user_id)
        );

        CREATE TABLE IF NOT EXISTS casino_stats (
            user_id TEXT NOT NULL,
            wins_bj NUMERIC NOT NULL DEFAULT 0,
            wins_slots NUMERIC NOT NULL DEFAULT 0,
            losses_bj NUMERIC NOT NULL DEFAULT 0,
            ties NUMERIC NOT NULL DEFAULT 0,
            surrenders NUMERIC NOT NULL DEFAULT 0,
            moneyspent_bj  NUMERIC NOT NULL DEFAULT 0,
            moneyspent_slots  NUMERIC NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id)
        );

        CREATE TABLE IF NOT EXISTS whosaidit_stats (
            user_id TEXT NOT NULL,
            correct NUMERIC NOT NULL DEFAULT 0,
            wrong NUMERIC NOT NULL DEFAULT 0,
            moneyspent  NUMERIC NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id)
        );

    """,

    # Change discriminator to user_id in casino_bets and casino_account
    8: """
        -- Create user_id column in casino_bet and fill it with data
        ALTER TABLE casino_bet ADD COLUMN user_id TEXT;
        UPDATE casino_bet SET user_id = (
          SELECT m->'author'->>'id'
          FROM message
          WHERE concat(m->'author'->>'username', '#', m->'author'->>'discriminator') = discriminator
          LIMIT 1
        );
        ALTER TABLE casino_bet ALTER COLUMN user_id SET NOT NULL;

        -- Change casino_bet primary key from discriminator to user_id
        ALTER TABLE casino_bet DROP CONSTRAINT casino_bet_pkey;
        ALTER TABLE casino_bet ADD PRIMARY KEY (user_id);

        -- Drop discriminator column
        ALTER TABLE casino_bet DROP COLUMN discriminator;

        -- Create user_id column in casino_account and fill it with data
        ALTER TABLE casino_account ADD COLUMN user_id TEXT;
        UPDATE casino_account SET user_id = (
          SELECT m->'author'->>'id'
          FROM message
          WHERE concat(m->'author'->>'username', '#', m->'author'->>'discriminator') = discriminator
          LIMIT 1
        );
        ALTER TABLE casino_bet ALTER COLUMN user_id SET NOT NULL;

        -- Change casino_account primary key from discriminator to user_id
        ALTER TABLE casino_account DROP CONSTRAINT casino_account_pkey;
        ALTER TABLE casino_account ADD PRIMARY KEY (user_id);

        -- Drop discriminator column
        ALTER TABLE casino_account DROP COLUMN discriminator;
    """,

    # Fix incorrect reminder times
    9: """
        UPDATE reminder SET ts = ts - interval '2 hours';
    """,

    # Create table for user information
    10: """
        CREATE TABLE discord_user (
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            raw JSONB NOT NULL,
            PRIMARY KEY (user_id)
        );
    """,

    # Add foreign key constraints to make sure data references are valid
    11: """
        ALTER TABLE casino_account
        ADD FOREIGN KEY (user_id) REFERENCES discord_user (user_id);

        ALTER TABLE casino_bet
        ADD FOREIGN KEY (user_id) REFERENCES discord_user (user_id);

        ALTER TABLE reminder
        ADD FOREIGN KEY (user_id) REFERENCES discord_user (user_id);

        ALTER TABLE casino_stats
        ADD FOREIGN KEY (user_id) REFERENCES discord_user (user_id);

        ALTER TABLE whosaidit_stats
        ADD FOREIGN KEY (user_id) REFERENCES discord_user (user_id);

        ALTER TABLE channel_archiver_status
        ADD FOREIGN KEY (message_id) REFERENCES message (message_id);
    """,

    # Add additional records to game stats tables
    12: """

    ALTER TABLE whosaidit_stats
    ADD COLUMN streak NUMERIC NOT NULL DEFAULT 0;

    ALTER TABLE whosaidit_stats
    ADD COLUMN record NUMERIC NOT NULL DEFAULT 0;


    """,

    # See above
    13: """

    ALTER TABLE casino_stats
    ADD COLUMN losses_slots NUMERIC NOT NULL DEFAULT 0;

    ALTER TABLE casino_stats
    ADD COLUMN biggestwin_slots NUMERIC NOT NULL DEFAULT 0;

    ALTER TABLE casino_stats
    ADD COLUMN bj_blackjack NUMERIC NOT NULL DEFAULT 0;
    """,

    14: """

    ALTER TABLE casino_stats
    ADD COLUMN moneywon_bj NUMERIC NOT NULL DEFAULT 0;

    ALTER TABLE casino_stats
    ADD COLUMN moneywon_slots NUMERIC NOT NULL DEFAULT 0;
    """,

    15: """

    CREATE TABLE casino_jackpot (
        jackpot NUMERIC NOT NULL DEFAULT 0
        );
    CREATE TABLE casino_jackpot_history (
            user_id TEXT NOT NULL,
            jackpot NUMERIC NOT NULL DEFAULT 0,
            date NUMERIC NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id)
        );
    INSERT INTO casino_jackpot (jackpot) VALUES (0);
    """,

    16: """

    CREATE TABLE resetdate (
        nextresetdate timestamp NOT NULL
        );
    """,

    17: """
    CREATE TABLE whosaidit_stats_history (
    user_id TEXT NOT NULL REFERENCES discord_user(user_id),
    message_id TEXT NOT NULL REFERENCES message(message_id),
    quote TEXT NOT NULL,
    correctname TEXT NOT NULL,
    playeranswer TEXT NOT NULL,
    correct NUMERIC NOT NULL DEFAULT 0,
    streak NUMERIC NOT NULL DEFAULT 0,
    losestreak NUMERIC NOT NULL DEFAULT 0,
    time timestamp NOT NULL,
    week NUMERIC NOT NULL
    );
    """,

    18: """
    CREATE TABLE whosaidit_weekly_winners (
    user_id TEXT NOT NULL REFERENCES discord_user(user_id),
    wins NUMERIC NOT NULL DEFAULT 0,
    losses NUMERIC NOT NULL DEFAULT 0,
    time timestamp NOT NULL
    );
    """,

    # Add user_id field to message table and index it
    19: """
        ALTER TABLE message ADD COLUMN user_id TEXT;
        UPDATE message SET user_id = m->'author'->>'id';
        CREATE INDEX message_user_id_idx ON message (user_id);
    """,

    # Add bot field to message table and index it
    20: """
        ALTER TABLE message ADD COLUMN bot BOOL;
        UPDATE message SET bot = coalesce(m->'author'->>'bot', 'false') != 'false';
        CREATE INDEX message_bot_idx ON message (bot);
        ALTER TABLE message ALTER COLUMN bot SET NOT NULL;
    """,
    21: """
        CREATE TABLE 
            custom_trophies
        (
            message_id TEXT NOT NULL REFERENCES message(message_id),
            trophy_name TEXT NOT NULL,
            trophy_conditions TEXT NOT NULL
        );
        """,
    22: """
        ALTER TABLE 
            custom_trophies
        ADD FOREIGN KEY 
            (message_id) REFERENCES message (message_id);
        """,
    23: """
        CREATE TABLE excluded_users (
            excluded_user_id TEXT NOT NULL REFERENCES discord_user(user_id),
            added_by_id TEXT NOT NULL REFERENCES discord_user(user_id)
            )
        """,
    24: """
    CREATE TABLE 
        censored_words
    (
        message_id TEXT NOT NULL REFERENCES message(message_id),
        censored_words TEXT NOT NULL,
        exchannel TEXT NOT NULL,
        infomessage TEXT NOT NULL

    );
    """,
    25: """
        ALTER TABLE 
            censored_words
        ADD FOREIGN KEY 
            (message_id) REFERENCES message (message_id);
        """
    }

_pool_holder = threading.local()

_connect_string = "postgres://%s:%s@localhost:5432/%s" % (
    os.environ["DATABASE_USERNAME"],
    os.environ["DATABASE_PASSWORD"],
    os.environ["DATABASE_NAME"]
)

async def get_pool():
    global _pool_holder
    pool = getattr(_pool_holder, "pool", None)
    if pool is None:
        pool = await asyncpg.create_pool(_connect_string)
        setattr(_pool_holder, "pool", pool)
    return pool

async def close_pool():
    global _pool_holder
    pool = getattr(_pool_holder, "pool", None)
    if pool is not None:
        await pool.close()
        setattr(_pool_holder, "pool", None)

# Database API

async def execute(sql, *args):
    pool = await get_pool()
    async with pool.acquire() as con:
        return await con.execute(sql, *args)

async def fetch(sql, *args):
    pool = await get_pool()
    async with pool.acquire() as con:
        return await con.fetch(sql, *args)

async def fetchrow(sql, *args):
    pool = await get_pool()
    async with pool.acquire() as con:
        return await con.fetchrow(sql, *args)

async def fetchval(sql, *args):
    pool = await get_pool()
    async with pool.acquire() as con:
        return await con.fetchval(sql, *args)

class transaction:
    def __init__(self, readonly = False):
        self.readonly = readonly

    async def __aenter__(self):
        self.pool = await get_pool()
        self.con = await self.pool.acquire()
        self.tx = self.con.transaction(readonly=self.readonly, isolation='serializable' if self.readonly else 'read_committed')
        await self.tx.start()
        return self.con

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is not None:
            await self.tx.rollback()
        else:
            await self.tx.commit()

        await self.pool.release(self.con)

# Migration stuff

async def table_exists(tx, table_name):
    rows = await tx.fetch("SELECT * FROM information_schema.tables WHERE table_name = $1", table_name)
    return bool(len(rows))

async def get_current_schema_version(tx):
    if await table_exists(tx, "schema_version"):
        result = await tx.fetchrow("SELECT max(version) FROM schema_version")
        return result[0] if result is not None else 0
    else:
        return 0

def new_migrations(version):
    mig_version = lambda m: m[0]
    not_applied = [ m for m in schema_migrations.items() if mig_version(m) > version ]
    if len(not_applied) == 0:
        return [], version

    not_applied = sorted(not_applied, key=mig_version)
    up_to = max(map(mig_version, not_applied))
    return not_applied, up_to

async def initialize_schema():
    async with transaction() as tx:
        version = await get_current_schema_version(tx)
        migrations, new_version = new_migrations(version)

        if len(migrations) > 0:
            for version, sql in migrations:
                print("database: migrating to version {0}".format(version))
                await tx.execute(sql)

            await tx.execute("INSERT INTO schema_version (version) VALUES ($1)", new_version)

    print("database: schema is in up to date")
