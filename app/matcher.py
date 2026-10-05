from rapidfuzz import fuzz
from app.db import conn
from app.utils import norm_article, norm_text

def _view(r, qty):
    return {"num_article": r["num_article"], "letter_article": r["letter_article"], "name": r["name"],
            "unit": r["unit"], "qty": qty, "price": r["price"]}

def _top(q, names, limit=5):
    scored = sorted(((fuzz.token_set_ratio(q, n), r) for n, r in names), key=lambda x: -x[0])[:limit]
    return [{"score": round(s), "num_article": r["num_article"], "letter_article": r["letter_article"],
             "name": r["name"], "unit": r["unit"]} for s, r in scored]

def match_items(items):
    with conn() as c:
        cat = [dict(r) for r in c.execute("SELECT * FROM catalog")]
        mp = {}
        for r in c.execute("SELECT * FROM mapping"):
            k = r["src_article"]
            mp[k if k.startswith("n:") else norm_article(k)] = dict(r)
        rules = [dict(r) for r in c.execute("SELECT * FROM accessory_rules")]
    by_key = {}
    for r in cat:
        for f in ("num_article", "letter_article"):
            k = norm_article(r[f])
            if k:
                by_key.setdefault(k, r)
    names = [(norm_text(r["name"]), r) for r in cat]

    out = []
    for it in items:
        m, score, how, factor, decision = None, 0, "не найдено", 1.0, ""
        akey = norm_article(it.get("article"))
        nkey = "n:" + norm_text(it["name"])
        hits = [h for h in (mp.get(akey) if akey else None, mp.get(nkey)) if h]
        for h in hits:
            if h.get("num_article"):
                cand = by_key.get(norm_article(h["num_article"]))
                if cand:
                    m, factor, score, how = cand, h["factor"] or 1, 100, "карта замен"
                    break
        if not m:
            for h in hits:
                if h.get("decision"):
                    decision, how = h["decision"], "решение из карты"
                    break
        if not m and not decision and akey and akey in by_key:
            m, score, how = by_key[akey], 100, "точный артикул"
        candidates = []
        if not m and not decision:
            candidates = _top(norm_text(it["name"]), names)
        status = "ok" if m else ("decided" if decision else ("review" if candidates else "none"))
        qty = round(it["qty"] * factor, 3)
        row = {"src": it, "match": _view(m, qty) if m else None, "decision": decision, "score": score, "how": how,
               "factor": factor, "status": status, "candidates": candidates, "accessories": []}
        out.append(row)
        if m:
            for r in rules:
                if norm_article(r["parent_num_article"]) == norm_article(m["num_article"]):
                    acc = by_key.get(norm_article(r["acc_num_article"]))
                    if acc:
                        a = _view(acc, max(0, round(qty * r["factor"] + r["offset"], 3)))
                        a["note"] = r["note"]
                        row["accessories"].append(a)
    return out

def candidates_for(name, limit=5):
    with conn() as c:
        cat = [dict(r) for r in c.execute("SELECT * FROM catalog")]
    return _top(norm_text(name), [(norm_text(r["name"]), r) for r in cat], limit)
