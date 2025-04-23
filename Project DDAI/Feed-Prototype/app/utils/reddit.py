# app/utils/reddit.py

import requests

def fetch_reddit_posts(subreddit: str, count: int = 3) -> list[dict]:
    """
    Fetch the top `count` hot posts from `r/<subreddit>` and return
    a list of { text: title, image: thumbnail_url_or_None }.
    """
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={count}"
    headers = {"User‑Agent": "MyFeedApp/0.1 (by u/your_reddit_username)"}
    resp = requests.get(url, headers=headers, timeout=5)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("data", {}).get("children", [])
    posts = []
    for item in items:
        d = item["data"]
        # skip stickied posts
        if d.get("stickied"): 
            continue
        title = d.get("title")
        thumb = d.get("thumbnail", "")
        image = thumb if thumb.startswith("http") else None
        posts.append({"text": title, "image": image})
        if len(posts) >= count:
            break
    return posts
