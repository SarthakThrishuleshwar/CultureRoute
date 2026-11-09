from pathlib import Path

# 1. Update study_db.py
p_db = Path("cultureroute/study_db.py")
text_db = p_db.read_text(encoding="utf-8")
if "from functools import lru_cache" not in text_db:
    text_db = text_db.replace("import hashlib\n", "import hashlib\nfrom functools import lru_cache\n")
if "@lru_cache(maxsize=16)\ndef load_study_catalog" not in text_db:
    text_db = text_db.replace("def load_study_catalog(", "@lru_cache(maxsize=16)\ndef load_study_catalog(")
p_db.write_text(text_db, encoding="utf-8")
print("study_db.py patched with lru_cache")

# 2. Update analytics.py
p_an = Path("cultureroute/analytics.py")
text_an = p_an.read_text(encoding="utf-8")
if "from functools import lru_cache" not in text_an:
    text_an = text_an.replace("from collections import Counter\n", "from collections import Counter\nfrom functools import lru_cache\n")
for fn in ["compute_cultural_shares", "compute_weekly_forecast_backtest", "compute_footfall_imputation_study", "compute_price_descriptives"]:
    target = f"def {fn}("
    replacement = f"@lru_cache(maxsize=16)\ndef {fn}("
    if replacement not in text_an and target in text_an:
        text_an = text_an.replace(target, replacement)
p_an.write_text(text_an, encoding="utf-8")
print("analytics.py patched with lru_cache")

# 3. Update dev_lab.py
p_lab = Path("cultureroute/dev_lab.py")
text_lab = p_lab.read_text(encoding="utf-8")
if "from functools import lru_cache" not in text_lab:
    text_lab = text_lab.replace("from dataclasses import dataclass, field\n", "from dataclasses import dataclass, field\nfrom functools import lru_cache\n")
for fn in ["compute_canonical_saved_planned_merge", "compute_methodology_comparison", "get_table_profile"]:
    target = f"def {fn}("
    replacement = f"@lru_cache(maxsize=64)\ndef {fn}("
    if replacement not in text_lab and target in text_lab:
        text_lab = text_lab.replace(target, replacement)
p_lab.write_text(text_lab, encoding="utf-8")
print("dev_lab.py patched with lru_cache")
