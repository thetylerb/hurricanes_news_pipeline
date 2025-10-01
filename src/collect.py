import pathlib, time, requests
from bs4 import BeautifulSoup
import re

BASE = "https://www.nhl.com"
INDEX = "https://www.nhl.com/hurricanes/news/"
DATA_DIR = pathlib.Path("data")
DATA_DIR.mkdir(exist_ok=True)
RAW_PATH = DATA_DIR / "raw_blob.txt"

HEADERS = {"User-Agent": "class-project/1.0"}
SLEEP = 1
MAX_ARTICLES = 10   # start small to test, then bump up

def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text

def is_article_url(href: str) -> bool:
    # keep only Hurricanes news detail pages, not /topic/ or the index itself
    if not href.startswith("/hurricanes/news/"):
        return False
    if "/topic/" in href or "/tag/" in href:
        return False
    # last segment should look like a slug (has a dash, not just 'news')
    last = href.rstrip("/").split("/")[-1]
    if last.lower() == "news":
        return False
    return "-" in last and len(last) > 8

def find_links(pages: int = 4) -> list[str]:
    seen = set()
    kept = []
    for p in range(pages):
        url = INDEX if p == 0 else f"{INDEX}?page={p}"
        html = fetch(url)
        soup = BeautifulSoup(html, "html.parser")

        # collect every href under the news page
        raw_hrefs = [a["href"] for a in soup.find_all("a", href=True)]
        print(f"[page {p}] found {len(raw_hrefs)} anchors")

        # normalize to absolute and filter
        for h in raw_hrefs:
            h_abs = BASE + h if h.startswith("/") else h
            # only consider links that point back to nhl.com/hurricanes
            if not h_abs.startswith("https://www.nhl.com/hurricanes/"):
                continue
            if is_article_url(h):
                if h_abs not in seen:
                    seen.add(h_abs)
                    kept.append(h_abs)

        print(f"[page {p}] kept so far: {len(kept)}")

        time.sleep(SLEEP)

    # print a preview of what we kept to verify
    print("Sample kept links:")
    for u in kept[:10]:
        print("  ", u)

    return kept[:MAX_ARTICLES]


def extract_text(url):
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    title = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
    # author
    author = ""
    ma = soup.find("meta", attrs={"name": "author"})
    if ma and ma.get("content"):
        author = ma["content"].strip()
    else:
        by = soup.find(lambda t: t.name in ["p","span","div"] and t.get_text().strip().lower().startswith("by "))
        if by:
            author = by.get_text(strip=True).removeprefix("By ").strip()

    # published date
    published = ""
    t = soup.find("time")
    if t and t.get("datetime"):
        published = t["datetime"].strip()

    # main body
    candidates = [
        "div.article-body", "div.Article__Content", "div#story-body", "article", "main"
    ]
    body = ""
    for sel in candidates:
        node = soup.select_one(sel)
        if node:
            txt = node.get_text("\n", strip=True)
            if len(txt) > 300:
                body = txt
                break
    if not body:
        body = "\n".join([p.get_text(" ", strip=True) for p in soup.find_all("p")])

    return (
        f"SOURCE_URL: {url}\n"
        f"TITLE: {title}\n"
        f"AUTHOR: {author}\n"
        f"PUBLISHED: {published}\n\n"
        f"{body}\n"
        "---ENDDOC---\n"
    )


def main():
    links = find_links()
    print(f"Found {len(links)} articles")
    docs = []
    for link in links:
        try:
            print("Scraping:", link)
            docs.append(extract_text(link))
            time.sleep(SLEEP)
        except Exception as e:
            print("Skip:", link, e)
    RAW_PATH.write_text("".join(docs), encoding="utf-8")
    print(f"Wrote {RAW_PATH}")

if __name__ == "__main__":
    main()
