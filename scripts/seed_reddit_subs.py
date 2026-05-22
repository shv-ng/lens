import tempfile
import requests
import logging
import csv
import os
import dotenv
import psycopg2

dotenv.load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

conn_string = os.environ.get("POSTGRES_URL")

count_sub_seeded = 0
limit = 5000

base_url = "https://www.reddit.com/subreddits/popular.json?limit=100"
after_token = None

headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
}


with tempfile.NamedTemporaryFile(
    mode="w+", suffix=".csv", delete=True, newline=""
) as tmp_csv:
    csv_file_path = tmp_csv.name
    logger.info(f"Temp CSV file path: {csv_file_path}")

    writer = csv.writer(tmp_csv)
    writer.writerow(["Subreddit", "Description"])
    #
    # while count_sub_seeded < 5000:  # limit to 5000 subs only
    #     url = f"{base_url}&after={after_token}" if after_token else base_url
    #
    #     r = requests.get(
    #         base_url,
    #         headers=headers,
    #     )
    #     if r.status_code == 200:
    #         data = r.json()
    #         children = data["data"]["children"]
    #         if not children:
    #             logger.info("No more children")
    #             break
    #
    #         for sub in children:
    #             sub_name = sub["data"]["display_name_prefixed"]
    #             description = sub["data"]["description"]
    #             writer.writerow([sub_name, description])
    #
    #         count_sub_seeded += len(children)
    #         logger.info(f"Seeded {count_sub_seeded} subs")
    #
    #         after_token = data["data"]["after"]
    #         if not after_token:
    #             logger.info("No more after token")
    #             break
    #     else:
    #         logger.error(f"Error fetching data: {r.status_code}")
    #         break
    #
    # tmp_csv.flush()
    #
    # logger.info("Connecting to Postgres")
    #
    tmp_csv.seek(0)

    conn = None
    try:
        conn = psycopg2.connect(conn_string)
        cur = conn.cursor()

        cur.execute(
            "CREATE TABLE IF NOT EXISTS subreddits (subreddit text, description text)"
        )

        cur.copy_expert(
            sql="COPY subreddits (subreddit, description) FROM STDIN WITH CSV HEADER",
            file=tmp_csv,
        )

        conn.commit()
        logger.info(
            "Successfully bulk inserted all rows cleanly into Postgres database!"
        )
    except Exception as e:
        logger.error(f"Error copying data to Postgres: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
