import pandas as pd
from app import db
from app.utils import norm_article, norm_text, to_float, norm_unit

MAP_COLUMNS = ["Наименование проекта", "Артикул проекта", "Код OBO", "Тип OBO (для проверки)",
               "Коэффициент", "Решение, если аналога нет", "Источник"]

def _find(df, *keys):
    for c in df.columns:
        if any(k in str(c).lower() for k in keys):
            return c

def load_catalog(df):
    cols = {
        "num": _find(df, "код", "цифр"), "let": _find(df, "артикул", "букв"),
        "name": _find(df, "наименование", "название"), "unit": _find(df, "единица", "ед."),
        "price": _find(df, "цена"), "maker": _find(df, "производ", "бренд"),
        "grp": _find(df, "групп"), "status": _find(df, "статус"),
    }
    if cols["name"] is None:
        raise ValueError("Не найдена колонка с наименованием")
    g = lambda r, k: str(r[cols[k]]).strip() if cols[k] is not None else ""
    with db.conn() as c:
        c.execute("DELETE FROM catalog")
        for _, r in df.iterrows():
            if not g(r, "name") and not g(r, "num"):
                continue
            c.execute("INSERT INTO catalog(num_article,letter_article,name,unit,price,maker,grp,status) VALUES(?,?,?,?,?,?,?,?)",
                      (g(r, "num"), g(r, "let"), g(r, "name"), norm_unit(g(r, "unit")),
                       to_float(g(r, "price")), g(r, "maker"), g(r, "grp"), g(r, "status")))
    return {"loaded": len(df), "columns": {k: (str(v) if v is not None else None) for k, v in cols.items()}}

def _keys(name, article):
    keys = []
    art = norm_article(article)
    if art:
        keys.append(art)
    if str(name).strip():
        keys.append("n:" + norm_text(name))
    return keys

def _put(c, name, article, code, factor, decision):
    keys = _keys(name, article)
    for k in keys:
        c.execute("INSERT OR REPLACE INTO mapping(src_article,num_article,factor,decision,label,art_raw) VALUES(?,?,?,?,?,?)",
                  (k, code, factor or 1, decision, str(name).strip(), str(article).strip()))
    return len(keys)

def load_mapping(df):
    cn = _find(df, "наименование")
    ca = _find(df, "артикул проекта", "артикул")
    cc = _find(df, "код obo", "код")
    cf = _find(df, "коэфф")
    cd = _find(df, "решение")
    if cc is None:
        cols = list(df.columns)
        ca, cc = cols[0], cols[1]
        cf = cols[2] if len(cols) > 2 else None
        cn = cd = None
    n = 0
    with db.conn() as c:
        for _, r in df.iterrows():
            code = str(r[cc]).strip()
            decision = str(r[cd]).strip() if cd is not None else ""
            if not code and not decision:
                continue
            factor = to_float(r[cf]) if cf is not None and str(r[cf]).strip() else 1
            name = r[cn] if cn is not None else ""
            art = r[ca] if ca is not None else ""
            n += _put(c, name, art, code, factor, "" if code else decision)
    return {"loaded": n}

def remember_choice(name, article, code="", factor=1, decision=""):
    with db.conn() as c:
        return _put(c, name, article, code, factor, "" if code else decision)

def forget_choice(name, article):
    with db.conn() as c:
        for k in _keys(name, article):
            c.execute("DELETE FROM mapping WHERE src_article = ?", (k,))
    return True

def map_dataframe():
    with db.conn() as c:
        letters = {r["num_article"]: r["letter_article"] for r in c.execute("SELECT num_article, letter_article FROM catalog")}
        rows = c.execute("SELECT label, art_raw, num_article, factor, decision FROM mapping WHERE label IS NOT NULL AND label != ''").fetchall()
    seen, out = set(), []
    for r in rows:
        k = (r["label"], r["art_raw"] or "", r["num_article"] or "", r["decision"] or "")
        if k in seen:
            continue
        seen.add(k)
        out.append([r["label"], r["art_raw"] or "", r["num_article"] or "", letters.get(r["num_article"], ""),
                    r["factor"] or 1, r["decision"] or "", "сайт"])
    return pd.DataFrame(out, columns=MAP_COLUMNS)

def save_map_file():
    df = map_dataframe()
    df.to_excel(db.MAP_XLSX, index=False)
    return len(df)
