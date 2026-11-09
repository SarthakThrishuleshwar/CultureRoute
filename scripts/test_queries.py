import re
import sqlite3

with open("app.py", encoding="utf-8") as f:
    code = f.read()

conn = sqlite3.connect("data/study_cache.db")
queries = re.findall(r"read_sql_query\(\s*\"\"\"(.*?)\"\"\"", code, re.DOTALL)
queries += re.findall(r"read_sql_query\(\s*\"([^\"]+)\"", code)
queries += re.findall(r"read_sql_query\(\s*'([^']+)'", code)

print(f"Found {len(queries)} direct read_sql_query strings")
for q in queries:
    clean_q = " ".join(q.split())
    if "{" in clean_q or "?" in clean_q or "%" in clean_q:
        continue
    try:
        conn.execute(clean_q)
    except Exception as e:
        print(f"FAIL: {clean_q[:60]}... -> {e}")

print("Static queries test finished.")
