import pandas as pd
from .common import rows_to_items

def parse_excel(file):
    items = []
    xl = pd.ExcelFile(file)
    for sheet in xl.sheet_names:
        df = xl.parse(sheet, header=None, dtype=object).fillna("")
        items += rows_to_items(df.values.tolist(), source=f"лист {sheet}")
    return items
