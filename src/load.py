import os, json, pathlib, datetime
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

load_dotenv()
DATA_DIR = pathlib.Path("data")
IN_PATH = DATA_DIR / "structured.json"

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

def main():
    data = json.loads(IN_PATH.read_text(encoding="utf-8"))
    df = pd.DataFrame(data)
    df["updated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    recs = df.to_dict(orient="records")

    supabase.table("articles").upsert(recs, on_conflict="id").execute()
    print(f"Upserted {len(recs)} rows into articles")

if __name__ == "__main__":
    main()
