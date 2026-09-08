"""Create or migrate the settings schema without discarding existing data."""

import sqlite3


SETTINGS_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS settings ("
    "id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
    "group1 TEXT, nam1 TEXT, wert1 TEXT, wert2 TEXT NOT NULL UNIQUE)"
)


def initialize_settings_db(connection):
    cursor = connection.cursor()
    try:
        # A savepoint also makes schema changes atomic with sqlite3's legacy
        # transaction handling, and does not commit an enclosing transaction.
        cursor.execute("SAVEPOINT webradiofs_settings")
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            tables = {row[0] for row in cursor.fetchall()}
            if "settings" not in tables and "settings2" in tables:
                cursor.execute("ALTER TABLE settings2 RENAME TO settings")

            cursor.execute(SETTINGS_SCHEMA)
            cursor.execute("PRAGMA table_info(settings)")
            columns = {row[1] for row in cursor.fetchall()}
            if not {"id", "group1", "nam1", "wert1"}.issubset(columns):
                raise sqlite3.DatabaseError("Unsupported webradioFS settings schema; database left unchanged")

            if "wert2" not in columns:
                # Keep the original rows, including duplicate legacy settings.
                # An existing backup must never be overwritten.
                cursor.execute("ALTER TABLE settings RENAME TO settings_legacy")
                cursor.execute(SETTINGS_SCHEMA)
                cursor.execute("SELECT id, group1, nam1, wert1 FROM settings_legacy ORDER BY id")
                rows = cursor.fetchall()
                keys = set()
                for setting_id, group, name, value in rows:
                    # Planner entries can share a time; their IDs distinguish
                    # them, just as in read_plan.writing().
                    key = str(name) + str(setting_id) if group == "plan" else str(group) + str(name)
                    if key not in keys:
                        cursor.execute(
                            "INSERT INTO settings (id, group1, nam1, wert1, wert2) VALUES (?, ?, ?, ?, ?)",
                            (setting_id, group, name, value, key),
                        )
                        keys.add(key)
            cursor.execute("RELEASE SAVEPOINT webradiofs_settings")
        except Exception:
            cursor.execute("ROLLBACK TO SAVEPOINT webradiofs_settings")
            cursor.execute("RELEASE SAVEPOINT webradiofs_settings")
            raise
    finally:
        cursor.close()
