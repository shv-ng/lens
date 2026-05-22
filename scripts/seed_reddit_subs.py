import requests

def batch_seed(data, batch_size):

count_sub_seeded = 0

url = "https://www.reddit.com/subreddits/popular.json?limit=100"

headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
}

while count_sub_seeded < 5000:  # limit to 5000 subs only
    r = requests.get(
        url,
        headers=headers,
    )
    if r.status_code == 200:
        data = r.json()

    count_sub_seeded += 100
