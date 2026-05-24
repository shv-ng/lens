import asyncio
import logging
import os

import dotenv
import psycopg2

from tools.embedder import get_embeddings

dotenv.load_dotenv()


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

conn_string = os.environ.get("POSTGRES_URL")
BATCH_SIZE = 256


async def backfill_subreddit_embeddings():
    with psycopg2.connect(conn_string) as conn:
        total_updated = 0

        while True:
            with conn.cursor() as cur:
                logger.info(
                    f"Fetching up to {BATCH_SIZE} subreddits missing embeddings..."
                )

                cur.execute(
                    """
                    SELECT subreddit, description 
                    FROM public.subreddits 
                    WHERE embedding IS NULL 
                    LIMIT %s;
                """,
                    (BATCH_SIZE,),
                )

                rows = cur.fetchall()

                if not rows:
                    logger.info("No more rows to process")
                    break

                logger.info(f"Processing batch of {len(rows)} subreddits...")

                subreddits = [row[0] for row in rows]
                descriptions = [row[1] if row[1] else row[0] for row in rows]

                vectors = await asyncio.to_thread(get_embeddings, descriptions)

                logger.info("Updating database batch...")
                for subreddit, vector in zip(subreddits, vectors):
                    cur.execute(
                        """
                        UPDATE public.subreddits
                        SET embedding = %s
                        WHERE subreddit = %s;
                        """,
                        (vector, subreddit),
                    )

                conn.commit()

                total_updated += len(rows)
                logger.info(
                    f"Successfully saved batch. Total updated so far: {total_updated}"
                )

        logger.info(
            f"Finished! Successfully backfilled {total_updated} total missing embeddings."
        )


if __name__ == "__main__":
    backfill_subreddit_embeddings()
