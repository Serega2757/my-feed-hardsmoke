function ФідДляGitHubHardSmoke() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheets = [
    "Liquids", "Cartridge", "ElfBar", "Pods", "Tabak",
    "Ugli", "Accessories", "Chashi", "Kalyani", "Комплекти"
  ];

  const props = PropertiesService.getScriptProperties();

  // Генеруємо XML
  const xmlContent = generateYML(ss, sheets);

  // ✅ Нормальний hash всього файлу
  const rawHash = Utilities.computeDigest(
    Utilities.DigestAlgorithm.MD5,
    xmlContent,
    Utilities.Charset.UTF_8
  );
  const newHash = Utilities.base64Encode(rawHash);

  const lastHash = props.getProperty("LAST_FEED_HASH");

  if (lastHash === newHash) {
    Logger.log("⏩ Без змін — пропуск");
    return;
  }

  const token = props.getProperty("GITHUB_TOKEN");
  const username = "serega2757";
  const repo = "my-feed-hardsmoke";
  const branch = "main";
  const path = "feed.xml";

  if (!token) throw new Error("❌ Немає GITHUB_TOKEN");

  let sha = props.getProperty("GITHUB_FILE_SHA");

  function upload(currentSha) {
    const payload = {
      message: "update feed.xml",
      content: Utilities.base64Encode(xmlContent, Utilities.Charset.UTF_8),
      branch: branch
    };

    if (currentSha) payload.sha = currentSha;

    return UrlFetchApp.fetch(
      `https://api.github.com/repos/${username}/${repo}/contents/${path}`,
      {
        method: "put",
        headers: {
          Authorization: `token ${token}`,
          Accept: "application/vnd.github+json"
        },
        contentType: "application/json",
        payload: JSON.stringify(payload),
        muteHttpExceptions: true
      }
    );
  }

  let response = upload(sha);
  let code = response.getResponseCode();
  let body = response.getContentText();

  // Якщо SHA неактуальний
  if (code === 422) {
    const getResp = UrlFetchApp.fetch(
      `https://api.github.com/repos/${username}/${repo}/contents/${path}`,
      {
        headers: {
          Authorization: `token ${token}`,
          Accept: "application/vnd.github+json"
        },
        muteHttpExceptions: true
      }
    );

    if (getResp.getResponseCode() === 200) {
      const data = JSON.parse(getResp.getContentText());
      sha = data.sha;
      props.setProperty("GITHUB_FILE_SHA", sha);

      response = upload(sha);
      code = response.getResponseCode();
      body = response.getContentText();
    }
  }

  if (code >= 200 && code < 300) {
    const data = JSON.parse(body);

    if (data.content && data.content.sha) {
      props.setProperty("GITHUB_FILE_SHA", data.content.sha);
    }

    props.setProperty("LAST_FEED_HASH", newHash);

    Logger.log(`✅ https://${username}.github.io/${repo}/${path}`);
  } else {
    throw new Error("❌ GitHub error: " + body);
  }
}

// ======================================================
// ХЕЛПЕРИ
// ======================================================

function toStr(v) {
  return v === null || v === undefined ? "" : String(v);
}

function escapeXml(v) {
  return toStr(v).replace(/[<>&'"]/g, c => (
    c === "<" ? "&lt;" :
    c === ">" ? "&gt;" :
    c === "&" ? "&amp;" :
    c === '"' ? "&quot;" : "&apos;"
  ));
}

function sanitizeCdata(v) {
  return toStr(v).replace(/]]>/g, "]]]]><![CDATA[>");
}

function normAvailability(v) {
  const s = toStr(v).trim().toLowerCase();

  return [
    "+", "true", "yes", "1",
    "in stock", "так", "наявний"
  ].includes(s) ? "true" : "false";
}

function normCurrency(v) {
  const s = toStr(v).trim().toUpperCase();
  return s || "UAH";
}

function normPrice(v) {
  const s = toStr(v).replace(/\s+/g, "").replace(",", ".");
  const m = s.match(/[0-9.]+/);
  return m ? m[0] : "0";
}

// ✅ Очищаємо та стискаємо description
function optimizeDescription(html) {
  let s = toStr(html);

  s = s.replace(/<script[\s\S]*?<\/script>/gi, "");
  s = s.replace(/<style[\s\S]*?<\/style>/gi, "");
  s = s.replace(/\s+/g, " ").trim();

  if (s.length > 1500) {
    s = s.substring(0, 1500);
  }

  return s;
}

// ======================================================
// XML
// ======================================================

function generateYML(ss, sheets) {
  let items = [];
  let categories = {};

  sheets.forEach((sheetName, index) => {
    const sheet = ss.getSheetByName(sheetName);
    if (!sheet) return;

    const data = sheet.getDataRange().getValues();
    if (data.length < 2) return;

    const categoryId = index + 1;
    categories[sheetName] = categoryId;

    if (sheetName === "Комплекти") {
      for (let i = 1; i < data.length; i++) {
        const row = data[i];
        if (!row[0]) continue;

        items.push({
          sku: row[0],
          name: row[1],
          price: normPrice(row[2]),
          availability: normAvailability(row[4]),
          currency: "UAH",
          vendorCode: row[0],
          url: "",
          image_url: "",
          description: "",
          categoryId
        });
      }

    } else {
      for (let i = 1; i < data.length; i++) {
        const row = data[i];
        if (!row[7]) continue;

        items.push({
          name: row[0],
          currency: normCurrency(row[1]),
          sku: row[2],
          url: row[3],
          image_url: row[4],
          description: row[5],
          availability: normAvailability(row[6]),
          vendorCode: row[7],
        
          // 🔥 Для ElfBar ціна з колонки J
          price: sheetName === "ElfBar"
            ? normPrice(row[9])
            : normPrice(row[8]),
        
          categoryId
        });
      }
    }
  });

  let xml = `<?xml version="1.0" encoding="UTF-8"?>\n`;
  xml += `<yml_catalog date="${Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd HH:mm")}">\n`;
  xml += `<shop>\n`;

  xml += `<name>My Shop</name>\n`;
  xml += `<company>My Company</company>\n`;
  xml += `<url>https://myshop.com</url>\n`;

  // Валюти
  xml += `<currencies>\n`;
  [...new Set(items.map(i => i.currency))].forEach(cur => {
    xml += `<currency id="${cur}" rate="1"/>\n`;
  });
  xml += `</currencies>\n`;

  // Категорії
  xml += `<categories>\n`;
  Object.entries(categories).forEach(([name, id]) => {
    xml += `<category id="${id}">${escapeXml(name)}</category>\n`;
  });
  xml += `</categories>\n`;

  // Offers
  xml += `<offers>\n`;

  items.forEach(item => {
    xml += `<offer id="${escapeXml(item.sku)}" available="${item.availability}">\n`;

    if (item.url) {
      xml += `<url>${escapeXml(item.url)}</url>\n`;
    }

    xml += `<price>${item.price}</price>\n`;
    xml += `<currencyId>${escapeXml(item.currency)}</currencyId>\n`;
    xml += `<categoryId>${item.categoryId}</categoryId>\n`;

    if (item.image_url) {
      xml += `<picture>${escapeXml(item.image_url)}</picture>\n`;
    }

    xml += `<vendorCode>${escapeXml(item.vendorCode)}</vendorCode>\n`;
    xml += `<name>${escapeXml(item.name)}</name>\n`;

    if (item.description) {
      const desc = optimizeDescription(item.description);
      xml += `<description><![CDATA[${sanitizeCdata(desc)}]]></description>\n`;
    }

    xml += `</offer>\n`;
  });

  xml += `</offers>\n`;
  xml += `</shop>\n`;
  xml += `</yml_catalog>`;

  return xml;
}
