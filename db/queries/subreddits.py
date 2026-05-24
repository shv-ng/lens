import logging

from db.postgres import Postgres

db = Postgres()
logger = logging.getLogger(__name__)


async def get_subreddits(embedding: list[float], limit: int = 5) -> list[dict]:
    query = """
        SELECT
            subreddit,
            description,
            embedding <=> $1::vector AS distance
        FROM subreddits
        ORDER BY distance
        LIMIT $2
    """

    vector = f"[{','.join(map(str, embedding))}]"

    pool = await db.get_connection()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            query,
            vector,
            limit,
        )

    return [dict(row) for row in rows]
