import re
from PIL import Image
from app.utils import to_float, norm_unit

def parse_image(file):
    """Простейший OCR: строка = текст + ед. изм. + число в конце. Результат ОБЯЗАТЕЛЬНО проверять."""
    import pytesseract
    text = pytesseract.image_to_string(Image.open(file), lang="rus+eng")
    items = []
    for line in text.splitlines():
        m = re.match(r"^\s*([\d.]+)?\s*(.+?)\s+(шт\.?|м\.?|компл\.?|кг)\s+([\d.,]+)\s*$", line, re.I)
        if m:
            items.append({"pos": m.group(1) or "", "name": m.group(2), "article": "", "maker": "",
                          "unit": norm_unit(m.group(3)), "qty": to_float(m.group(4)), "source": "фото (OCR)"})
    return items
