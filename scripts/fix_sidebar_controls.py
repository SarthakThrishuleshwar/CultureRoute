from pathlib import Path

p = Path("cultureroute/ui_components.py")
text = p.read_text(encoding="utf-8")

# 1. Fix the header clutter hiding rule (remove button[kind="header"])
old_clutter = """    /* Hide Deploy button and Streamlit menu clutter without destroying the sidebar expand trigger */
    .stDeployButton,
    [data-testid="stDeployButton"],
    .stAppDeployButton,
    [data-testid="stAppDeployButton"],
    button[data-testid="stAppDeployButton"],
    button[kind="header"],
    [data-testid="stToolbarActions"],
    [data-testid="stHeaderActionElements"],
    [data-testid="stDecoration"],
    #MainMenu,
    footer {"""

new_clutter = """    /* Hide Deploy button and Streamlit menu clutter while preserving sidebar collapse and expand buttons */
    .stDeployButton,
    [data-testid="stDeployButton"],
    .stAppDeployButton,
    [data-testid="stAppDeployButton"],
    button[data-testid="stAppDeployButton"],
    .stToolbarActions,
    [data-testid="stToolbarActions"],
    [data-testid="stHeaderActionElements"],
    [data-testid="stDecoration"],
    #MainMenu,
    footer {"""

# Handle both single and double curly braces
if old_clutter.replace("{", "{{") in text:
    text = text.replace(old_clutter.replace("{", "{{"), new_clutter.replace("{", "{{"))
elif old_clutter in text:
    text = text.replace(old_clutter, new_clutter)

# 2. Fix the header styling (do not set height: 0 which clips the expand button)
old_header = """    header[data-testid="stHeader"],
    [data-testid="stHeader"] {{
        background: transparent !important;
        height: 0 !important;
        min-height: 0 !important;
        border: none !important;
        box-shadow: none !important;
    }}"""

new_header = """    header[data-testid="stHeader"],
    [data-testid="stHeader"] {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        z-index: 99999 !important;
    }}"""

if old_header in text:
    text = text.replace(old_header, new_header)

# 3. Replace the pinned sidebar and floating toggle rules with clean native collapse/expand rules
old_pinned_block = """    /* Pinned and permanent sidebar on desktop screens (>= 769px) */
    @media (min-width: 769px) {{
        [data-testid="stSidebar"],
        section[data-testid="stSidebar"] {{
            position: relative !important;
            transform: none !important;
            margin-left: 0 !important;
            width: 290px !important;
            min-width: 290px !important;
            max-width: 290px !important;
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            box-shadow: 2px 0 12px rgba(41, 41, 37, 0.06) !important;
        }}

        [data-testid="stSidebar"] > div {{
            width: 290px !important;
            min-width: 290px !important;
            transform: none !important;
        }}

        [data-testid="stAppViewContainer"] {{
            margin-left: 0 !important;
        }}

        [data-testid="stExpandSidebarButton"] {{
            display: none !important;
        }}
    }}

    /* Tactile floating navigation toggle on smaller screens or when collapsed */
    [data-testid="stExpandSidebarButton"],
    button[data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapsedControl"] {{
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        position: fixed !important;
        top: 14px !important;
        left: 14px !important;
        z-index: 9999999 !important;
        background-color: var(--yellow) !important;
        color: var(--red) !important;
        border: 2px solid var(--red) !important;
        border-radius: 4px !important;
        box-shadow: 3px 3px 0 var(--red) !important;
        padding: 8px 14px !important;
        font-family: var(--display) !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        cursor: pointer !important;
        align-items: center !important;
        gap: 8px !important;
        pointer-events: auto !important;
        width: auto !important;
        height: auto !important;
    }}

    [data-testid="stExpandSidebarButton"]:hover {{
        background-color: #fff9ee !important;
        transform: translate(2px, 2px) !important;
        box-shadow: 1px 1px 0 var(--red) !important;
    }}

    [data-testid="stExpandSidebarButton"]:after {{
        content: " Navigation Menu" !important;
        font-family: var(--display) !important;
        font-size: 0.92rem !important;
        font-weight: 700 !important;
        color: var(--red) !important;
    }}"""

new_pinned_block = """    /* Sidebar Theme & Controls (fully supporting native open/close toggle) */
    [data-testid="stSidebar"],
    section[data-testid="stSidebar"] {{
        background-color: #f0ebe0 !important;
        border-right: 1.5px solid var(--line) !important;
        box-shadow: 2px 0 12px rgba(41, 41, 37, 0.06) !important;
    }}

    /* Sidebar Collapse Button (inside sidebar header) */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapseButton"] button {{
        display: inline-flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        background-color: var(--yellow) !important;
        color: var(--red) !important;
        border: 1.5px solid var(--red) !important;
        border-radius: 4px !important;
        box-shadow: 2px 2px 0 var(--red) !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
    }}
    [data-testid="stSidebarCollapseButton"] button:hover {{
        background-color: #fffaf0 !important;
        transform: translate(1px, 1px) !important;
        box-shadow: 1px 1px 0 var(--red) !important;
    }}

    /* Sidebar Expand Button (visible when sidebar is closed) */
    [data-testid="stExpandSidebarButton"],
    button[data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapsedControl"] {{
        display: inline-flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        background-color: var(--yellow) !important;
        color: var(--red) !important;
        border: 2px solid var(--red) !important;
        border-radius: 4px !important;
        box-shadow: 2px 2px 0 var(--red) !important;
        padding: 6px 12px !important;
        font-family: var(--display) !important;
        font-size: 0.9rem !important;
        font-weight: 700 !important;
        cursor: pointer !important;
        z-index: 999999 !important;
        transition: all 0.15s ease !important;
    }}
    [data-testid="stExpandSidebarButton"]:hover,
    button[data-testid="stExpandSidebarButton"]:hover {{
        background-color: #fffaf0 !important;
        transform: translate(1px, 1px) !important;
        box-shadow: 1px 1px 0 var(--red) !important;
    }}"""

if old_pinned_block in text:
    text = text.replace(old_pinned_block, new_pinned_block)
    print("Pinned block replaced successfully!")
else:
    print("Warning: old_pinned_block not found verbatim, checking alternatives")

p.write_text(text, encoding="utf-8")
print("Finished updating cultureroute/ui_components.py")
