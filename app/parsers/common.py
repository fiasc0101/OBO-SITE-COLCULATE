
import re
from app.utils import to_float, norm_unit

HEADERS = {
    "pos":      ["поз", "№", "n п/п", "номер"],
    "name":     ["наименование", "название", "оборудование", "описание", "товар", "name"],
    "article":  ["артикул", "тип", "марка", "article"],
    "article2": ["код продукции", "код"],
    "maker":    ["производитель", "изготовитель", "завод", "бренд"],
    "unit":     ["ед", "единица", "unit"],
    "qty":      ["кол", "количество", "qty"],
}

def detect_columns(header_row):
    res = {}
    for i, cell in enumerate(header_row):
        c = str(cell or "").lower().replace("\n", " ")
        for field, keys in HEADERS.items():
            if field not in res and any(k in c for k in keys):
                res[field] = i
    return res

SECTION_RE = re.compile(r"^\d+[xх×]\d", re.I)
QTY_RE = re.compile(r"^\s*(\d[\d\s]*(?:[.,]\d+)?)\s*([^\d\s].*)?$")

def split_qty(value):
    s = str(value or "").replace("\n", " ").strip()
    m = QTY_RE.match(s)
    if not m:
        return None, ""
    return to_float(m.group(1)), norm_unit((m.group(2) or "").strip())

def rows_to_items(table, source="", state=None):
    state = state if state is not None else {}
    items = []
    for row in table:
        c = detect_columns(row)
        if "name" in c and "qty" in c:
            state["cols"] = c
            continue
        cols = state.get("cols")
        if not cols:
            continue
        shift = 0
        if "pos" in cols:
            pc = cols["pos"]
            cell = str(row[pc] if pc < len(row) else "").strip()
            if not re.fullmatch(r"\d+([.,]\d+)?", cell):
                for i, x in enumerate(row):
                    if re.fullmatch(r"\d+", str(x or "").strip()):
                        if i != pc and i < cols.get("name", 99) + 2:
                            shift = i - pc
                        break
        get = lambda f: (row[cols[f] + shift] if f in cols and 0 <= cols[f] + shift < len(row) else None)
        clean = lambda v: "" if v is None else str(v).replace("\n", " ").strip()
        name = clean(get("name"))
        a1, a2 = clean(get("article")), clean(get("article2"))
        if a1 and a2 and len(a1) <= 2 and " " not in a1 and " " not in a2:
            article = a1 + a2
        else:
            article = a1 or a2
        unit = norm_unit(get("unit"))
        qty, unit2 = split_qty(get("qty"))
        if not unit:
            unit = unit2

        if re.fullmatch(r"\d+", name) and (not article or article.isdigit()):
            continue

        if qty is None:
            if name and not unit:
                state["group"] = name
            continue
        if not name:
            continue

        group = state.get("group", "")
        if SECTION_RE.match(name) and group:
            name = f"{group} {name}"

        items.append({
            "pos": clean(get("pos")),
            "name": name,
            "article": article,
            "maker": clean(get("maker")),
            "unit": unit,
            "qty": qty,
            "source": source,
        })
    return items

def fix_positions(items):
    blocks = []
    cur = None
    last_sec = 0
    for it in items:
        p = it["pos"].replace(",", ".")
        m = re.fullmatch(r"(\d+)\.(\d+)", p)
        if m:
            sec = int(m.group(1))
            if cur is None or sec < last_sec:
                cur = {"items": [], "seen": {}}
                blocks.append(cur)
            last_sec = sec
        if cur is None:
            cur = {"items": [], "seen": {}}
            blocks.append(cur)
        cur["items"].append((it, p))

    out = []
    for n, b in enumerate(blocks, 1):
        lst = []
        for it, p in b["items"]:
            m = re.fullmatch(r"(\d+)\.(\d+)", p)
            if m:
                a, s = m.group(1), m.group(2)
                seen = b["seen"].setdefault(a, set())
                if s in seen and (s + "0") not in seen:
                    s += "0"
                seen.add(s)
                p = f"{a}.{s}"
            it["pos"] = p
            it["block"] = n
            if it["qty"] and it["qty"] > 0:
                lst.append(it)

        def key(it):
            m = re.fullmatch(r"(\d+)\.(\d+)", it["pos"])
            return (int(m.group(1)), int(m.group(2))) if m else (10**6, 0)
        if lst and all(re.fullmatch(r"\d+\.\d+", i["pos"]) for i in lst):
            lst = sorted(lst, key=key)
        out += lst
    return out
