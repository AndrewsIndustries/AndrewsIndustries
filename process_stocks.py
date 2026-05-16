import urllib.request
import csv
import datetime
import os

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTQYftjQ9fHLfDzmWIZ7QFdW0SplgDJPVpaaHKirmWkOERgEMNSr2yPcwXUNKRnxSwFRPTTQf8maQjs/pub?gid=134813518&single=true&output=csv"
OUTPUT_PATH = "data/Stock Watch.xml"

def parse_numeric(val):
    if not val: return 0.0
    try:
        # Remove currency symbols, commas, and %
        cleaned = "".join(c for c in str(val) if c.isdigit() or c in ".-")
        return float(cleaned)
    except:
        return 0.0

def analyze_stock(row):
    ticker = str(row[0]).strip().upper() if row[0] else "N/A"
    price = parse_numeric(row[2])   # Column C
    change = parse_numeric(row[5])  # Column F

    action = "HOLD"
    confidence = 85.0

    if change > 1.5:
        action = "BUY"
        confidence = min(98.0, 65.0 + (change * 2))
    elif change < -1.5:
        action = "SELL"
        confidence = min(98.0, 55.0 + abs(change * 2))

    return {
        "ticker": ticker,
        "price": price,
        "change": change,
        "action": action,
        "confidence": confidence
    }

def main():
    try:
        print(f"Fetching CSV data from {SHEET_CSV_URL}")
        response = urllib.request.urlopen(SHEET_CSV_URL)
        content = response.read().decode('utf-8')
        reader = csv.reader(content.splitlines())
        rows = list(reader)
    except Exception as e:
        print(f"Failed to fetch data: {e}")
        return

    # Skip header
    data_rows = [r for r in rows if r and r[0].lower() != "ticker" and r[0].strip()]
    
    stocks = [analyze_stock(r) for r in data_rows]
    
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<StockWatchReport>\n'
    xml += '  <Header>\n'
    xml += '    <Organization>Andrews Industries</Organization>\n'
    xml += f'    <Generated>{timestamp}</Generated>\n'
    xml += f'    <Count>{len(stocks)}</Count>\n'
    xml += '  </Header>\n'
    xml += '  <MarketData>\n'
    
    for s in stocks:
        xml += f'    <Stock ticker="{s["ticker"]}">\n'
        xml += f'      <Price>{s["price"]:.2f}</Price>\n'
        xml += f'      <ChangePercent>{s["change"]:.2f}</ChangePercent>\n'
        xml += '      <Analysis>\n'
        xml += f'        <Action>{s["action"]}</Action>\n'
        xml += f'        <Confidence>{s["confidence"]:.1f}</Confidence>\n'
        xml += '      </Analysis>\n'
        xml += '    </Stock>\n'
        
    xml += '  </MarketData>\n</StockWatchReport>'

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"Successfully generated {OUTPUT_PATH}")

if __name__ == "__main__":
    main()