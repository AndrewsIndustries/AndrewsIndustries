/**
 * Andrews Stock Reporter.gs
 * Complete unified block of code including optimized VIX and DXY data fetching and reporting.
 */

function sendDailyStockReport() {
  const data = getReportData();
  const htmlBody = generateHtmlEmail(data);
  
  MailApp.sendEmail({
    to: Session.getActiveUser().getEmail(),
    subject: `Daily Market & Stock Report - ${data.timestamp}`,
    htmlBody: htmlBody
  });
}

function getReportData() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  
  // Cleanly fetch VIX and DXY directly using the native GOOGLEFINANCE formulas 
  // evaluated safely via an isolated cell pull to prevent web-scraping dependencies.
  const vixCurrent = getNativeMarketPrice("INDEXCBOE:VIX");
  const dxyCurrent = getNativeMarketPrice("CURRENCY:DXY");

  // Fetch Stock Data 
  // Assuming tickers are in Column A of your active sheet starting at Row 2
  const tickerRange = sheet.getRange("A2:A" + sheet.getLastRow()).getValues();
  const stocks = [];
  let totalChange = 0;

  tickerRange.forEach(row => {
    const ticker = row[0];
    if (!ticker) return;

    const priceRaw = getNativeMarketPrice(ticker, "price", false);
    const changePct = getNativeMarketPrice(ticker, "changepct", false) / 100;
    const sma50Raw = getNativeMarketPrice(ticker, "average50", false);
    const sma200Raw = getNativeMarketPrice(ticker, "average200", false);
    const high52Raw = getNativeMarketPrice(ticker, "high52", false);
    const low52Raw = getNativeMarketPrice(ticker, "low52", false);
    const peRaw = getNativeMarketPrice(ticker, "pe", false);
    const epsRaw = getNativeMarketPrice(ticker, "eps", false);
    const betaRaw = getNativeMarketPrice(ticker, "beta", false);
    
    // Use the Predictive Engine for advanced analysis
    const analysis = calculateAlphaForecast(priceRaw, sma50Raw, sma200Raw, high52Raw, low52Raw, betaRaw);
    const vixMultiplier = parseFloat(vixCurrent) > 25 ? 0.9 : 1.0;

    const distFromHigh = (typeof priceRaw === 'number' && typeof high52Raw === 'number') 
      ? ((1 - (priceRaw / high52Raw)) * 100).toFixed(1) : "N/A";

    const changeRaw = isNaN(changePct) ? 0 : (changePct * 100);

    stocks.push({
      ticker: ticker,
      price: typeof priceRaw === 'number' ? priceRaw.toFixed(2) : "N/A",
      change: changeRaw.toFixed(2) + "%",
      changeRaw: changeRaw,
      status: changeRaw >= 0 ? "Warming" : "Cooling",
      prediction: analysis.forecast,
      forecast: `Exp. Target: $${analysis.target}`,
      distFromHigh: distFromHigh,
      sentiment: analysis.sentiment * vixMultiplier,
      risk: analysis.risk,
      pe: typeof peRaw === 'number' ? peRaw.toFixed(1) : "N/A",
      eps: typeof epsRaw === 'number' ? epsRaw.toFixed(2) : "N/A"
    });
    
    totalChange += changeRaw;
  });
  
  return {
    stocks: stocks,
    totalStocks: stocks.length,
    avgChange: stocks.length > 0 ? (totalChange / stocks.length).toFixed(2) : "0.00",
    vix: parseFloat(vixCurrent),
    dxy: dxyCurrent,
    timestamp: Utilities.formatDate(new Date(), "GMT-5", "MM/dd/yyyy HH:mm z")
  };
}

/**
 * Helper function to retrieve live market index prices safely without spreadsheet clutter.
 */
function getNativeMarketPrice(ticker, attribute = "price", format = true) {
  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    const lastRow = sheet.getLastRow();
    
    // Inject formula into a temporary execution row safely below your active dataset
    const targetCell = sheet.getRange(lastRow + 1, 1);
    targetCell.setFormula(`=GOOGLEFINANCE("${ticker}", "${attribute}")`);
    
    // Force spreadsheet execution engine to flush and fetch calculation results instantly
    SpreadsheetApp.flush(); 
    
    const price = targetCell.getValue();
    targetCell.clearContent(); // Remove temporary row footprint instantly
    
    if (typeof price !== 'number') return "N/A";
    return format ? price.toFixed(2) : price;
  } catch(e) {
    return "N/A";
  }
}

function generateHtmlEmail(data) {
  const template = HtmlService.createTemplateFromFile('Report');
  
  // Inject script data variables cleanly into template context
  template.stocks = data.stocks;
  template.totalStocks = data.totalStocks;
  template.avgChange = data.avgChange;
  template.vix = data.vix;
  template.dxy = data.dxy;
  template.timestamp = data.timestamp;
  
  return template.evaluate().getContent();
}

/**
 * Run manually to verify permissions and layout tracking output.
 */
function testRun() {
  sendDailyStockReport();
}