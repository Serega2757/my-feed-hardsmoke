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
    {"gid": "1268499113", "file": "the-crash.xml", "name": "The Crash"},
]

LOG_FILE = "debug_log.txt"


def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def reset_log():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("=== DEBUG LOG ===\n")


def load_sheet(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"

    r = requests.get(url, timeout=30)
    r.raise_for_status()

    text = r.content.decode("utf-8-sig")
    return list(csv.reader(StringIO(text)))


def clean(v):
    if v is None:
        return ""
    return str(v).replace("\ufeff", "").strip()


def available(value):
    v = clean(value).lower()

    if v == "":
        return ""

    if "да" in v:
        return "true"

    if "нет" in v:
        return "false"

    return ""


def analyze_rows(rows, gid):
    yes_count = 0
    no_count = 0
    empty_count = 0
    other_count = 0
    active_rows = 0
    samples = []

    for row in rows[1:]:
        if len(row) < 6:
            continue

        a = clean(row[0])
        f = clean(row[5])

        if not a:
            continue

        active_rows += 1

        if len(samples) < 10:
            samples.append(f)

        low = f.lower()

        if low == "":
            empty_count += 1
        elif "да" in low:
            yes_count += 1
        elif "нет" in low:
            no_count += 1
        else:
            other_count += 1

    log("")
    log(f"GID: {gid}")
    log(f"Rows with A filled: {active_rows}")
    log(f"Contains 'да': {yes_count}")
    log(f"Contains 'нет': {no_count}")
    log(f"Empty F: {empty_count}")
    log(f"Other values: {other_count}")
    log("Sample F values:")
    for s in samples:
        log(f"  [{s}]")



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
    reset_log()
    log("Start: " + datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%Y-%m-%d %H:%M:%S"))

    for item in SHEETS:
        rows = load_sheet(item["gid"])
        analyze_rows(rows, item["gid"])

        xml = create_xml(rows, item["name"])

        with open(item["file"], "w", encoding="utf-8") as f:
            f.write(xml)

        log(f"Created: {item['file']}")

    log("Done")


if __name__ == "__main__":
    main()
