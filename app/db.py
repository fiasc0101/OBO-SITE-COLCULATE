import os, sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB = os.path.join(DATA_DIR, "app.db")
BASE_XLSX = os.path.join(DATA_DIR, "baza_obo.xlsx")
MAP_XLSX = os.path.join(DATA_DIR, "karta_zamen.xlsx")

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS catalog(
            id INTEGER PRIMARY KEY, num_article TEXT, letter_article TEXT, name TEXT,
            unit TEXT, price REAL, maker TEXT, specs TEXT);
        CREATE INDEX IF NOT EXISTS i_num ON catalog(num_article);
        CREATE INDEX IF NOT EXISTS i_let ON catalog(letter_article);
        CREATE TABLE IF NOT EXISTS mapping(
            src_article TEXT PRIMARY KEY, num_article TEXT, factor REAL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS accessory_rules(
            id INTEGER PRIMARY KEY, parent_num_article TEXT, acc_num_article TEXT,
            factor REAL DEFAULT 1, offset REAL DEFAULT 0, note TEXT);
        """)
        for table, col in (("catalog", "status"), ("catalog", "grp"),
                           ("mapping", "decision"), ("mapping", "label"), ("mapping", "art_raw")):
            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
            except sqlite3.OperationalError:
                pass
