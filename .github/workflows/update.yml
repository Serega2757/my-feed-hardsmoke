#!/usr/bin/env python3
"""
Генератор feed.xml для HardSmoke.

Порт Apps Script `ФідДляGitHubHardSmoke` на Python для запуска в GitHub Actions.
Логика формирования офферов повторяет оригинал один в один, плюс добавлены
теги <available>, <supplierCode>, <quantity> для корректного импорта в OneBox.

Зависимостей нет — только стандартная библиотека.
"""

import csv
import io
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

# ======================================================
# КОНФИГ
# ======================================================

# ID таблицы «Товари для Gmall».
# Берётся из URL: docs.google.com/spreadsheets/d/<ВОТ_ЭТОТ_КУСОК>/edit
SPREADSHEET_ID = os.environ.get(
    "SPREADSHEET_ID",
    "ВСТАВЬТЕ_ID_ТАБЛИЦЫ_ТОВАРИ_ДЛЯ_GMALL",
)

OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "feed.xml")

# Порядок важен: индекс в списке + 1 = categoryId в фиде.
SHEETS = [
    "Liquids", "Cartridge", "ElfBar", "Pods", "Tabak",
    "Ugli", "Accessories", "Chashi", "Kalyani", "Комплекти",
]

# Предохранитель: если новый фид содержит меньше указанной доли офферов
# от предыдущего — не перезаписывать файл и упасть с ошибкой.
# Защищает от обнуления каталога в OneBox, если Google отдал битый ответ.
MIN_RATIO = float(os.environ.get("MIN_RATIO", "0.5"))

TIMEOUT = 60

# ======================================================
# ХЕЛПЕРЫ (порт из Apps Script)
# ======================================================


def to_str(v):
    return "" if v is None else str(v)


_ESCAPE_MAP = {
    "<": "&lt;",
    ">": "&gt;",
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
}


def escape_xml(v):
    return re.sub(r"[<>&'\"]", lambda m: _ESCAPE_MAP[m.group(0)], to_str(v))


def sanitize_cdata(v):
    return to_str(v).replace("]]>", "]]]]><![CDATA[>")


_AVAILABLE_VALUES = {"+", "true", "yes", "1", "in stock", "так", "наявний"}


def norm_availability(v):
    s = to_str(v).strip().lower()
    return "true" if s in _AVAILABLE_VALUES else "false"


def norm_currency(v):
    return to_str(v).strip().upper() or "UAH"


def norm_price(v):
    # В JS String.replace(",", ".") меняет только первое вхождение — повторяем.
    s = re.sub(r"\s+", "", to_str(v)).replace(",", ".", 1)
    m = re.search(r"[0-9.]+", s)
    return m.group(0) if m else "0"


def optimize_description(html):
    s = to_str(html)
    s = re.sub(r"<script[\s\S]*?</script>", "", s, flags=re.IGNORECASE)
    s = re.sub(r"<style[\s\S]*?</style>", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:1500]


def cell(row, index):
    """Безопасный доступ к ячейке: CSV-строки бывают короче шапки."""
    return row[index] if index < len(row) else ""


# ======================================================
# ЧТЕНИЕ ТАБЛИЦЫ
# ======================================================


def load_sheet(sheet_name):
    """Читает лист по имени через gviz-экспорт. Таблица должна быть
    расшарена как «Всем, у кого есть ссылка — читатель»."""
    url = (
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
        f"/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(sheet_name)}"
    )

    req = urllib.request.Request(url, headers={"User-Agent": "hardsmoke-feed/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read()

    text = raw.decode("utf-8-sig", errors="replace")

    # Если таблица закрыта — Google отдаёт HTML страницы логина, а не CSV.
    head = text.lstrip()[:200].lower()
    if head.startswith("<!doctype") or head.startswith("<html"):
        raise RuntimeError(
            f"Лист «{sheet_name}»: вместо CSV пришёл HTML. "
            f"Скорее всего, у таблицы нет доступа по ссылке."
        )

    return list(csv.reader(io.StringIO(text)))


# ======================================================
# СБОРКА XML
# ======================================================


def collect_items():
    items = []
    categories = {}

    for index, sheet_name in enumerate(SHEETS):
        try:
            data = load_sheet(sheet_name)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Не удалось прочитать лист «{sheet_name}»: {exc}") from exc

        if len(data) < 2:
            print(f"  {sheet_name}: пусто, пропуск")
            continue

        category_id = index + 1
        categories[sheet_name] = category_id
        before = len(items)

        if sheet_name == "Комплекти":
            for row in data[1:]:
                sku = cell(row, 0)
                if not sku:
                    continue

                items.append({
                    "sku": sku,
                    "name": cell(row, 1),
                    "price": norm_price(cell(row, 2)),
                    "availability": norm_availability(cell(row, 4)),
                    "currency": "UAH",
                    "vendorCode": sku,
                    "url": "",
                    "image_url": "",
                    "description": "",
                    "categoryId": category_id,
                })
        else:
            for row in data[1:]:
                if not cell(row, 7):
                    continue

                items.append({
                    "name": cell(row, 0),
                    "currency": norm_currency(cell(row, 1)),
                    "sku": cell(row, 2),
                    "url": cell(row, 3),
                    "image_url": cell(row, 4),
                    "description": cell(row, 5),
                    "availability": norm_availability(cell(row, 6)),
                    "vendorCode": cell(row, 7),
                    # Для ElfBar цена из колонки J, для остальных — из I
                    "price": norm_price(cell(row, 9) if sheet_name == "ElfBar" else cell(row, 8)),
                    "categoryId": category_id,
                })

        print(f"  {sheet_name}: +{len(items) - before} офферов")

    return items, categories


def generate_yml(items, categories):
    generated_at = datetime.now(ZoneInfo("Europe/Kyiv"))
    now = generated_at.strftime("%Y-%m-%d %H:%M")
    stamp = generated_at.strftime("%d.%m.%Y %H:%M:%S")

    in_stock = sum(1 for i in items if i["availability"] == "true")

    out = ['<?xml version="1.0" encoding="UTF-8"?>\n']

    # Шапка с датой формирования — видна сразу при открытии файла.
    # XML-комментарии парсерами игнорируются, на импорт в OneBox не влияют.
    out.append(
        f"<!-- Сформовано: {stamp} (Europe/Kyiv) | "
        f"офферів: {len(items)}, в наявності: {in_stock}, "
        f"немає: {len(items) - in_stock} -->\n"
    )

    out.append(f'<yml_catalog date="{now}">\n')
    out.append("<shop>\n")

    out.append("<name>My Shop</name>\n")
    out.append("<company>My Company</company>\n")
    out.append("<url>https://myshop.com</url>\n")

    # Валюты
    out.append("<currencies>\n")
    seen = []
    for item in items:
        if item["currency"] not in seen:
            seen.append(item["currency"])
    for cur in seen:
        out.append(f'<currency id="{cur}" rate="1"/>\n')
    out.append("</currencies>\n")

    # Категории
    out.append("<categories>\n")
    for name, cat_id in categories.items():
        out.append(f'<category id="{cat_id}">{escape_xml(name)}</category>\n')
    out.append("</categories>\n")

    # Офферы
    out.append("<offers>\n")

    for item in items:
        out.append(
            f'<offer id="{escape_xml(item["sku"])}" available="{item["availability"]}">\n'
        )

        if item["url"]:
            out.append(f'<url>{escape_xml(item["url"])}</url>\n')

        out.append(f'<price>{item["price"]}</price>\n')
        out.append(f'<currencyId>{escape_xml(item["currency"])}</currencyId>\n')
        out.append(f'<categoryId>{item["categoryId"]}</categoryId>\n')

        if item["image_url"]:
            out.append(f'<picture>{escape_xml(item["image_url"])}</picture>\n')

        out.append(f'<vendorCode>{escape_xml(item["vendorCode"])}</vendorCode>\n')

        # Дублируем идентификатор и наличие обычными тегами (не атрибутами):
        # OneBox некорректно читает атрибуты в секции «Постачальники».
        out.append(f'<available>{item["availability"]}</available>\n')
        out.append(f'<supplierCode>{escape_xml(item["sku"])}</supplierCode>\n')
        out.append(
            f'<quantity>{"100" if item["availability"] == "true" else "0"}</quantity>\n'
        )

        out.append(f'<name>{escape_xml(item["name"])}</name>\n')

        if item["description"]:
            desc = optimize_description(item["description"])
            out.append(f"<description><![CDATA[{sanitize_cdata(desc)}]]></description>\n")

        out.append("</offer>\n")

    out.append("</offers>\n")
    out.append("</shop>\n")
    out.append("</yml_catalog>")

    return "".join(out)


def previous_offer_count(path):
    if not os.path.exists(path):
        return 0
    with open(path, "r", encoding="utf-8") as f:
        return f.read().count("<offer ")


# ======================================================
# MAIN
# ======================================================


def main():
    if "ВСТАВЬТЕ_ID" in SPREADSHEET_ID:
        sys.exit("❌ Не задан SPREADSHEET_ID — впишите ID таблицы в скрипт или в переменную окружения")

    print(f"Старт: {datetime.now(ZoneInfo('Europe/Kyiv')).strftime('%Y-%m-%d %H:%M:%S')}")

    items, categories = collect_items()

    in_stock = sum(1 for i in items if i["availability"] == "true")
    print(f"Всего офферов: {len(items)} (в наличии {in_stock}, нет {len(items) - in_stock})")

    if not items:
        sys.exit("❌ Ноль офферов — файл не перезаписан, чтобы не обнулить каталог в OneBox")

    old_count = previous_offer_count(OUTPUT_FILE)
    if old_count and len(items) < old_count * MIN_RATIO:
        sys.exit(
            f"❌ Резкое падение количества офферов: было {old_count}, стало {len(items)}. "
            f"Файл не перезаписан. Проверьте таблицу."
        )

    xml = generate_yml(items, categories)

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        f.write(xml)

    print(f"✅ Записан {OUTPUT_FILE} ({len(xml)} символов, было офферов {old_count})")


if __name__ == "__main__":
    main()
