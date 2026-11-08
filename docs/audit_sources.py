"""Read-only reconciliation of CultureRoute claims against the supplied ZIP databases.

Run from anywhere: python docs/audit_sources.py
No third-party packages are required. The databases are extracted to temporary files,
opened in SQLite read-only mode, and removed when the audit ends.
"""

from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
import sqlite3
import zipfile


ROOT = Path(__file__).resolve().parent.parent
PACKS = (
    (ROOT / "SmartTrip (1).zip", "SmartTrip/data/PS-01.db"),
    (ROOT / "WanderMatch.zip", "WanderMatch/data/PS-11.db"),
)
CULTURAL = ("heritage", "museum", "religious", "food")


def one(conn: sqlite3.Connection, sql: str) -> int:
    return int(conn.execute(sql).fetchone()[0])


def scoped_selected(expression: str = "count(*)") -> str:
    return f"""
        SELECT {expression}
        FROM itinerary_items ii
        JOIN itineraries i ON i.itinerary_id = ii.itinerary_id
        JOIN trips t ON t.trip_id = i.trip_id
        JOIN cities c ON c.city_id = t.destination_city_id
        JOIN activities_poi a ON a.poi_id = ii.entity_id
        WHERE c.country_code = 'IN'
          AND t.status <> 'cancelled'
          AND i.is_active = 1
          AND ii.status = 'confirmed'
          AND ii.item_type = 'poi'
          AND ii.entity_type = 'poi'
          AND a.city_id = t.destination_city_id
    """


def audit() -> None:
    with ExitStack() as stack:
        temporary_paths: list[Path] = []
        for zip_path, entry in PACKS:
            with zipfile.ZipFile(zip_path) as archive:
                with NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                    tmp.write(archive.read(entry))
                    temporary_paths.append(Path(tmp.name))
        try:
            smart = sqlite3.connect(temporary_paths[0].as_uri() + "?mode=ro", uri=True)
            wander = sqlite3.connect(temporary_paths[1].as_uri() + "?mode=ro", uri=True)
            stack.callback(smart.close)
            stack.callback(wander.close)

            smart_tables = {r[0] for r in smart.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            wander_tables = {r[0] for r in wander.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            common = smart_tables & wander_tables
            assert len(smart_tables) == 18 and len(wander_tables) == 14 and len(common) == 8
            for name in sorted(common):
                assert smart.execute(f'PRAGMA table_info("{name}")').fetchall() == wander.execute(f'PRAGMA table_info("{name}")').fetchall(), f"Shared schema differs: {name}"
                pk = next(r[1] for r in smart.execute(f'PRAGMA table_info("{name}")') if r[5] == 1)
                left = smart.execute(f'SELECT * FROM "{name}" ORDER BY "{pk}"').fetchall()
                right = wander.execute(f'SELECT * FROM "{name}" ORDER BY "{pk}"').fetchall()
                assert left == right, f"Shared table differs: {name}"

            total_smart = sum(one(smart, f'SELECT count(*) FROM "{n}"') for n in smart_tables)
            total_wander = sum(one(wander, f'SELECT count(*) FROM "{n}"') for n in wander_tables)
            shared_rows = sum(one(smart, f'SELECT count(*) FROM "{n}"') for n in common)
            assert (total_smart, total_wander, shared_rows) == (32627, 27428, 11327)
            print(f"Source tables/rows: SmartTrip {len(smart_tables)}/{total_smart}; WanderMatch {len(wander_tables)}/{total_wander}")
            print(f"Shared identical tables/rows: {len(common)}/{shared_rows}; distinct combined: {len(smart_tables | wander_tables)}/{total_smart + total_wander - shared_rows}")

            smart.execute("ATTACH DATABASE ? AS wm", (temporary_paths[1].as_uri() + "?mode=ro",))
            city_count = one(smart, "SELECT count(*) FROM cities WHERE country_code='IN'")
            poi_count = one(smart, "SELECT count(*) FROM activities_poi a JOIN cities c USING(city_id) WHERE c.country_code='IN'")
            trip_count = one(smart, "SELECT count(*) FROM trips t JOIN cities c ON c.city_id=t.destination_city_id WHERE c.country_code='IN' AND t.status<>'cancelled'")
            interaction_where = "FROM wm.user_interactions u JOIN activities_poi a ON u.entity_type='poi' AND u.entity_id=a.poi_id JOIN cities c ON c.city_id=a.city_id WHERE c.country_code='IN'"
            interaction_count = one(smart, f"SELECT count(*) {interaction_where}")
            selected_count = one(smart, scoped_selected())
            cultural_predicate = "('heritage','museum','religious','food')"
            cultural_poi = one(smart, f"SELECT count(*) FROM activities_poi a JOIN cities c USING(city_id) WHERE c.country_code='IN' AND a.poi_category IN {cultural_predicate}")
            cultural_interactions = one(smart, f"SELECT count(*) {interaction_where} AND a.poi_category IN {cultural_predicate}")
            cultural_selected = one(smart, scoped_selected() + f" AND a.poi_category IN {cultural_predicate}")
            assert (city_count, poi_count, trip_count, interaction_count, selected_count) == (45, 675, 411, 6850, 3191)
            assert (cultural_poi, cultural_interactions, cultural_selected) == (211, 2144, 961)
            mismatch_count = one(smart, "SELECT count(*) FROM itinerary_items ii JOIN itineraries i ON i.itinerary_id=ii.itinerary_id JOIN trips t ON t.trip_id=i.trip_id JOIN cities c ON c.city_id=t.destination_city_id JOIN activities_poi a ON a.poi_id=ii.entity_id WHERE c.country_code='IN' AND t.status<>'cancelled' AND i.is_active=1 AND ii.status='confirmed' AND ii.item_type='poi' AND ii.entity_type='poi' AND a.city_id<>t.destination_city_id")
            assert mismatch_count == 0, f"Selected stop/trip city mismatches: {mismatch_count}"
            print(f"Study: cities {city_count}; attractions {poi_count}; trips {trip_count}; interactions {interaction_count}; selected stops {selected_count}")
            print(f"Cultural shares: {cultural_poi}/{poi_count}={cultural_poi/poi_count:.1%}; {cultural_interactions}/{interaction_count}={cultural_interactions/interaction_count:.1%}; {cultural_selected}/{selected_count}={cultural_selected/selected_count:.1%}")

            saved = {row[0] for row in smart.execute(f"SELECT DISTINCT u.entity_id {interaction_where} AND u.interaction_type='save'")}
            planned = {row[0] for row in smart.execute(scoped_selected("DISTINCT ii.entity_id"))}
            assert (len(saved), len(planned), len(saved & planned), len(saved - planned), len(planned - saved), len(saved | planned)) == (363, 655, 352, 11, 303, 666)
            print(f"Saved/planned distinct POIs: left {len(saved)}, right {len(planned)}, inner {len(saved & planned)}, saved-only {len(saved - planned)}, planned-only {len(planned - saved)}, outer {len(saved | planned)}")

            events = smart.execute("SELECT count(*),sum(e.expected_footfall IS NULL) FROM events_festivals e JOIN cities c USING(city_id) WHERE c.country_code='IN'").fetchone()
            assert events == (225, 46)
            print(f"Indian events: {events[0]}; missing expected footfall: {events[1]}")

            hours = smart.execute("SELECT (a.opens_at IS NULL), (a.closes_at IS NULL), count(*) FROM activities_poi a JOIN cities c USING(city_id) WHERE c.country_code='IN' GROUP BY 1,2").fetchall()
            assert {(open_null, close_null): count for open_null, close_null, count in hours} == {(0, 0): 537, (0, 1): 67, (1, 0): 64, (1, 1): 7}
            print("India attraction hours: 537 both present; 67 missing close; 64 missing open; 7 both missing")

            timestamps = smart.execute(f"SELECT u.occurred_at {interaction_where} AND a.poi_category IN {cultural_predicate}")
            weekly: Counter = Counter()
            for (timestamp,) in timestamps:
                day = datetime.fromisoformat(timestamp).date()
                weekly[day - timedelta(days=day.weekday())] += 1
            weeks = sorted(weekly)
            # Final Monday-Sunday period is partial in the source snapshot.
            complete_weeks = weeks[:-1]
            values = [weekly[week] for week in complete_weeks]
            last_week_mae = sum(abs(values[i] - values[i - 1]) for i in range(len(values) - 12, len(values))) / 12
            four_week_mae = sum(abs(values[i] - sum(values[i - 4:i]) / 4) for i in range(len(values) - 12, len(values))) / 12
            assert len(complete_weeks) == 57 and round(last_week_mae, 2) == 3.42 and round(four_week_mae, 2) == 3.88
            print(f"Weekly forecast: {len(complete_weeks)} complete weeks; last-12 MAE {last_week_mae:.2f} (last-week), {four_week_mae:.2f} (four-week mean)")
        finally:
            try:
                smart.close()
                wander.close()
            except UnboundLocalError:
                pass
            for path in temporary_paths:
                path.unlink(missing_ok=True)


if __name__ == "__main__":
    audit()
