import pandas as pd
import requests
import io
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime

# --- CONFIGURATION ---
CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSE3KbF9vc5pfq9E3-ysTS3dooWoe6yO1tmpxPVFMcr8qfn7u8zr8qADFqxLrbxkQgyLD5qBTO-kbPC/pub?output=csv'
# Using a relative path for GitHub Actions compatibility
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'Digital_Downloads.xml')

def sync_downloads_data():
    """Fetches the spreadsheet data, prints a summary, and saves to XML for the web UI."""
    print(f"[-] Fetching spreadsheet: {CSV_URL}")
    try:
        response = requests.get(CSV_URL, timeout=15)
        response.raise_for_status()
        
        # Handle potential empty CSVs
        csv_text = response.text.strip()
        if not csv_text:
            raise ValueError("The spreadsheet returned no data.")
        
        df = pd.read_csv(io.StringIO(csv_text))
        
        # Build XML Structure
        root = ET.Element('DigitalDownloadsReport')
        header = ET.SubElement(root, 'Header')
        ET.SubElement(header, 'Generated').text = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        ET.SubElement(header, 'Count').text = str(len(df))
        
        items_node = ET.SubElement(root, 'Items')

        processed_count = 0
        for index, row in df.iterrows():
            # Ensure we have at least: Name(0), Price(1), and Link(2)
            if len(row) < 3: continue
            
            name = str(row.iloc[0]).strip()
            price = str(row.iloc[1]).strip()
            link = str(row.iloc[2]).strip()

            if name == 'nan' or not name: continue
            if price != 'nan' and price and not price.startswith('$'):
                price = f"${price}"

            item = ET.SubElement(items_node, 'Item')
            ET.SubElement(item, 'Name').text = name
            ET.SubElement(item, 'Price').text = price
            ET.SubElement(item, 'Link').text = link
            processed_count += 1
            
        ET.SubElement(header, 'ProcessedCount').text = str(processed_count)
        print(f"[+] Successfully processed {processed_count} valid items.")

        # Pretty Print and Save
        xml_str = minidom.parseString(ET.tostring(root, 'utf-8')).toprettyxml(indent="    ")
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(xml_str)
        print(f"[+] Successfully updated: {OUTPUT_FILE}")

    except Exception as e:
        print(f"[!] Sync failed: {e}")

if __name__ == "__main__":
    sync_downloads_data()
