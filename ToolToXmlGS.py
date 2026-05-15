import streamlit as st
import pandas as pd
import PyRSS2Gen
import datetime
import re
from io import StringIO

st.set_page_config(
    page_title="GSheet to RSS Converter",
    page_icon="📡",
    layout="wide"
)

def transform_gsheet_url(url):
    """
    Converts various Google Sheets URL formats into a direct CSV export URL.
    Supports both 'Publish to the web' and standard sharing links.
    """
    # Extract GID if present
    gid_match = re.search(r'gid=([0-9]+)', url)
    gid = gid_match.group(1) if gid_match else "0"

    # Case 1: Published to web links (/d/e/...)
    if "/d/e/" in url:
        base_url = url.split('?')[0].replace('/pubhtml', '/pub')
        return f"{base_url}?gid={gid}&single=true&output=csv"

    # Case 2: Standard sharing links (/d/ID/...)
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    if match:
        sheet_id = match.group(1)
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

    return None

def generate_rss(df, feed_title, feed_link, feed_desc):
    """
    Maps the processed DataFrame rows to RSS items.
    """
    items = []
    
    for _, row in df.iterrows():
        try:
            # Ensure the pubDate is a valid datetime object for PyRSS2Gen
            pub_date = pd.to_datetime(row['pubDate'])
            
            # If the timezone info is missing, assume UTC for RFC 822 compliance
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=datetime.timezone.utc)

            rss_item = PyRSS2Gen.RSSItem(
                title=str(row['title']),
                link=str(row['link']),
                description=str(row['description']),
                guid=PyRSS2Gen.Guid(str(row['link'])),
                pubDate=pub_date
            )
            items.append(rss_item)
        except Exception as e:
            st.warning(f"Skipping row due to error: {e}")

    rss_feed = PyRSS2Gen.RSS2(
        title=feed_title,
        link=feed_link,
        description=feed_desc,
        lastBuildDate=datetime.datetime.now(datetime.timezone.utc),
        items=items
    )
    
    return rss_feed.to_xml(encoding='utf-8')

def main():
    st.title("📡 Google Sheets to RSS Converter")
    st.markdown("""
    Convert any **publicly accessible** Google Sheet into an RSS 2.0 feed.
    This tool now automatically maps **Column A (Title)**, **Column C (Link)**, and **Column F (Description)**.
    """)

    with st.sidebar:
        st.header("Feed Configuration")
        feed_title = st.text_input("Feed Title", value="My Google Sheet Feed")
        feed_desc = st.text_area("Feed Description", value="RSS feed automatically generated from a Google Sheet.")
        feed_link = st.text_input("Site URL", value="https://docs.google.com")

    gsheet_url = st.text_input(
        "Enter Google Sheet URL", 
        placeholder="https://docs.google.com/spreadsheets/d/your-id/edit#gid=0"
    )

    if gsheet_url:
        export_url = transform_gsheet_url(gsheet_url)
        
        if not export_url:
            st.error("❌ Invalid Google Sheets URL format.")
            return

        try:
            with st.spinner("Fetching data from Google Sheets..."):
                # Read without headers to ignore existing names and get index-based access
                df_raw = pd.read_csv(export_url, header=None)
            
            if len(df_raw.columns) < 6:
                st.error("❌ The sheet must have at least 6 columns (A through F).")
                return

            # Extract header names from Row 1 (Index 0)
            headers = df_raw.iloc[0]
            
            # Map data starting from Row 2 (Index 1)
            rss_df = pd.DataFrame()
            rss_df['title'] = df_raw.iloc[1:, 0]       # Column A
            rss_df['link'] = df_raw.iloc[1:, 2]        # Column C
            rss_df['description'] = df_raw.iloc[1:, 5] # Column F
            # Auto-generate pubDate since the requirement was removed
            rss_df['pubDate'] = datetime.datetime.now(datetime.timezone.utc)

            st.success(f"✅ Loaded. Mapping: [A] {headers[0]} | [C] {headers[2]} | [F] {headers[5]}")
                
            # Preview Data using the custom headers from Row 1
            with st.expander("Preview Mapped Data", expanded=True):
                preview = rss_df[['title', 'link', 'description']].copy()
                preview.columns = [str(headers[0]), str(headers[2]), str(headers[5])]
                st.dataframe(preview, use_container_width=True)

            if st.button("🚀 Generate & Download RSS"):
                try:
                    rss_xml = generate_rss(rss_df, feed_title, feed_link, feed_desc)
                    
                    st.download_button(
                        label="📥 Download .xml file",
                        data=rss_xml,
                        file_name="feed.xml",
                        mime="application/rss+xml"
                    )
                    st.code(rss_xml[:1000] + "...", language="xml")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error generating RSS: {e}")

        except Exception as e:
            st.error("❌ Could not access the spreadsheet.")
            st.error(f"Details: {e}")
            st.info("Check if the spreadsheet is set to 'Anyone with the link can view'. Private sheets require OAuth/Service Accounts.")

if __name__ == "__main__":
    main()