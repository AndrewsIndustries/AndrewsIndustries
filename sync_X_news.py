import feedparser
import hashlib
import json
import re
import os
from datetime import datetime, timezone
import requests

# --- CONFIGURATION ---
# Add or remove X (Twitter) handles here
X_HANDLES = [
    'conflict_radar',
    'osintwarfare',
    'Osinttechnical',
    'sentdefender',
    'PolymarketIntel'
]

def get_nitter_url(handle):
    return f'https://nitter.poast.org/{handle}/rss'

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'osint_news.json')

def clean_text(text):
    """Strips HTML tags and removes broken encodings."""
    if not text: return ""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Remove tracking pixels or weird artifacts
    clean = ' '.join(clean.split())
    return clean

def classify_urgency(headline, summary):
    """Objective urgency classification based on intelligence heuristics."""
    text = (headline + " " + summary).lower()
    
    high_triggers = [
        'strike', 'war', 'invasion', 'missile', 'blockade', 'nuclear', 'offensive', 
        'combat', 'cyberattack', 'casualty', 'breaking', 'urgent', 'intercept'
    ]
    med_triggers = ['exercise', 'military drill', 'explosion', 'diplomatic shift', 'unconfirmed', 'alert', 'protest', 'deployment', 'sanction', 'satellite', 'geolocated']
    
    if any(kw in text for kw in high_triggers):
        return "HIGH"
    if any(kw in text for kw in med_triggers):
        return "MEDIUM"
    return "LOW"

def identify_region(text):
    """Extracts primary region or body of water involved."""
    regions = [
        "Ukraine", "Russia", "Israel", "Gaza", "Iran", "Taiwan", "China", 
        "Red Sea", "Middle East", "North Korea", "South China Sea", "USA", 
        "Europe", "NATO", "Pacific", "Arctic", "Lebanon", "Yemen", "Sudan", 
        "Black Sea", "Baltic"
    ]
    for region in regions:
        if region.lower() in text.lower():
            return region
    return "Global"

def sync_osint():
    """Ingests raw XML feeds and outputs a clean, unified JSON array."""
    print(f"[-] Initializing OSINT Ingest...")
    
    seen_titles = set()
    unified_data = []
    # Browser-like headers to prevent 403 Forbidden errors from OSINT providers
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    for handle in X_HANDLES:
        url = get_nitter_url(handle)
        try:
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            feed = feedparser.parse(response.content)

            for entry in feed.entries:
                headline = clean_text(entry.get('title', ''))
                
                # 1. Deduplication
                if not headline or headline in seen_titles:
                    continue
                seen_titles.add(headline)

                # 2. Content Cleaning & Summary
                summary_raw = entry.get('summary', entry.get('description', ''))
                summary = clean_text(summary_raw)[:280]

                # 3. Urgency Classification
                alert_level = classify_urgency(headline, summary)
                
                # 4. Data Construction
                item = {
                    "id": entry.get('id', hashlib.md5(headline.encode()).hexdigest()),
                    "timestamp_z": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    "source": f"@{handle.upper()}",
                    "headline": headline,
                    "summary": summary,
                    "alert_level": alert_level,
                    "primary_region": identify_region(headline + " " + summary)
                }
                unified_data.append(item)

        except Exception as e:
            print(f"[!] Error processing @{handle}: {e}")

    # Save strictly as JSON array
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(unified_data, f, indent=2)
    
    print(f"[+] OSINT Sync Complete. {len(unified_data)} events processed.")
    return json.dumps(unified_data) # Strict JSON output

if __name__ == "__main__":
    sync_osint()