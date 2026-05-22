import os
import asyncpg
import dotenv
import logging

dotenv.load_dotenv()
logger = logging.getLogger(__name__)

conn_string = os.environ.get("POSTGRES_URL")

if not conn_string:
    ValueError("POSTGRES_URL not set in .env file")


class Postgres:
    pool: asyncpg.Pool | None = None

    @classmethod
    async def connect(cls):
        if not cls.pool:
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
        if cls.pool is None:
            logger.fatal("Postgres not Connected")
            return 
        return cls.pool

