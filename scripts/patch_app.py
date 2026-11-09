import re
from pathlib import Path

app_path = Path(r"C:\SHARAN PROJECTS\Dev AAT\CultureRoute\app.py")
content = app_path.read_text(encoding="utf-8")

# 1. Update imports if needed
if "from PIL import Image" not in content:
    content = content.replace("import streamlit as st", "from PIL import Image\nimport streamlit as st", 1)

# 2. Update page configuration
new_cfg = """# Page Configuration
FAVICON_PNG = Path(__file__).resolve().parent / "site" / "dist" / "assets" / "favicon.png"
fav_img = None
if FAVICON_PNG.exists():
    try:
        fav_img = Image.open(FAVICON_PNG)
    except Exception:
        fav_img = None

st.set_page_config(
    page_title="CultureRoute · Cultural Day Trip Planner & DEV Lab",
    page_icon=fav_img if fav_img is not None else None,
    layout="wide",
    initial_sidebar_state="expanded",
)"""

content = re.sub(
    r"# Page Configuration\r?\nFAVICON_PATH =.*?\r?\nst\.set_page_config\(.*?\r?\n\)",
    new_cfg,
    content,
    flags=re.DOTALL
)

app_path.write_text(content, encoding="utf-8")
print("app.py successfully patched!")
