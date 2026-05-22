import tempfile
import requests
import logging
import csv
import os
import dotenv

dotenv.load_dotenv()

logger = logging.getLogger(__name__)

db_url = os.environ.get("POSTGRES_URL")

count_sub_seeded = 0

url = "https://www.reddit.com/subreddits/popular.json?limit=100"

headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
}


with tempfile.NamedTemporaryFile(mode="w+",suffix='.csv',delete=True,newline='') as tmp_csv:
    csv_file_path = tmp_csv.name
    logger.info(f"Temp CSV file path: {csv_file_path}")

    writer = csv.writer(tmp_csv)
    writer.writerow(["Subreddit", "Description"])

    while count_sub_seeded < 5000:  # limit to 5000 subs only
        r = requests.get(
            url,
            headers=headers,
        )
        if r.status_code == 200:
            data = r.json()
            for sub in data["data"]["children"]:
                sub_name = sub["data"]["display_name_prefixed"]
                description = sub["data"]["description"]
                writer.writerow([sub_name, description])
        count_sub_seeded += 100
        logger.info(f"Seeded {count_sub_seeded} subs")
    tmp_csv.flush()


