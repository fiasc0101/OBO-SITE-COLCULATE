import io, os
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from app import db
from app.parsers.excel_parser import parse_excel
from app.parsers.pdf_parser import parse_pdf
from app.parsers.image_parser import parse_image
from app.matcher import match_items, candidates_for
from app.exporter import build_excel
from app.loader import load_catalog, load_mapping, remember_choice, forget_choice, save_map_file, map_dataframe

db.init()
with db.conn() as _c:
    _n_cat = _c.execute("SELECT COUNT(*) FROM catalog").fetchone()[0]
    _n_map = _c.execute("SELECT COUNT(*) FROM mapping").fetchone()[0]
if _n_cat == 0 and os.path.exists(db.BASE_XLSX):
    load_catalog(pd.read_excel(db.BASE_XLSX, dtype=object).fillna(""))
if _n_map == 0 and os.path.exists(db.MAP_XLSX):
    load_mapping(pd.read_excel(db.MAP_XLSX, dtype=object).fillna(""))

app = FastAPI(title="Калькулятор спецификаций")
app.mount("/static", StaticFiles(directory=os.path.join(db.BASE_DIR, "app", "static")), name="static")

@app.get("/")
def index():
    return FileResponse(os.path.join(db.BASE_DIR, "app", "static", "index.html"))

@app.post("/api/parse")
async def parse(file: UploadFile = File(...)):
    data = io.BytesIO(await file.read())
    n = file.filename.lower()
    try:
        if n.endswith((".xlsx", ".xlsm", ".xls")): items = parse_excel(data)
        elif n.endswith(".pdf"): items = parse_pdf(data)
        elif n.endswith((".png", ".jpg", ".jpeg", ".tif", ".bmp")): items = parse_image(data)
        else: raise HTTPException(400, "Поддерживаются PDF, Excel, изображения")
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка разбора: {e}")
    return {"items": items}

@app.post("/api/match")
def match(payload: dict):
    return {"rows": match_items(payload["items"])}

@app.post("/api/candidates")
def candidates(payload: dict):
    return {"candidates": candidates_for(payload.get("name", ""))}

@app.get("/api/catalog/count")
def catalog_count():
    with db.conn() as c:
        return {"catalog": c.execute("SELECT COUNT(*) FROM catalog").fetchone()[0],
                "mapping": c.execute("SELECT COUNT(*) FROM mapping").fetchone()[0]}

@app.post("/api/catalog/upload")
async def upload_catalog(file: UploadFile = File(...)):
    raw = await file.read()
    df = pd.read_excel(io.BytesIO(raw), dtype=object).fillna("")
    try:
        res = load_catalog(df)
    except ValueError as e:
        raise HTTPException(400, str(e))
    with open(db.BASE_XLSX, "wb") as f:
        f.write(raw)
    return res

@app.post("/api/mapping/upload")
async def upload_mapping(file: UploadFile = File(...)):
    df = pd.read_excel(io.BytesIO(await file.read()), dtype=object).fillna("")
    res = load_mapping(df)
    save_map_file()
    return res

@app.post("/api/mapping/remember")
def remember(payload: dict):
    n = remember_choice(payload.get("name", ""), payload.get("article", ""), payload.get("code", ""),
                        payload.get("factor", 1), payload.get("decision", ""))
    save_map_file()
    return {"saved": n}

@app.post("/api/mapping/forget")
def forget(payload: dict):
    forget_choice(payload.get("name", ""), payload.get("article", ""))
    save_map_file()
    return {"ok": True}

@app.get("/api/mapping/export")
def export_map():
    buf = io.BytesIO()
    map_dataframe().to_excel(buf, index=False)
    return Response(buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=karta_zamen.xlsx"})

@app.post("/api/rules/add")
def add_rule(payload: dict):
    with db.conn() as c:
        c.execute("INSERT INTO accessory_rules(parent_num_article,acc_num_article,factor,offset,note) VALUES(?,?,?,?,?)",
                  (payload["parent"], payload["acc"], payload.get("factor", 1), payload.get("offset", 0), payload.get("note", "")))
    return {"ok": True}

@app.post("/api/export")
def export(payload: dict):
    xlsx = build_excel(payload["rows"], with_price=payload.get("with_price", False))
    return Response(xlsx, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=result.xlsx"})
