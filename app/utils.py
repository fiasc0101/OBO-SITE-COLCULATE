import re

def norm_article(s) -> str:
    return re.sub(r"[\s\-_./]", "", str(s or "")).upper()

def norm_text(s) -> str:
    t = str(s or "").lower().replace("ё", "е").replace("×", "x").replace("х", "x").replace("*", "x")
    t = re.sub(r"\s*x\s*(?=\d)", "x", t)
    t = re.sub(r"[\s]+", " ", t)
    return t.strip(" .,;:")

def to_float(v):
    try:
        return float(str(v).replace(",", ".").replace(" ", ""))
    except ValueError:
        return None

UNIT_MAP = {"шт": "шт", "шт.": "шт", "штука": "шт", "pcs": "шт", "м": "м", "м.": "м", "п.м": "м", "пм": "м",
            "компл": "компл", "компл.": "компл", "к-т": "компл", "кг": "кг"}

def norm_unit(u):
    u = str(u or "").strip().lower()
    return UNIT_MAP.get(u, u)
