from pathlib import Path

p = Path("cultureroute/study_data.py")
text = p.read_text(encoding="utf-8")

# Normalize line endings to LF for matching
crlf = "\r\n" in text
lines = text.splitlines()

# Find the start of open_study_databases
start_idx = -1
for i, line in enumerate(lines):
    if line.strip().startswith("@contextmanager") and i + 1 < len(lines) and "def open_study_databases" in lines[i + 1]:
        start_idx = i
        break

assert start_idx != -1, "open_study_databases not found"

# Find end of function (before def verify_and_audit_study)
end_idx = -1
for i in range(start_idx, len(lines)):
    if lines[i].startswith("def verify_and_audit_study"):
        end_idx = i
        break

assert end_idx != -1, "verify_and_audit_study not found"

new_code = """# Persistent extracted SQLite cache paths for maximum query throughput
CACHE_DIR = ROOT_DIR / "data"
CACHE_SMART_DB = CACHE_DIR / ".cache_smart.db"
CACHE_WANDER_DB = CACHE_DIR / ".cache_wander.db"


def _ensure_extracted_cache() -> Tuple[Path, Path]:
    \"\"\"Ensure both study databases are extracted once to persistent disk cache.\"\"\"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    smart_needs_extract = not CACHE_SMART_DB.exists()
    if not smart_needs_extract:
        smart_needs_extract = CACHE_SMART_DB.stat().st_mtime < SMART_TRIP_ZIP.stat().st_mtime

    if smart_needs_extract:
        with zipfile.ZipFile(SMART_TRIP_ZIP) as z1:
            CACHE_SMART_DB.write_bytes(z1.read(SMART_DB_ENTRY))

    wander_needs_extract = not CACHE_WANDER_DB.exists()
    if not wander_needs_extract:
        wander_needs_extract = CACHE_WANDER_DB.stat().st_mtime < WANDER_MATCH_ZIP.stat().st_mtime

    if wander_needs_extract:
        with zipfile.ZipFile(WANDER_MATCH_ZIP) as z2:
            CACHE_WANDER_DB.write_bytes(z2.read(WANDER_DB_ENTRY))

    return CACHE_SMART_DB, CACHE_WANDER_DB


@contextmanager
def open_study_databases() -> Generator[Tuple[sqlite3.Connection, sqlite3.Connection], None, None]:
    \"\"\"Open persistent extracted SQLite databases in read-only mode with zero unzipping overhead.\"\"\"
    if not SMART_TRIP_ZIP.exists():
        raise FileNotFoundError(f"Missing SmartTrip archive at {SMART_TRIP_ZIP}")
    if not WANDER_MATCH_ZIP.exists():
        raise FileNotFoundError(f"Missing WanderMatch archive at {WANDER_MATCH_ZIP}")

    smart_path, wander_path = _ensure_extracted_cache()

    smart_conn: sqlite3.Connection | None = None
    wander_conn: sqlite3.Connection | None = None

    try:
        smart_conn = sqlite3.connect(f"{smart_path.as_uri()}?mode=ro", uri=True)
        wander_conn = sqlite3.connect(f"{wander_path.as_uri()}?mode=ro", uri=True)
        smart_conn.row_factory = sqlite3.Row
        wander_conn.row_factory = sqlite3.Row

        # Attach WanderMatch database as 'wm' to smart_conn for joined queries
        smart_conn.execute("ATTACH DATABASE ? AS wm", (f"{wander_path.as_uri()}?mode=ro",))

        yield smart_conn, wander_conn

    finally:
        if smart_conn:
            try:
                smart_conn.close()
            except Exception:
                pass
        if wander_conn:
            try:
                wander_conn.close()
            except Exception:
                pass


"""

new_lines = lines[:start_idx] + new_code.splitlines() + lines[end_idx:]
join_char = "\r\n" if crlf else "\n"
p.write_text(join_char.join(new_lines), encoding="utf-8")
print("Successfully patched cultureroute/study_data.py!")
