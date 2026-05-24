import logging
import os

import asyncpg

logger = logging.getLogger(__name__)


class Postgres:
    pool: asyncpg.Pool | None = None

    @classmethod
    async def connect(cls):

        if not cls.pool:
            conn_string = os.environ.get("POSTGRES_URL")
            if not conn_string:
                ValueError("POSTGRES_URL not set in .env file")

            cls.pool = await asyncpg.create_pool(
                conn_string,
                min_size=1,
                max_size=10,
            )
            logger.info("Connected to Postgres")

    @classmethod
    async def disconnect(cls):
        if cls.pool:
            await cls.pool.close()
            cls.pool = None

            logger.info("Closed Postgres connection")

    @classmethod
    async def get_connection(cls):
        if cls.pool is None or cls.pool.is_closing():
            logger.error("Postgres not connected, connecting...")
            await cls.connect()
        return cls.pool
