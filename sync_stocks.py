import pandas as pd
import datetime
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom

# --- CONFIGURATION ---
# URL to your source Google Sheet exported as CSV
CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTQYftjQ9fHLfDzmWIZ7QFdW0SplgDJPVpaaHKirmWkOERgEMNSr2yPcwXUNKRnxSwFRPTTQf8maQjs/pub?gid=134813518&single=true&output=csv'
# Target path for the generated XML report
XML_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'Stock Watch.xml')

def sync_spreadsheet_to_xml():
    """
    Reads stock data from a CSV and exports it to a structured XML file.
    Strictly maps Column T as a raw string without numeric conversion.
    """
    stocks_data = []
    # 1. Fetch and Parse CSV
    try:
        df = pd.read_csv(CSV_URL)
        
        # Dynamically find the index for 'WARMING OR COOLING' to match JS logic
        headers = [str(c).strip().upper() for c in df.columns]
        try:
            status_idx = headers.index('WARMING OR COOLING')
        except ValueError:
            status_idx = 19  # Fallback to Column T if header not found
            
        for i in range(len(df)):
            ticker_val = str(df.iloc[i, 0]).strip()
            
            # Skip empty/invalid rows
            if ticker_val == 'nan' or not ticker_val:
                continue
                
            price_val = str(df.iloc[i, 2]).strip()
            if price_val.lower() != 'nan' and not price_val.startswith('$'):
                price_val = f"${price_val}"
                
            change_val = str(df.iloc[i, 5]).strip()
            if change_val.lower() != 'nan' and not change_val.endswith('%'):
                change_val = f"{change_val}%"

            stocks_data.append({
                'ticker': ticker_val,
                'price': price_val,
                'days_change': change_val,
                'warming_cooling': str(df.iloc[i, status_idx]).strip()  
            })  

    except Exception as e:
        print(f"Error: Could not fetch CSV from {CSV_URL}")
        print(f"Details: {e}")
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
    try:
        xml_str = minidom.parseString(ET.tostring(root, 'utf-8')).toprettyxml(indent="    ")
        
        # Ensure target directory exists
        os.makedirs(os.path.dirname(XML_OUTPUT_PATH), exist_ok=True)
        
        with open(XML_OUTPUT_PATH, 'w', encoding='utf-8') as f:
            f.write(xml_str)
        print(f"Successfully generated XML report with {len(stocks_data)} items at {XML_OUTPUT_PATH}")
        
    except Exception as e:
        print(f"Failed to write XML output file: {e}")

if __name__ == "__main__":
    sync_spreadsheet_to_xml()