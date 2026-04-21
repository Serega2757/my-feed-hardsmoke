import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo
import csv
from io import StringIO
import re

SPREADSHEET_ID = "1HhzquSfjN5t5Y_B2LRsrmWsdG5baGFtQgGnSubXSZ2I"

SHEETS = [
    {"gid": "775578539", "file": "pizpar.xml", "name": "Pizdatuy_par"},
    {"gid": "601174273", "file": "drop.xml", "name": "Drop"},
]


def load_sheet(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return list(csv.reader(StringIO(r.text)))


def clean(value):
    if value is None:
        return ""
    return str(value).replace("\ufeff", "").strip()


def available(value):
    v = "" if value is None else str(value)
    v = v.lower().strip()

    # убираем весь мусор кроме букв и цифр
    v = re.sub(r"[^a-zа-яіїє0-9]+", "", v)

    true_values = {
        "да", "є", "yes", "true", "1", "instock",
        "наявний", "наявності", "available"
    }

    false_values = {
        "нет", "ні", "no", "false", "0",
        "outofstock", "відсутній"
    }

    if v in true_values:
        return "true"

    if v in false_values:
        return "false"

    return "false"


def create_xml(rows, shop_name):
    now = datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%Y-%m-%d %H:%M")

    root = ET.Element("yml_catalog", date=now)
    shop = ET.SubElement(root, "shop")

    ET.SubElement(shop, "name").text = shop_name
    ET.SubElement(shop, "company").text = shop_name
    ET.SubElement(shop, "url").text = "https://serega2757.github.io/my-feed-hardsmoke/"

    currencies = ET.SubElement(shop, "currencies")
    for cur in ["UAH", "USD", "EUR"]:
        ET.SubElement(currencies, "currency", id=cur, rate="1")

    categories = ET.SubElement(shop, "categories")
    ET.SubElement(categories, "category", id="1").text = shop_name

    offers = ET.SubElement(shop, "offers")

    for row in rows[1:]:
        if len(row) < 6:
            continue

        sku = clean(row[0])
        vendor = clean(row[1])
        name = clean(row[2])
        price = clean(row[3]).replace(",", ".")
        currency = clean(row[4]).upper() or "UAH"
        stock = available(row[5])

        if not sku or not name:
            continue

        offer = ET.SubElement(offers, "offer", id=sku, available=stock)
        ET.SubElement(offer, "price").text = price
        ET.SubElement(offer, "currencyId").text = currency
        ET.SubElement(offer, "categoryId").text = "1"
        ET.SubElement(offer, "vendorCode").text = vendor
        ET.SubElement(offer, "name").text = name

    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def main():
    for item in SHEETS:
        rows = load_sheet(item["gid"])
        xml = create_xml(rows, item["name"])

        with open(item["file"], "w", encoding="utf-8") as f:
            f.write(xml)

        print(f"Updated {item['file']}")


if __name__ == "__main__":
    main()
