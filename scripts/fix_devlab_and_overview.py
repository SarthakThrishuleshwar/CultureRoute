import re
from pathlib import Path

DEV_LAB_PY = Path(r"C:\SHARAN PROJECTS\Dev AAT\CultureRoute\cultureroute\dev_lab.py")
APP_PY = Path(r"C:\SHARAN PROJECTS\Dev AAT\CultureRoute\app.py")

print("Patching dev_lab.py...")
dev_lab_content = DEV_LAB_PY.read_text(encoding="utf-8")

# 1. Add import time if missing
if "import time" not in dev_lab_content:
    dev_lab_content = dev_lab_content.replace("import sqlite3", "import sqlite3\nimport time", 1)

# 2. Update SQLQueryResult dataclass
old_sql_result = """@dataclass(frozen=True)
class SQLQueryResult:
    is_success: bool
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    is_truncated: bool
    error_message: Optional[str] = None"""

new_sql_result = """@dataclass(frozen=True)
class SQLQueryResult:
    is_success: bool
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    is_truncated: bool
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0"""

if old_sql_result in dev_lab_content:
    dev_lab_content = dev_lab_content.replace(old_sql_result, new_sql_result)
    print("Updated SQLQueryResult in dev_lab.py!")
else:
    # Regex fallback
    dev_lab_content = re.sub(
        r"@dataclass\(frozen=True\)\s+class SQLQueryResult:.*?error_message: Optional\[str\] = None",
        new_sql_result,
        dev_lab_content,
        flags=re.DOTALL
    )
    print("Regex updated SQLQueryResult in dev_lab.py!")

# 3. Update execute_query to measure execution time
old_exec_query_start = """    def execute_query(self, query: str) -> SQLQueryResult:
        \"\"\"Execute a single read-only SQL query inside the secured sandbox.\"\"\"
        clean_query = query.strip()"""

new_exec_query_start = """    def execute_query(self, query: str) -> SQLQueryResult:
        \"\"\"Execute a single read-only SQL query inside the secured sandbox.\"\"\"
        t0 = time.perf_counter()
        clean_query = query.strip()"""

dev_lab_content = dev_lab_content.replace(old_exec_query_start, new_exec_query_start)

# Update success return in execute_query
old_success_return = """            return SQLQueryResult(
                is_success=True,
                columns=columns,
                rows=[list(r) for r in output_rows],
                row_count=len(output_rows),
                is_truncated=is_truncated
            )"""

new_success_return = """            exec_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return SQLQueryResult(
                is_success=True,
                columns=columns,
                rows=[list(r) for r in output_rows],
                row_count=len(output_rows),
                is_truncated=is_truncated,
                execution_time_ms=exec_ms
            )"""

dev_lab_content = dev_lab_content.replace(old_success_return, new_success_return)
DEV_LAB_PY.write_text(dev_lab_content, encoding="utf-8")
print("dev_lab.py successfully patched!")

# 4. Patch app.py: DEV Lab top banner & sample run error handling
print("Patching app.py...")
app_content = APP_PY.read_text(encoding="utf-8")

# DEV Lab banner cleanup: remove non-clickable confusing text spans
old_devlab_banner = """    # Academic Workflow Interactive Banner
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
    \"\"\", unsafe_allow_html=True)

    # Guided Station Roadmaps pointing directly to the tabs below
    st_cols = st.columns(5)
    with st_cols[0]:
        st.markdown('<div style=\"background:#ffffff;border:1px solid #b6afa3;border-top:3px solid #982b32;padding:8px 10px;font-size:0.77rem;line-height:1.4;\"><strong>Tab 1 &middot; Profiler</strong><br><span style=\"color:#5c5852;\">Grains, keys & null counts across 24 tables</span></div>', unsafe_allow_html=True)
    with st_cols[1]:
        st.markdown('<div style=\"background:#ffffff;border:1px solid #b6afa3;border-top:3px solid #365376;padding:8px 10px;font-size:0.77rem;line-height:1.4;\"><strong>Tab 2 &middot; Transforms</strong><br><span style=\"color:#5c5852;\">pandas filtering, price tier binning & joins</span></div>', unsafe_allow_html=True)
    with st_cols[2]:
        st.markdown('<div style=\"background:#ffffff;border:1px solid #b6afa3;border-top:3px solid #b79d5b;padding:8px 10px;font-size:0.77rem;line-height:1.4;\"><strong>Tab 3 &middot; SQL Sandbox</strong><br><span style=\"color:#5c5852;\">Read-only SQLite query execution & benchmarks</span></div>', unsafe_allow_html=True)
    with st_cols[3]:
        st.markdown('<div style=\"background:#ffffff;border:1px solid #b6afa3;border-top:3px solid #7d6f58;padding:8px 10px;font-size:0.77rem;line-height:1.4;\"><strong>Tab 4 &middot; Visuals</strong><br><span style=\"color:#5c5852;\">Wilson CIs, category & action donuts, ECDFs</span></div>', unsafe_allow_html=True)
    with st_cols[4]:
        st.markdown('<div style=\"background:#ffffff;border:1px solid #b6afa3;border-top:3px solid #292925;padding:8px 10px;font-size:0.77rem;line-height:1.4;\"><strong>Tab 5 &middot; Formulas</strong><br><span style=\"color:#5c5852;\">Syllabus formulas & Parquet export code</span></div>', unsafe_allow_html=True)
    st.markdown('<div style=\"margin-bottom: 12px;\"></div>', unsafe_allow_html=True)"""

new_devlab_banner = """    # DEV Lab Station Navigator Guide
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

app_content = app_content.replace(old_devlab_banner, new_devlab_banner)

# Patch sample run in Tab 5
old_sample_run = """                if st.button(f"Run this example ({item['unit']})", key=f"btn_run_{item['unit']}"):
                    sandbox = ReadOnlySQLSandbox()
                    exec_res = sandbox.execute_query(item["preset_query"])
                    if exec_res.is_success:
                        st.success(f"Executed in {exec_res.execution_time_ms:.1f}ms ({exec_res.row_count} rows returned):")
                        if exec_res.rows:
                            res_df = pd.DataFrame(exec_res.rows, columns=exec_res.columns)
                            st.dataframe(res_df, hide_index=True, use_container_width=True)
                    else:
                        st.error(f"Execution Error: {exec_res.error_message}")"""

new_sample_run = """                if st.button(f"Run this example ({item['unit']})", key=f"btn_run_{item['unit']}"):
                    try:
                        sandbox = ReadOnlySQLSandbox()
                        exec_res = sandbox.execute_query(item["preset_query"])
                        if exec_res.is_success:
                            time_ms = getattr(exec_res, "execution_time_ms", 0.0)
                            st.success(f"Executed in {time_ms:.1f}ms ({exec_res.row_count} rows returned):")
                            if exec_res.rows:
                                res_df = pd.DataFrame(exec_res.rows, columns=exec_res.columns)
                                st.dataframe(res_df, hide_index=True, use_container_width=True)
                        else:
                            st.error(f"Execution Error: {exec_res.error_message}")
                    except Exception as ex:
                        st.error(f"Execution Exception: {ex}")"""

app_content = app_content.replace(old_sample_run, new_sample_run)

# Also update the FAQ in Overview to remove outdated "ML omitted" claim
old_faq_ml = """    with st.expander("Why are artificial intelligence and machine learning models omitted?"):
        st.write(
            "In strict accordance with project specifications, CultureRoute uses explicit constraint rules, directed matrix legs, "
            "and conventional statistical methods (Wilson score intervals, Beta-Binomial Bayesian models, lognormal MLE estimation, "
            "and moving-average forecasting). All calculations are completely transparent and verifiable."
        )"""

new_faq_ml = """    with st.expander("How does CultureRoute predict weekly cultural demand?"):
        st.write(
            "CultureRoute incorporates a trained, regularized Poisson count regression model (Prediction Model view) "
            "evaluated with strict chronological zero-leakage holdout splits across 45 Indian study cities and 57 complete weeks. "
            "Routing remains purely deterministic and rules-based to ensure 100% reproducible itineraries."
        )"""

app_content = app_content.replace(old_faq_ml, new_faq_ml)

APP_PY.write_text(app_content, encoding="utf-8")
print("app.py successfully patched!")
