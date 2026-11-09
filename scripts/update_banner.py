from pathlib import Path

app_path = Path(r"C:\SHARAN PROJECTS\Dev AAT\CultureRoute\app.py")
content = app_path.read_text(encoding="utf-8")

old_banner = """    # DEV Lab Station Navigator Guide
    st.markdown(\"\"\"
    <div style=\"background: #ffffff; border: 1.5px solid #b6afa3; border-top: 4px solid #982b32; padding: 16px 22px; margin-bottom: 18px; box-shadow: 2px 2px 0 rgba(41,41,37,0.04);\">
        <div style=\"display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px;\">
            <div style=\"font-family: Georgia, serif; font-size: 1.15rem; font-weight: bold; color: #292925;\">
                DEV Lab Interactive Stations &middot; Syllabus Units 1&ndash;5
            </div>
            <a href=\"?view=datasets\" target=\"_self\" style=\"font-size: 0.84rem; color: #982b32; text-decoration: none; font-weight: bold;\">
                &larr; Switch to Full 24-Table Dataset Catalog
            </a>
        </div>
        <p style=\"font-size: 0.85rem; color: #5c5852; margin: 6px 0 0; line-height: 1.55;\">
            Select any station tab below to inspect schema grains, execute live pandas transformations, test read-only SQL queries, or run hands-on syllabus examples.
        </p>
    </div>
    \"\"\", unsafe_allow_html=True)"""

new_banner = """    # Academic Workflow Interactive Banner
    st.markdown(\"\"\"
    <div style=\"background: #ffffff; border: 1.5px solid #b6afa3; border-left: 5px solid #982b32; padding: 18px 24px; margin-bottom: 16px; box-shadow: 2px 2px 0 rgba(41,41,37,0.04);\">
        <div style=\"display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px;\">
            <div style=\"font-family: Georgia, serif; font-size: 1.15rem; font-weight: bold; color: #292925;\">
                What You Can Do Here &middot; 6-Step Evaluator Workbench
            </div>
            <a href=\"?view=datasets\" target=\"_self\" style=\"font-size: 0.84rem; color: #982b32; text-decoration: none; font-weight: bold;\">
                &larr; Inspect Full 24-Table Dataset Catalog
            </a>
        </div>
        <p style=\"font-size: 0.86rem; color: #5c5852; margin: 8px 0 12px; line-height: 1.55;\">
            The DEV Lab is an interactive teaching workbench covering Syllabus Units 1&ndash;5.
            Follow the guided research path below to inspect schema grains, execute type-safe pandas derivations, run bounded SQL queries, and audit outer-join set partitions.
        </p>
        <div style=\"display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-size: 0.78rem; font-weight: bold; text-transform: uppercase;\">
            <a href=\"?view=datasets\" target=\"_self\" style=\"background: #eee3a6; padding: 5px 10px; border: 1px solid #dfd6a8; color: #982b32; text-decoration: none;\">1. Select in Catalog &rarr;</a>
            <span style=\"color: #736f66; padding: 4px 2px;\">&rarr;</span>
            <span style=\"background: #ffffff; padding: 5px 10px; border: 1px solid #b6afa3; color: #292925;\">2. Inspect (Tab 1)</span>
            <span style=\"color: #736f66; padding: 4px 2px;\">&rarr;</span>
            <span style=\"background: #ffffff; padding: 5px 10px; border: 1px solid #b6afa3; color: #292925;\">3. Transform (Tab 2)</span>
            <span style=\"color: #736f66; padding: 4px 2px;\">&rarr;</span>
            <span style=\"background: #ffffff; padding: 5px 10px; border: 1px solid #b6afa3; color: #292925;\">4. Compare (Tab 4)</span>
            <span style=\"color: #736f66; padding: 4px 2px;\">&rarr;</span>
            <span style=\"background: #ffffff; padding: 5px 10px; border: 1px solid #b6afa3; color: #292925;\">5. Chart (Tab 4)</span>
            <span style=\"color: #736f66; padding: 4px 2px;\">&rarr;</span>
            <span style=\"background: #ffffff; padding: 5px 10px; border: 1px solid #b6afa3; color: #292925;\">6. Explain & Export (Tabs 3 &amp; 5)</span>
        </div>
    </div>
    \"\"\", unsafe_allow_html=True)"""

content = content.replace(old_banner, new_banner)
app_path.write_text(content, encoding="utf-8")
print("Banner successfully updated!")
