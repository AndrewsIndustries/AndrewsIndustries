import pandas as pd
import datetime
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom

# --- CONFIGURATION ---
# URL to your source Google Sheet exported as CSV
CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTQYftjQ9fHLfDzmWIZ7QFdW0SplgDJPVpaaHKirmWkOERgEMNSr2yPcwXUNKRnxSwFRPTTQf8maQjs/pub?gid=134813518&single=true&output=csv'
# Target path for the generated XML report
XML_OUTPUT_PATH = r'C:\Users\andre\Documents\GitHub\AndrewsIndustries\data\Stock Watch.xml'

def sync_spreadsheet_to_xml():
    """
    Reads stock data from a CSV and exports it to a structured XML file.
    Strictly maps Column T as a raw string without numeric conversion.
    """
    stocks_data = []
    # 1. Fetch and Parse CSV
    try:
        df = pd.read_csv(CSV_URL)
        for _, row in df.iterrows():
            stocks_data.append({
                'ticker': row[0],
                'price': str(row[2]),
                'days_change': str(row[5]),
                'warming_cooling': str(row[19])  
            })  



    except FileNotFoundError:
        print(f"Error: Could not fetch CSV from {CSV_URL}")
        return

    # 2. Build XML Structure
    root = ET.Element('StockWatchReport')
    header = ET.SubElement(root, 'Header')
    ET.SubElement(header, 'Organization').text = 'Andrews Industries'
    ET.SubElement(header, 'Generated').text = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    ET.SubElement(header, 'Count').text = str(len(stocks_data))
    
    market_data = ET.SubElement(root, 'MarketData')
    for stock in stocks_data:
        stock_node = ET.SubElement(market_data, 'Stock', ticker=stock['ticker'])
        ET.SubElement(stock_node, 'Price').text = stock['price']
        ET.SubElement(stock_node, 'DaysChange').text = stock['days_change']
        ET.SubElement(stock_node, 'warming_cooling').text = stock['warming_cooling']

    # 3. Write to file with pretty formatting
    xml_str = minidom.parseString(ET.tostring(root, 'utf-8')).toprettyxml(indent="  ")
    os.makedirs(os.path.dirname(XML_OUTPUT_PATH), exist_ok=True)
    with open(XML_OUTPUT_PATH, "w", encoding='utf-8') as f:
        f.write(xml_str)
    print(f"Sync complete. {len(stocks_data)} stocks exported to {XML_OUTPUT_PATH}")

if __name__ == "__main__":
    sync_spreadsheet_to_xml()