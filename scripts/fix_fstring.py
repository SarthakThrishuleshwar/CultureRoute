from pathlib import Path

p = Path("cultureroute/ui_components.py")
text = p.read_text(encoding="utf-8")

# Replace single braces in the newly added block with double braces
old_block = """    /* Screen Auto-Stabilization: eliminate layout shifts and running flicker */
    [data-test-script-state="running"] [data-testid="stMain"],
    [data-test-script-state="running"] .main,
    [data-test-script-state="running"] [data-testid="stSidebar"],
    .stApp[data-test-script-state="running"] [data-testid="stAppViewBlockContainer"] {
        opacity: 1 !important;
        filter: none !important;
        transition: none !important;
    }

    /* Stabilize tab transitions and prevent jumping */
    [data-testid="stTabs"] {
        min-height: 480px;
    }
    [data-testid="stTabContent"] {
        animation: fadeIn 0.12s ease-in-out;
    }
    @keyframes fadeIn {
        from { opacity: 0.92; }
        to { opacity: 1; }
    }

    /* Innovative Pill styling */
    [data-testid="stPills"] {
        margin: 6px 0 10px !important;
    }
    [data-testid="stPills"] button,
    button[data-testid="stBaseButton-pills"] {
        border-radius: 20px !important;
        border: 1.5px solid var(--line) !important;
        background-color: #ffffff !important;
        color: var(--ink) !important;
        font-family: var(--body) !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        padding: 4px 14px !important;
        box-shadow: 1px 1px 0 rgba(41, 41, 37, 0.08) !important;
        transition: all 0.12s ease-in-out !important;
    }
    [data-testid="stPills"] button:hover,
    button[data-testid="stBaseButton-pills"]:hover {
        border-color: var(--red) !important;
        color: var(--red) !important;
        background-color: #fffaf7 !important;
        transform: translateY(-1px) !important;
        box-shadow: 1px 2px 4px rgba(152, 43, 50, 0.15) !important;
    }
    [data-testid="stPills"] button[aria-pressed="true"],
    button[data-testid="stBaseButton-pills"][aria-pressed="true"] {
        background-color: var(--red) !important;
        color: #ffffff !important;
        border-color: var(--red) !important;
        box-shadow: 2px 2px 0 #6e1c22 !important;
    }"""

new_block = """    /* Screen Auto-Stabilization: eliminate layout shifts and running flicker */
    [data-test-script-state="running"] [data-testid="stMain"],
    [data-test-script-state="running"] .main,
    [data-test-script-state="running"] [data-testid="stSidebar"],
    .stApp[data-test-script-state="running"] [data-testid="stAppViewBlockContainer"] {{
        opacity: 1 !important;
        filter: none !important;
        transition: none !important;
    }}

    /* Stabilize tab transitions and prevent jumping */
    [data-testid="stTabs"] {{
        min-height: 480px;
    }}
    [data-testid="stTabContent"] {{
        animation: fadeIn 0.12s ease-in-out;
    }}
    @keyframes fadeIn {{
        from {{ opacity: 0.92; }}
        to {{ opacity: 1; }}
    }}

    /* Innovative Pill styling */
    [data-testid="stPills"] {{
        margin: 6px 0 10px !important;
    }}
    [data-testid="stPills"] button,
    button[data-testid="stBaseButton-pills"] {{
        border-radius: 20px !important;
        border: 1.5px solid var(--line) !important;
        background-color: #ffffff !important;
        color: var(--ink) !important;
        font-family: var(--body) !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        padding: 4px 14px !important;
        box-shadow: 1px 1px 0 rgba(41, 41, 37, 0.08) !important;
        transition: all 0.12s ease-in-out !important;
    }}
    [data-testid="stPills"] button:hover,
    button[data-testid="stBaseButton-pills"]:hover {{
        border-color: var(--red) !important;
        color: var(--red) !important;
        background-color: #fffaf7 !important;
        transform: translateY(-1px) !important;
        box-shadow: 1px 2px 4px rgba(152, 43, 50, 0.15) !important;
    }}
    [data-testid="stPills"] button[aria-pressed="true"],
    button[data-testid="stBaseButton-pills"][aria-pressed="true"] {{
        background-color: var(--red) !important;
        color: #ffffff !important;
        border-color: var(--red) !important;
        box-shadow: 2px 2px 0 #6e1c22 !important;
    }}"""

assert old_block in text, "old_block not found in ui_components.py"
text = text.replace(old_block, new_block)
p.write_text(text, encoding="utf-8")
print("Successfully fixed f-string escaping in cultureroute/ui_components.py!")
