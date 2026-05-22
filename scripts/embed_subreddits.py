from tools.embedder import get_embeddings
from tools.embedder import get_embeddings
import psycopg2
import os
import dotenv

dotenv.load_dotenv()
logger = logging.getLogger(__name__)

conn_string = os.environ.get("POSTGRES_URL")

def backfill_subreddit_embeddings():
    with psycopg2.connect(conn_string) as conn:
        with conn.cursor() as cur:
            
            print("Fetching subreddits missing embeddings...")
            cur.execute("""
                SELECT subreddit, description 
                FROM public.subreddits 
                WHERE embedding IS NULL 
                  AND description IS NOT NULL;
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("Everything is up to date! No missing embeddings found.")
                return

            print(f"Found {len(rows)} subreddits to process.")
            
            subreddits = [row[0] for row in rows]
            descriptions = [row[1] for row in rows]
            
            print("Generating embeddings via FastEmbed...")
            vectors = get_embeddings(descriptions) 
            
            print("Updating database...")
            for subreddit, vector in zip(subreddits, vectors):
                cur.execute("""
                    UPDATE public.subreddits
                    SET embedding = %s
                    WHERE subreddit = %s;
                """, (vector, subreddit))
            
            conn.commit()
            print("Successfully backfilled all missing embeddings!")

if __name__ == "__main__":
    backfill_subreddit_embeddings()
