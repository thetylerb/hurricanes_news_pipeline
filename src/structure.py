import os, json, pathlib, datetime, re, hashlib, textwrap
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
DATA_DIR = pathlib.Path("data")
RAW_PATH = DATA_DIR / "raw_blob.txt"
OUT_PATH = DATA_DIR / "structured.json"

BASE_URL = os.getenv("OPENAI_BASE_URL")
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_DEPLOYMENT", "gpt-4o")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

PROMPT = """
You will receive one Hurricanes news article blob that begins with:
SOURCE_URL, TITLE, AUTHOR, PUBLISHED, followed by the body text.

Return ONLY VALID JSON. No prose, no code fences. Schema:
{
  "id": string,                 // derive from source_url or a stable hash
  "title": string,
  "author": string|null,
  "published_at": string|null,  // ISO8601 if possible, else null
  "summary": string,            // 2-3 sentences
  "tags": string[],             // simple hockey tags if obvious
  "source_url": string,
  "extracted_at": string        // set to now if not provided
}
Output a SINGLE JSON object (not an array).
"""

def chunks(blob: str):
    return [c.strip() for c in blob.split("---ENDDOC---") if c.strip()]

def best_effort_json(text: str):
    text = (text or "").strip()
    if not text:
        raise ValueError("empty LLM response")
    # already JSON?
    try:
        return json.loads(text)
    except Exception:
        pass
    # try to extract an object
    m = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if m:
        return json.loads(m.group(1))
    raise ValueError("no JSON found")

def slug_from_url(url: str) -> str:
    s = url.rstrip("/").split("/")[-1] or url
    if not s or s == "news":
        s = hashlib.md5(url.encode("utf-8")).hexdigest()[:16]
    return s

def parse_headers(doc: str):
    # Grab header lines (we wrote them in collect.py)
    source = re.search(r"^SOURCE_URL:\s*(.+)$", doc, flags=re.MULTILINE)
    title  = re.search(r"^TITLE:\s*(.+)$",      doc, flags=re.MULTILINE)
    author = re.search(r"^AUTHOR:\s*(.*)$",     doc, flags=re.MULTILINE)
    publ   = re.search(r"^PUBLISHED:\s*(.*)$",  doc, flags=re.MULTILINE)
    # Body = everything after the first blank line following PUBLISHED
    parts = doc.split("\n\n", 1)
    body = parts[1].strip() if len(parts) > 1 else ""
    return {
        "source_url": source.group(1).strip() if source else "",
        "title": title.group(1).strip() if title else "",
        "author": (author.group(1).strip() or None) if author else None,
        "published_at": (publ.group(1).strip() or None) if publ else None,
        "body": body
    }

def naive_summary(text: str, max_chars=400) -> str:
    # very simple fallback: first 2 sentences or first N chars
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sents) >= 2:
        out = " ".join(sents[:2])
    else:
        out = textwrap.shorten(text, width=max_chars, placeholder="…")
    return out

def main():
    if not RAW_PATH.exists():
        print("No raw_blob.txt found. Run collect.py first.")
        return

    blob = RAW_PATH.read_text(encoding="utf-8")
    docs = chunks(blob)
    records = []
    now = datetime.datetime.utcnow().isoformat() + "Z"

    print(f"Structuring {len(docs)} docs via {MODEL} @ {BASE_URL}")

    for i, doc in enumerate(docs, 1):
        headers = parse_headers(doc)
        url = headers["source_url"]
        default_obj = {
            "id": slug_from_url(url),
            "title": headers["title"],
            "author": headers["author"],
            "published_at": headers["published_at"],
            "summary": naive_summary(headers["body"]) if headers["body"] else "",
            "tags": [],
            "source_url": url,
            "extracted_at": now,
        }

        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "Always return strictly JSON."},
                    {"role": "developer", "content": PROMPT},
                    {"role": "user", "content": doc}
                ],
                temperature=0,
            )
            raw = resp.choices[0].message.content or ""
            print(f"[{i}/{len(docs)}] LLM reply (first 160 chars): {raw[:160]!r}")
            obj = best_effort_json(raw)

            # make sure required fields exist; fill from defaults if missing
            for k, v in default_obj.items():
                obj[k] = obj.get(k) or v

            records.append(obj)

        except Exception as e:
            # Fallback: still emit a usable record so the pipeline continues
            print(f"[{i}/{len(docs)}] Falling back to local parse due to:", e)
            records.append(default_obj)

    OUT_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} records to {OUT_PATH}")

if __name__ == "__main__":
    main()
