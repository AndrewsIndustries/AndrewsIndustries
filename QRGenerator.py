import pandas as pd
import qrcode # type: ignore
import os
import requests
import re
import io

# --- CONFIGURATION ---
CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTp9TnMwxNNqwp3Ol3kjBaxvwvsyX9iLUltpNS6kMNhyARRYMYMIFwKNoW3D25XxACg2jk1MpKNOdCE/pub?output=csv'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QR_DIR = os.path.join(BASE_DIR, 'images', 'QRCodes')

def sanitize_filename(name):
    """Removes invalid characters for file naming."""
    return re.sub(r'[^a-zA-Z0-9_]', '_', str(name).strip())

def generate_qr_assets():
    # 1. Create directory if it doesn't exist
    if not os.path.exists(QR_DIR):
        os.makedirs(QR_DIR)
        print(f"Created directory: {QR_DIR}")

    # 2. Fetch Spreadsheet Data
    print("Fetching data from Google Sheets...")
    try:
        # Use a timeout and headers to ensure a clean fetch
        response = requests.get(CSV_URL, timeout=10)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
    except Exception as e:
        print(f"Error fetching sheet: {e}")
        return

    # 3. Process Rows
    # Column A (Index 0) = Link | Column B (Index 1) = Name
    for index, row in df.iterrows():
        link = str(row.iloc[0]).strip()
        name = str(row.iloc[1]).strip()

        if not link or not name or link == 'nan' or name == 'nan':
            continue

        print(f"Generating QR for: {name}")
        
        # Generate QR
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(link)
        qr.make(fit=True)
        
        # Create Image and convert to RGB (required for JPG)
        img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        
        # Save as JPG
        filename = f"{sanitize_filename(name)}.jpg"
        filepath = os.path.join(QR_DIR, filename)
        img.save(filepath, "JPEG", quality=95)

    print(f"\nSuccess! All QR Codes saved to: {QR_DIR}")

if __name__ == "__main__":
    generate_qr_assets()