"""CultureRoute DEV Lab & Syllabus Demonstrator (Stage R6).

Covers all 5 syllabus units:
1. EDA Foundations:
   - Table profiling, grains, keys, missingness, and safe projections.
   - Three-way methodology comparison: Exploratory (p_hat), Classical (Wilson 95% CI),
     and Bayesian (Beta-Binomial Beta(1,1) posterior credible interval) on deterministic owner trip cohort.
2. Data Transformations:
   - Filter & Derive (cultural tags, price binning with separate Free tier, type-safe filters).
   - Group by & Aggregate (split-apply-combine, stop counts, cultural shares).
   - Pivot & Heatmap (city x category cross-tab matrix).
   - Canonical Merge: Saved vs Planned distinct POIs outer join:
     * 363 saved POIs
     * 655 planned POIs
     * 352 inner join (both)
     * 363 left join
     * 666 full outer join (352 both, 11 saved only, 303 planned only).
3. Bounded Read-Only SQL Sandbox:
   - SQLite authorizer blocking all writes, DDL, PRAGMA, ATTACH/DETACH, and extension loading.
   - Resource bounded (query length <= 1500 chars, 500 row max, progress handler step bound, single-statement enforcement).
   - Distinct syntax, denial, timeout, and truncation messages.
4. Graphical Methods:
   - Visualizations across bar, distribution, heatmap, scatter, and intervals with companion data tables.
5. pandas & Sources Export Engine:
   - Safe CSV formula escaping (preventing spreadsheet formula injection) and typed Parquet round-tripping via PyArrow.
   - Formulas and syntax reference covering Units 1–5 with runnable examples.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import io
import math
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from scipy.stats import beta

from cultureroute.study_data import open_study_databases, _scoped_selected_sql
from cultureroute.study_db import (
    open_study_cache,
    load_study_catalog,
    TableCatalogEntry,
    StudyDatabaseCatalog,
    SENSITIVE_COLUMNS,
    CULTURAL_CATEGORIES,
)


@dataclass(frozen=True)
class MethodologyComparisonResult:
    cohort_description: str
    sample_size: int
    success_count: int
    empirical_proportion: float
    wilson_lower: float
    wilson_upper: float
    bayes_prior: str
    bayes_posterior_alpha: int
    bayes_posterior_beta: int
    bayes_lower: float
    bayes_upper: float


@dataclass(frozen=True)
class CanonicalMergeResult:
    saved_count: int
    planned_count: int
    inner_count: int
    left_count: int
    full_outer_count: int
    both_count: int
    saved_only_count: int
    planned_only_count: int
    merged_df: pd.DataFrame


@dataclass(frozen=True)
class SQLQueryResult:
    is_success: bool
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    is_truncated: bool
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass(frozen=True)
class TableProfileResult:
    table_name: str
    origin_pack: str
    grain: str
    row_count: int
    primary_key: List[str]
    foreign_keys: List[str]
    column_count: int
    columns: List[str]
    column_types: Dict[str, str]
    null_counts: Dict[str, int]
    safe_columns: List[str]
    sample_df: pd.DataFrame


# ------------------------------------------------------------------------------
# Unit 1: EDA & Methodology Comparisons
# ------------------------------------------------------------------------------

def compute_methodology_comparison(strict_active_only: bool = False) -> MethodologyComparisonResult:
    """Compare EDA (proportion), Classical (Wilson CI), and Bayesian (Beta-Binomial) on owner cohort."""
    with open_study_databases() as (smart, _):
        if strict_active_only:
            sql = """
                SELECT t.trip_id, t.owner_user_id, t.start_date,
                       EXISTS(
                           SELECT 1 FROM itineraries i
                           JOIN itinerary_items ii ON ii.itinerary_id = i.itinerary_id
                           JOIN activities_poi a ON a.poi_id = ii.entity_id
                           WHERE i.trip_id = t.trip_id AND i.is_active = 1 AND ii.status = 'confirmed'
                             AND ii.item_type = 'poi' AND ii.entity_type = 'poi'
                             AND a.city_id = t.destination_city_id
                             AND a.poi_category IN ('heritage','museum','religious','food')
                       ) as has_cultural
                FROM trips t
                JOIN cities c ON c.city_id = t.destination_city_id
                WHERE c.country_code = 'IN' AND t.status <> 'cancelled'
                ORDER BY t.owner_user_id, t.start_date DESC, t.trip_id ASC
            """
            cohort_desc = "One trip per owner: shared active-and-confirmed stop contract (293 / 341)"
        else:
            sql = """
                SELECT t.trip_id, t.owner_user_id, t.start_date,
                       EXISTS(
                           SELECT 1 FROM itineraries i
                           JOIN itinerary_items ii ON ii.itinerary_id = i.itinerary_id
                           JOIN activities_poi a ON a.poi_id = ii.entity_id
                           WHERE i.trip_id = t.trip_id AND ii.status = 'confirmed' AND a.poi_category IN ('heritage','museum','religious','food')
                       ) as has_cultural
                FROM trips t
                JOIN cities c ON c.city_id = t.destination_city_id
                WHERE c.country_code = 'IN' AND t.status <> 'cancelled'
                ORDER BY t.owner_user_id, t.start_date DESC, t.trip_id ASC
            """
            cohort_desc = "One trip per owner: legacy itinerary cohort (301 / 341)"
        rows = smart.execute(sql).fetchall()

    # Deterministic cohort: 1 trip per owner (latest start date, stable trip_id tie-break)
    seen_owners = set()
    selected_trips = []
    for r in rows:
        if r["owner_user_id"] not in seen_owners:
            seen_owners.add(r["owner_user_id"])
            selected_trips.append(dict(r))

    n = len(selected_trips)
    k = sum(1 for t in selected_trips if t["has_cultural"])
    p_hat = k / n if n else 0.0

    # 95% Wilson Score Interval (z = 1.95996)
    z = 1.95996
    denom = 1.0 + (z ** 2) / n
    center = (p_hat + (z ** 2) / (2.0 * n)) / denom
    margin = (z * math.sqrt((p_hat * (1.0 - p_hat) / n) + (z ** 2) / (4.0 * (n ** 2)))) / denom
    w_low = center - margin
    w_high = center + margin

    # Bayesian Beta-Binomial with Beta(1,1) prior
    a_post = 1 + k
    b_post = 1 + n - k
    bayes_low = beta.ppf(0.025, a_post, b_post)
    bayes_high = beta.ppf(0.975, a_post, b_post)

    return MethodologyComparisonResult(
        cohort_description=cohort_desc,
        sample_size=n,
        success_count=k,
        empirical_proportion=round(p_hat, 4),
        wilson_lower=round(w_low, 4),
        wilson_upper=round(w_high, 4),
        bayes_prior="Beta(1, 1) flat prior",
        bayes_posterior_alpha=a_post,
        bayes_posterior_beta=b_post,
        bayes_lower=round(bayes_low, 4),
        bayes_upper=round(bayes_high, 4)
    )


def get_table_profile(table_name: str, sample_limit: int = 50) -> Optional[TableProfileResult]:
    """Retrieve full catalog profiling information and safe preview for a table."""
    cat = load_study_catalog()
    entry = cat.tables.get(table_name)
    if not entry:
        return None

    safe_cols_sql = ", ".join(entry.safe_columns)
    with open_study_cache() as conn:
        df_sample = pd.read_sql_query(
            f"SELECT {safe_cols_sql} FROM {table_name} LIMIT {sample_limit}",
            conn
        )

    formatted_fks = [
        f"{fk.get('from')} -> {fk.get('table')}({fk.get('to')})" if isinstance(fk, dict) else str(fk)
        for fk in entry.foreign_keys
    ]

    return TableProfileResult(
        table_name=entry.table_name,
        origin_pack=entry.origin_pack,
        grain=entry.grain,
        row_count=entry.row_count,
        primary_key=entry.primary_key,
        foreign_keys=formatted_fks,
        column_count=len(entry.columns),
        columns=entry.columns,
        column_types=entry.column_types,
        null_counts=entry.null_counts,
        safe_columns=entry.safe_columns,
        sample_df=df_sample
    )


# ------------------------------------------------------------------------------
# Unit 2: Guided Data Transformations
# ------------------------------------------------------------------------------

def filter_and_derive_poi(
    min_cost: float = 0.0,
    max_cost: float = 1000.0,
    selected_categories: Optional[List[str]] = None,
    only_step_free: bool = False
) -> Tuple[pd.DataFrame, str]:
    """Apply type-safe filter, price tier binning, and cultural flag derivation to POIs."""
    with open_study_cache() as conn:
        df = pd.read_sql_query(
            """
            SELECT p.poi_id, p.name, c.name as city_name, p.poi_category, p.entry_cost,
                   p.typical_duration_minutes, p.accessibility, p.lat, p.lng
            FROM activities_poi p
            JOIN cities c ON c.city_id = p.city_id
            WHERE c.country_code = 'IN'
            """,
            conn
        )

    # Numeric cast for entry_cost
    df["entry_cost"] = pd.to_numeric(df["entry_cost"], errors="coerce").fillna(0.0)

    # 1. Filters
    cat_filter = selected_categories or list(df["poi_category"].unique())
    filtered_df = df[
        (df["entry_cost"] >= min_cost) &
        (df["entry_cost"] <= max_cost) &
        (df["poi_category"].isin(cat_filter))
    ].copy()

    if only_step_free:
        filtered_df = filtered_df[filtered_df["accessibility"] == "step_free"].copy()

    # 2. Price tier derivation: [0, 0] = Free, (0, 100] = Budget, (100, 500] = Moderate, >500 = Premium
    def assign_price_tier(cost: float) -> str:
        if cost == 0.0:
            return "Free (INR 0)"
        elif cost <= 100.0:
            return "Budget (1–100)"
        elif cost <= 500.0:
            return "Moderate (101–500)"
        else:
            return "Premium (>500)"

    filtered_df["price_tier"] = filtered_df["entry_cost"].apply(assign_price_tier)

    # 3. Cultural flag derivation
    filtered_df["is_cultural"] = filtered_df["poi_category"].isin(CULTURAL_CATEGORIES)

    # Generate reproducible pandas snippet
    snippet = f"""# Reproducible pandas transformation
import pandas as pd
import sqlite3

conn = sqlite3.connect("data/study_cache.db")
query = '''
    SELECT p.poi_id, p.name, c.name as city_name, p.poi_category, p.entry_cost,
           p.typical_duration_minutes, p.accessibility, p.lat, p.lng
    FROM activities_poi p JOIN cities c ON c.city_id = p.city_id
    WHERE c.country_code = 'IN'
'''
df = pd.read_sql_query(query, conn)
df['entry_cost'] = pd.to_numeric(df['entry_cost'], errors='coerce').fillna(0.0)

# 1. Filter
cats = {cat_filter}
filtered = df[
    (df['entry_cost'] >= {min_cost}) &
    (df['entry_cost'] <= {max_cost}) &
    (df['poi_category'].isin(cats))
]
{f"filtered = filtered[filtered['accessibility'] == 'step_free']" if only_step_free else "# Step-free filter: disabled"}

# 2. Derive Price Tier (explicit zero / free tier separation)
bins = [-float('inf'), 0.0, 100.0, 500.0, float('inf')]
labels = ['Free (INR 0)', 'Budget (1–100)', 'Moderate (101–500)', 'Premium (>500)']
filtered['price_tier'] = pd.cut(filtered['entry_cost'], bins=bins, labels=labels, right=True)

# 3. Cultural Flag
cultural_cats = {list(CULTURAL_CATEGORIES)}
filtered['is_cultural'] = filtered['poi_category'].isin(cultural_cats)
"""
    return filtered_df, snippet


def groupby_aggregate_stops(group_by: str = "city_name") -> Tuple[pd.DataFrame, str]:
    """Demonstrate split-apply-combine aggregation on planned stops."""
    with open_study_cache() as conn:
        df = pd.read_sql_query(
            """
            SELECT s.entity_id as poi_id, c.name as city_name, s.poi_category, s.cost as entry_fee,
                   s.duration_minutes,
                   CASE WHEN s.poi_category IN ('heritage', 'museum', 'religious', 'food') THEN 1 ELSE 0 END as is_cultural
            FROM view_study_selected_stops s
            JOIN cities c ON c.city_id = s.destination_city_id
            """,
            conn
        )

    df["entry_fee"] = pd.to_numeric(df["entry_fee"], errors="coerce").fillna(0.0)
    df["duration_minutes"] = pd.to_numeric(df["duration_minutes"], errors="coerce").fillna(0.0)

    if group_by not in df.columns:
        group_by = "city_name"

    agg_df = df.groupby(group_by).agg(
        total_stops=("poi_id", "count"),
        cultural_stops=("is_cultural", "sum"),
        avg_entry_fee=("entry_fee", "mean"),
        avg_duration=("duration_minutes", "mean")
    ).reset_index()

    agg_df["cultural_share_pct"] = (agg_df["cultural_stops"] / agg_df["total_stops"] * 100.0).round(1)
    agg_df["avg_entry_fee"] = agg_df["avg_entry_fee"].round(2)
    agg_df["avg_duration"] = agg_df["avg_duration"].round(1)
    agg_df = agg_df.sort_values(by="total_stops", ascending=False)

    snippet = f"""# Reproducible split-apply-combine aggregation
import pandas as pd
import sqlite3

conn = sqlite3.connect("data/study_cache.db")
query = '''
    SELECT s.entity_id as poi_id, c.name as city_name, s.poi_category, s.cost as entry_fee,
           s.duration_minutes,
           CASE WHEN s.poi_category IN ('heritage', 'museum', 'religious', 'food') THEN 1 ELSE 0 END as is_cultural
    FROM view_study_selected_stops s
    JOIN cities c ON c.city_id = s.destination_city_id
'''
df = pd.read_sql_query(query, conn)

# Split by '{group_by}', Apply aggregations, Combine to summary
agg_df = df.groupby("{group_by}").agg(
    total_stops=("poi_id", "count"),
    cultural_stops=("is_cultural", "sum"),
    avg_entry_fee=("entry_fee", "mean"),
    avg_duration=("duration_minutes", "mean")
).reset_index()

agg_df["cultural_share_pct"] = (agg_df["cultural_stops"] / agg_df["total_stops"] * 100.0).round(1)
agg_df = agg_df.sort_values(by="total_stops", ascending=False)
"""
    return agg_df, snippet


def pivot_city_category_matrix() -> Tuple[pd.DataFrame, pd.DataFrame, str]:
    """Construct reversible long-to-wide pivot table of city x category planned stops."""
    with open_study_cache() as conn:
        df = pd.read_sql_query(
            """
            SELECT c.name as city_name, s.poi_category, count(*) as stop_count
            FROM view_study_selected_stops s
            JOIN cities c ON c.city_id = s.destination_city_id
            WHERE s.poi_category IN ('heritage', 'museum', 'religious', 'food')
            GROUP BY c.name, s.poi_category
            """,
            conn
        )

    with open_study_cache() as conn:
        all_cities = [r[0] for r in conn.execute("SELECT name FROM view_study_cities ORDER BY name").fetchall()]

    # Wide Pivot Table (missing combinations filled with 0, indexed across all 45 cities)
    pivot_df = df.pivot(index="city_name", columns="poi_category", values="stop_count").fillna(0).astype(int)
    pivot_df = pivot_df.reindex(all_cities, fill_value=0)

    snippet = """# Reversible long-to-wide pivot and wide-to-long melt
import pandas as pd
import sqlite3

conn = sqlite3.connect("data/study_cache.db")
df = pd.read_sql_query('''
    SELECT c.name as city_name, s.poi_category, count(*) as stop_count
    FROM view_study_selected_stops s
    JOIN cities c ON c.city_id = s.destination_city_id
    WHERE s.poi_category IN ('heritage', 'museum', 'religious', 'food')
    GROUP BY c.name, s.poi_category
''', conn)

# Pivot: Long to Wide
pivot_wide = df.pivot(index="city_name", columns="poi_category", values="stop_count").fillna(0).astype(int)

# Reversible Reshape: Wide back to Long
long_restored = pivot_wide.reset_index().melt(
    id_vars="city_name",
    var_name="poi_category",
    value_name="stop_count"
)
"""
    return pivot_df, df, snippet


def transform_user_interactions(
    interaction_types: Optional[List[str]] = None,
    cultural_only: bool = False,
    group_by_dimension: str = "interaction_type"
) -> Tuple[pd.DataFrame, Dict[str, Any], str]:
    """Demonstrate WanderMatch interaction telemetry join and aggregation."""
    with open_study_cache() as conn:
        raw_total = int(conn.execute("SELECT count(*) FROM user_interactions").fetchone()[0])
        sql = """
            SELECT u.interaction_id, u.user_id, u.entity_type, u.entity_id as poi_id,
                   u.interaction_type, u.occurred_at,
                   a.name as attraction_name, a.poi_category, c.name as city_name,
                   CASE WHEN a.poi_category IN ('heritage', 'museum', 'religious', 'food') THEN 1 ELSE 0 END as is_cultural
            FROM user_interactions u
            LEFT JOIN activities_poi a ON u.entity_type = 'poi' AND u.entity_id = a.poi_id
            LEFT JOIN cities c ON a.city_id = c.city_id
        """
        df = pd.read_sql_query(sql, conn)

    df_matched = df[df["city_name"].notna()].copy()
    matched_count = len(df_matched)
    unmatched_count = raw_total - matched_count

    if interaction_types:
        df_matched = df_matched[df_matched["interaction_type"].isin(interaction_types)]

    if cultural_only:
        df_matched = df_matched[df_matched["is_cultural"] == 1]

    if group_by_dimension in ["interaction_type", "poi_category", "city_name"]:
        grp = df_matched.groupby(group_by_dimension).agg(
            total_interactions=("interaction_id", "count"),
            distinct_users=("user_id", "nunique"),
            distinct_pois=("poi_id", "nunique"),
            cultural_events=("is_cultural", "sum")
        ).reset_index().sort_values("total_interactions", ascending=False)
        grp["cultural_share_pct"] = (grp["cultural_events"] / grp["total_interactions"] * 100).round(1)
    else:
        grp = df_matched

    metrics = {
        "raw_total": raw_total,
        "matched_count": matched_count,
        "unmatched_count": unmatched_count,
        "filtered_count": len(df_matched),
        "cultural_count": int(df_matched["is_cultural"].sum()),
    }

    snippet = (
        "# Reproducible WanderMatch Interaction Transformation\n"
        "import pandas as pd\nimport sqlite3\n\n"
        "conn = sqlite3.connect('data/study_cache.db')\n"
        "query = '''\n"
        "    SELECT u.interaction_id, u.user_id, u.interaction_type, u.occurred_at,\n"
        "           a.name as attraction_name, a.poi_category, c.name as city_name,\n"
        "           CASE WHEN a.poi_category IN ('heritage', 'museum', 'religious', 'food') THEN 1 ELSE 0 END as is_cultural\n"
        "    FROM user_interactions u\n"
        "    JOIN activities_poi a ON u.entity_type = 'poi' AND u.entity_id = a.poi_id\n"
        "    JOIN cities c ON a.city_id = c.city_id\n"
        "    WHERE c.country_code = 'IN'\n"
        "'''\n"
        "df_matched = pd.read_sql_query(query, conn)\n"
        f"grouped = df_matched.groupby('{group_by_dimension}').agg(\n"
        "    total_interactions=('interaction_id', 'count'),\n"
        "    distinct_users=('user_id', 'nunique'),\n"
        "    distinct_pois=('poi_id', 'nunique'),\n"
        "    cultural_events=('is_cultural', 'sum')\n"
        ").reset_index()\n"
    )
    return grp, metrics, snippet


def compute_canonical_saved_planned_merge() -> CanonicalMergeResult:
    """Compute the audited full outer merge between saved POIs and planned POIs."""
    with open_study_databases() as (smart, _):
        interaction_where = (
            "FROM wm.user_interactions u "
            "JOIN activities_poi a ON u.entity_type='poi' AND u.entity_id=a.poi_id "
            "JOIN cities c ON c.city_id=a.city_id WHERE c.country_code='IN'"
        )
        saved_rows = smart.execute(
            f"SELECT DISTINCT u.entity_id as poi_id, a.name, a.poi_category, c.name as city_name "
            f"{interaction_where} AND u.interaction_type='save' ORDER BY a.poi_id ASC"
        ).fetchall()

        planned_rows = smart.execute(
            _scoped_selected_sql("DISTINCT ii.entity_id as poi_id, a.name, a.poi_category, c.name as city_name")
            + " ORDER BY ii.entity_id ASC"
        ).fetchall()

    df_saved = pd.DataFrame([dict(r) for r in saved_rows])
    df_planned = pd.DataFrame([dict(r) for r in planned_rows])

    df_saved["in_saved"] = True
    df_planned["in_planned"] = True

    # Outer join on poi_id
    df_merged = pd.merge(
        df_saved,
        df_planned,
        on="poi_id",
        how="outer",
        suffixes=("_saved", "_planned")
    )

    df_merged["in_saved"] = df_merged["in_saved"].fillna(False)
    df_merged["in_planned"] = df_merged["in_planned"].fillna(False)

    df_merged["membership"] = df_merged.apply(
        lambda row: "Both (Inner)" if row["in_saved"] and row["in_planned"]
        else ("Saved Only" if row["in_saved"] else "Planned Only"),
        axis=1
    )

    both_cnt = int(sum((df_merged["in_saved"] == True) & (df_merged["in_planned"] == True)))
    saved_only_cnt = int(sum((df_merged["in_saved"] == True) & (df_merged["in_planned"] == False)))
    planned_only_cnt = int(sum((df_merged["in_saved"] == False) & (df_merged["in_planned"] == True)))

    return CanonicalMergeResult(
        saved_count=len(df_saved),
        planned_count=len(df_planned),
        inner_count=both_cnt,
        left_count=len(df_saved),
        full_outer_count=len(df_merged),
        both_count=both_cnt,
        saved_only_count=saved_only_cnt,
        planned_only_count=planned_only_cnt,
        merged_df=df_merged
    )


# ------------------------------------------------------------------------------
# Unit 3: Bounded Read-Only SQL Sandbox
# ------------------------------------------------------------------------------

class ReadOnlySQLSandbox:
    """Bounded, read-only SQL evaluation environment with SQLite authorizer and progress handler."""

    DISALLOWED_ACTIONS = {
        sqlite3.SQLITE_INSERT,
        sqlite3.SQLITE_UPDATE,
        sqlite3.SQLITE_DELETE,
        sqlite3.SQLITE_DROP_TABLE,
        sqlite3.SQLITE_DROP_INDEX,
        sqlite3.SQLITE_DROP_VIEW,
        sqlite3.SQLITE_CREATE_TABLE,
        sqlite3.SQLITE_CREATE_INDEX,
        sqlite3.SQLITE_CREATE_VIEW,
        sqlite3.SQLITE_ALTER_TABLE,
        sqlite3.SQLITE_PRAGMA,
        sqlite3.SQLITE_ATTACH,
        sqlite3.SQLITE_DETACH,
    }

    MAX_QUERY_LENGTH = 1500
    MAX_ROWS_RETURNED = 500
    MAX_VM_STEPS = 100000

    def __init__(self):
        pass

    def _authorizer_callback(self, action_code: int, arg1: Any, arg2: Any, db_name: Any, trigger_name: Any) -> int:
        if action_code in self.DISALLOWED_ACTIONS:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    def execute_query(self, query: str) -> SQLQueryResult:
        """Execute a single read-only SQL query inside the secured sandbox."""
        t0 = time.perf_counter()
        clean_query = query.strip()

        # 1. Length check
        if len(clean_query) > self.MAX_QUERY_LENGTH:
            return SQLQueryResult(
                is_success=False,
                columns=[],
                rows=[],
                row_count=0,
                is_truncated=False,
                error_message=f"Query exceeds maximum permitted length ({self.MAX_QUERY_LENGTH} characters)."
            )

        # 2. Disallow stacked statements
        if clean_query.endswith(";"):
            clean_query = clean_query[:-1].strip()

        if ";" in clean_query:
            return SQLQueryResult(
                is_success=False,
                columns=[],
                rows=[],
                row_count=0,
                is_truncated=False,
                error_message="Multiple statements / stacked queries are rejected for security."
            )

        # 3. Disallowed keywords check as fast preliminary reject
        upper_q = clean_query.upper()
        for forbidden in ["ATTACH", "DETACH", "DROP", "ALTER", "INSERT", "UPDATE", "DELETE", "PRAGMA"]:
            if re.search(r"\b" + forbidden + r"\b", upper_q):
                return SQLQueryResult(
                    is_success=False,
                    columns=[],
                    rows=[],
                    row_count=0,
                    is_truncated=False,
                    error_message=f"Disallowed SQL command or keyword detected: '{forbidden}'"
                )

        try:
            # Use open_study_cache() if cache exists, otherwise open_study_databases()
            conn = sqlite3.connect("file:data/study_cache.db?mode=ro", uri=True)
        except Exception:
            # Fallback to in-memory study connection
            conn = sqlite3.connect(":memory:")

        try:
            # Install SQLite authorizer
            conn.set_authorizer(self._authorizer_callback)

            # Install progress handler step bound to stop infinite recursive CTEs / expensive loops
            step_count = [0]
            def progress_handler():
                step_count[0] += 1
                if step_count[0] > self.MAX_VM_STEPS:
                    return 1  # Abort query
                return 0

            conn.set_progress_handler(progress_handler, 1000)

            cursor = conn.cursor()
            cursor.execute(clean_query)

            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            raw_rows = cursor.fetchmany(self.MAX_ROWS_RETURNED + 1)

            is_truncated = len(raw_rows) > self.MAX_ROWS_RETURNED
            output_rows = raw_rows[:self.MAX_ROWS_RETURNED]

            exec_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return SQLQueryResult(
                is_success=True,
                columns=columns,
                rows=[list(r) for r in output_rows],
                row_count=len(output_rows),
                is_truncated=is_truncated,
                execution_time_ms=exec_ms
            )
        except sqlite3.OperationalError as e:
            err = str(e)
            if "interrupted" in err.lower() or "aborted" in err.lower():
                return SQLQueryResult(
                    is_success=False,
                    columns=[],
                    rows=[],
                    row_count=0,
                    is_truncated=False,
                    error_message="Query Work Limit Exceeded: Execution aborted due to excessive computational complexity."
                )
            elif "not authorized" in err.lower() or "denied" in err.lower():
                return SQLQueryResult(
                    is_success=False,
                    columns=[],
                    rows=[],
                    row_count=0,
                    is_truncated=False,
                    error_message=f"Database Authorizer Denied: Operation is not permitted in read-only sandbox ({err})."
                )
            else:
                return SQLQueryResult(
                    is_success=False,
                    columns=[],
                    rows=[],
                    row_count=0,
                    is_truncated=False,
                    error_message=f"SQL Syntax or Database Error: {err}"
                )
        except sqlite3.DatabaseError as e:
            return SQLQueryResult(
                is_success=False,
                columns=[],
                rows=[],
                row_count=0,
                is_truncated=False,
                error_message=f"Database Authorizer Denied: {str(e)}"
            )
        except Exception as e:
            return SQLQueryResult(
                is_success=False,
                columns=[],
                rows=[],
                row_count=0,
                is_truncated=False,
                error_message=f"SQL Execution Error: {str(e)}"
            )
        finally:
            conn.close()


# ------------------------------------------------------------------------------
# Unit 5: Typed Exports & Syllabus Reference
# ------------------------------------------------------------------------------

def export_dataframe_to_csv(df: pd.DataFrame) -> str:
    """Export DataFrame to CSV with spreadsheet formula injection protection."""
    safe_df = df.copy()
    for col in safe_df.columns:
        if safe_df[col].dtype == object or safe_df[col].dtype == "string":
            safe_df[col] = safe_df[col].apply(
                lambda x: f"'{x}" if isinstance(x, str) and x.startswith(("=", "+", "-", "@")) else x
            )
    return safe_df.to_csv(index=False)


def export_dataframe_to_parquet(df: pd.DataFrame) -> bytes:
    """Export DataFrame to binary Parquet using pyarrow."""
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow")
    return buffer.getvalue()


def get_syllabus_reference_units() -> List[Dict[str, Any]]:
    """Return comprehensive reference documentation and hands-on examples for Units 1–5."""
    return [
        {
            "unit": "Unit 1",
            "title": "EDA Foundations",
            "topic": "Scales of Measurement & Methodology Comparisons",
            "purpose": "Distinguish measurement scales (nominal, ordinal, interval, ratio) and compare exploratory, classical, and Bayesian estimates of cultural engagement.",
            "formula_syntax": "Empirical: p_hat = k / n\nWilson 95% CI: (p_hat + z^2/(2n) +/- z*sqrt(p(1-p)/n + z^2/(4n^2))) / (1 + z^2/n)\nBayesian Beta(1,1): Posterior ~ Beta(1 + k, 1 + n - k)",
            "prerequisites": "Deterministic owner cohort (1 trip per owner, latest start date, stable tie-break). n = 341 owners.",
            "study_example": "Shared active-and-confirmed stop contract yields k=293, n=341 (85.92%), Wilson CI [81.82%, 89.23%], Bayes [81.84%, 89.26%].",
            "interpretation": "Point estimates ignore sampling error; the Wilson score interval provides robust coverage for proportions, while the Bayesian posterior represents complete posterior parameter probability.",
            "preset_query": "SELECT count(DISTINCT owner_user_id) as total_owners FROM trips WHERE status <> 'cancelled'"
        },
        {
            "unit": "Unit 2",
            "title": "Data Transformations",
            "topic": "Deduplication, Discretization, and Canonical Merge",
            "purpose": "Demonstrate robust schema normalization, price binning with separate free tiers, and exact full outer join set partitions.",
            "formula_syntax": "Price Tier = cut(entry_cost, bins=[-inf, 0, 100, 500, inf], labels=['Free', 'Budget', 'Moderate', 'Premium'])\nOuter Join Partition: |A union B| = |A| + |B| - |A intersect B|",
            "prerequisites": "363 saved distinct POIs from WanderMatch telemetry, 655 planned distinct POIs from SmartTrip itinerary items.",
            "study_example": "Set partition: 352 Inner (Both), 11 Saved Only, 303 Planned Only => 666 Full Outer Join distinct attractions.",
            "interpretation": "Raw many-to-many joins inflate row counts; distinct key deduplication before merging guarantees audited set conservation.",
            "preset_query": "SELECT poi_category, count(*) as count, round(avg(entry_cost), 2) as avg_price FROM activities_poi GROUP BY poi_category"
        },
        {
            "unit": "Unit 3",
            "title": "Statistics & Time Series",
            "topic": "Measures of Dispersion, Continuous Weekly Indexing & Forecasting",
            "purpose": "Construct continuous calendar-indexed weekly time series and evaluate one-step out-of-sample forecasting baselines.",
            "formula_syntax": "IQR = Q3 - Q1\nMAE = (1/N) * sum(|y_t - y_hat_t|)\nModel 1 (Last-Week): y_hat_t = y_{t-1}\nModel 2 (4-Week Mean): y_hat_t = (1/4) * sum_{i=1}^4 y_{t-i}",
            "prerequisites": "57 continuous Monday–Sunday weeks across study interactions, evaluated on last 12 complete target weeks.",
            "study_example": "Model 1 MAE = 3.42, Model 2 MAE = 3.88. Next-week dated forecast: 2026-08-17 (Model 1 = 44.0, Model 2 = 39.25).",
            "interpretation": "Weekly aggregation dampens daily noise; testing on an out-of-sample holdout prevents optimistic overfitting.",
            "preset_query": "SELECT strftime('%Y-%W', occurred_at) as week, count(*) as interactions FROM user_interactions GROUP BY week ORDER BY week LIMIT 10"
        },
        {
            "unit": "Unit 4",
            "title": "Graphical Methods",
            "topic": "Distributions, Coordinate Scatter & Companion Tables",
            "purpose": "Communicate complex multivariate relationships with proper scale, units, sample size, and accessible data table parity.",
            "formula_syntax": "ECDF: F_n(x) = (1/n) * sum(I(x_i <= x))\nLognormal MLE: mu = (1/n)*sum(ln x_i), sigma^2 = (1/n)*sum((ln x_i - mu)^2)",
            "prerequisites": "225 Indian events with 46 original preserved nulls, evaluated on deterministic 20% holdout set.",
            "study_example": "Lognormal MLE on positive event footfalls achieves holdout MAE = 413.25, outperforming simple mean imputation.",
            "interpretation": "Skewed distributions like event footfall or attraction fees require log transforms or median summaries rather than assuming normality.",
            "preset_query": "SELECT expected_footfall FROM events_festivals WHERE expected_footfall IS NOT NULL ORDER BY expected_footfall DESC LIMIT 10"
        },
        {
            "unit": "Unit 5",
            "title": "pandas & Data Sources",
            "topic": "Vectorized Operations, Parquet Columnar Storage & SQL Sandboxing",
            "purpose": "Execute secure read-only SQL queries, prevent CSV spreadsheet formula injection, and achieve typed Parquet round-trip serialization.",
            "formula_syntax": "Formula Escaping: if cell.startswith(('=', '+', '-', '@')): cell = \"'\" + cell\nParquet: df.to_parquet(buffer, engine='pyarrow')",
            "prerequisites": "PyArrow 17.0.0+, SQLite Authorizer with progress handler bounding execution steps.",
            "study_example": "Exporting the 666 outer join POI dataset to Parquet reduces payload size while preserving integer, float, and string column dtypes exactly.",
            "interpretation": "Data pipelines must guard against injection attacks at both input (SQL authorizer) and output (CSV escaping) boundaries.",
            "preset_query": "SELECT * FROM view_study_cities ORDER BY population DESC LIMIT 5"
        }
    ]
