import requests
import xml.etree.ElementTree as ET
from datetime import datetime

SPREADSHEET_ID = "1HhzquSfjN5t5Y_B2LRsrmWsdG5baGFtQgGnSubXSZ2I"

SHEETS = [
    {"gid": "775578539", "file": "pizpar.xml"},
    {"gid": "601174273", "file": "drop.xml"},
]


def load_sheet(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.text.splitlines()


def parse_csv(lines):
    import csv
    from io import StringIO

    rows = list(csv.reader(StringIO("\n".join(lines))))
    return rows


def available(v):
    return "true" if str(v).strip().lower() == "да" else "false"


def safe(v):
    return "" if v is None else str(v).strip()


def create_xml(rows, shop_name):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

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

        sku = safe(row[0])
        vendor = safe(row[1])
        name = safe(row[2])
        price = safe(row[3]).replace(",", ".")
        currency = safe(row[4]).upper() or "UAH"
        stock = available(row[5])

        if not sku or not name:
            continue

        offer = ET.SubElement(offers, "offer", id=sku, available=stock)
        ET.SubElement(offer, "price").text = price
        ET.SubElement(offer, "currencyId").text = currency
        ET.SubElement(offer, "categoryId").text = "1"
        ET.SubElement(offer, "vendorCode").text = vendor
        ET.SubElement(offer, "name").text = name

    xml_data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return xml_data.decode("utf-8")


def main():
    for item in SHEETS:
        lines = load_sheet(item["gid"])
        rows = parse_csv(lines)

        xml = create_xml(rows, item["file"].replace(".xml", ""))

        with open(item["file"], "w", encoding="utf-8") as f:
            f.write(xml)

        print(f"Created {item['file']}")


if __name__ == "__main__":
    main()
