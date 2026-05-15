import streamlit as st
import requests
from bs4 import BeautifulSoup
import PyRSS2Gen
import datetime
from urllib.parse import urljoin
import io

st.set_page_config(
    page_title="Google News RSS Generator",
    page_icon="📰",
    layout="wide"
)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
BASE_URL = "https://news.google.com"

def fetch_google_news_data(url):
    """
    Fetches the HTML from Google News and parses article information.
    """
    try:
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        st.error(f"Failed to fetch URL: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.find_all("article")
    
    extracted_data = []
    
    for article in articles:
        # Title is usually inside an h3 or h4 or a specific class
        title_tag = article.find("h3") or article.find("h4") or article.find("a")
        link_tag = article.find("a", href=True)
        time_tag = article.find("time")
        
        if title_tag and link_tag:
            title = title_tag.get_text().strip()
            # Clean up relative links
            link = urljoin(BASE_URL, link_tag['href'])
            
            # Extract date if available
            pub_date = datetime.datetime.now()
            if time_tag and time_tag.get('datetime'):
                try:
                    # Google News usually uses ISO format strings
                    date_str = time_tag['datetime'].replace('Z', '+00:00')
                    pub_date = datetime.datetime.fromisoformat(date_str)
                except:
                    pass
            
            extracted_data.append({
                "title": title,
                "link": link,
                "pub_date": pub_date,
                "description": f"Source: {article.get_text()[:100]}..."
            })
            
    return extracted_data

def generate_rss_xml(data, original_url):
    """
    Generates a valid RSS 2.0 XML string using PyRSS2Gen.
    """
    items = []
    for entry in data:
        items.append(
            PyRSS2Gen.RSSItem(
                title=entry['title'],
                link=entry['link'],
                description=entry['description'],
                guid=PyRSS2Gen.Guid(entry['link']),
                pubDate=entry['pub_date']
            )
        )

    rss = PyRSS2Gen.RSS2(
        title="Google News Custom Feed",
        link=original_url,
        description="Automatically generated feed from Google News search results.",
        lastBuildDate=datetime.datetime.now(),
        items=items
    )
    
    return rss.to_xml(encoding="utf-8")

def main():
    st.title("📰 Google News to RSS Feed")
    st.markdown("""
    Convert any Google News search result URL into a functional RSS feed. 
    Simply paste the URL from your browser address bar below.
    """)

    url_input = st.text_input(
        "Enter Google News URL:", 
        placeholder="https://news.google.com/home?hl=en-US&gl=US&ceid=US%3Aen"
    )

    col1, col2 = st.columns([1, 4])
    
    with col1:
        generate_btn = st.button("Generate RSS", type="primary", use_container_width=True)

    if generate_btn:
        if not url_input:
            st.warning("Please enter a valid URL.")
            return

        with st.spinner("Scraping Google News..."):
            data = fetch_google_news_data(url_input)
            
            if data:
                st.success(f"Found {len(data)} articles!")
                
                # Generate XML
                rss_xml = generate_rss_xml(data, url_input)
                
                # Preview Table
                with st.expander("Preview Extracted Data", expanded=False):
                    st.table(data[:10]) # Show first 10 for preview

                # Download Section
                st.subheader("Your Generated RSS Feed")
                
                # Text area for raw code
                st.code(rss_xml, language="xml")
                
                # Download button
                st.download_button(
                    label="Download .xml file",
                    data=rss_xml,
                    file_name="google_news_feed.xml",
                    mime="application/rss+xml"
                )
            else:
                st.error("No articles found. Please check the URL or try a different search.")

if __name__ == "__main__":
    main()