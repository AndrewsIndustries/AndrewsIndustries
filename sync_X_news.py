try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    feedparser = None
    FEEDPARSER_AVAILABLE = False
    import xml.etree.ElementTree as ET

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

def get_nitter_urls(handle):
    """Returns multiple instance URLs for redundancy."""
    instances = [
        'https://nitter.privacydev.net',
        'https://nitter.poast.org',
        'https://nitter.perennialte.ch',
        'https://nitter.net'
    ]
    return [f"{inst}/{handle}/rss" for inst in instances]

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'x_news.json')

def clean_text(text):
    """Strips HTML tags and cleans up whitespace."""
    if not text: return ""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Remove tracking pixels or weird artifacts
    clean = ' '.join(clean.split())
    return clean

def classify_urgency(headline, summary):
    """Objective urgency classification based on keyword triggers."""
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

def sync_x_news():
    """Ingests X (Twitter) RSS feeds and outputs a clean, unified JSON array."""
    print(f"[-] Initializing X Content Ingest...")
    
    seen_titles = set()
    unified_data = []
    # Browser-like headers to prevent 403 Forbidden errors
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}

    for handle in X_HANDLES:
        success = False
        for url in get_nitter_urls(handle):
            if success: break
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code != 200: continue
                
                entries = []
                if FEEDPARSER_AVAILABLE:
                    feed = feedparser.parse(response.content)
                    entries = feed.entries
                else:
                    root = ET.fromstring(response.content)
                    for item in root.findall('.//item'):
                        entries.append({
                            'title': item.findtext('title'),
                            'summary': item.findtext('description'),
                            'link': item.findtext('link'),
                            'id': item.findtext('guid') or item.findtext('link')
                        })

                if not entries: continue

                for entry in entries:
                    headline = clean_text(entry.get('title', ''))
                    if not headline or headline in seen_titles: continue
                    seen_titles.add(headline)

                    summary_raw = entry.get('summary', entry.get('description', ''))
                    summary = clean_text(summary_raw)[:280]
                    alert_level = classify_urgency(headline, summary)
                    
                    item = {
                        "id": entry.get('id', hashlib.md5(headline.encode()).hexdigest()),
                        "timestamp_z": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                        "link": entry.get('link', entry.get('id', '#')),
                        "source": f"@{handle.upper()}",
                        "headline": headline,
                        "summary": summary,
                        "alert_level": alert_level,
                        "primary_region": identify_region(headline + " " + summary)
                    }
                    unified_data.append(item)
                
                success = True
                print(f"[+] Synced @{handle}")
            except Exception:
                continue
        
        if not success:
            print(f"[!] Failed to sync @{handle} from all instances.")

    # Ensure the feed is never empty so the ticker doesn't stall
    if not unified_data:
        unified_data.append({
            "id": "sys-check",
            "timestamp_z": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "source": "@SYSTEM",
            "headline": "X Content Stream active. Waiting for new updates from handles...",
            "alert_level": "LOW",
            "primary_region": "Global"
        })

    # Save strictly as JSON array
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(unified_data, f, indent=2)
    
    print(f"[+] X News Sync Complete. {len(unified_data)} events processed.")
    return json.dumps(unified_data) # Strict JSON output

if __name__ == "__main__":
    sync_x_news()