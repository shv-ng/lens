import requests

url = "https://www.reddit.com/subreddits/popular.json?limit=100"

headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
}


r = requests.get(
    url,
    headers=headers,
)
print(r)

# print(r.status_code)
# print(r.json())
