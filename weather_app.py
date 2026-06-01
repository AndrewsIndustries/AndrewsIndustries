import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import os

# Configuration
LAT, LON = 39.2348, -119.5839

st.set_page_config(page_title="Andrews Industries Weather", layout="wide")

# Load shared CSS
css_path = os.path.join(os.path.dirname(__file__), "weather.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def get_weather_data():
    # NWS requires a User-Agent header with contact info
    headers = {'User-Agent': '(AndrewsIndustries Weather App, contact: andre@example.com)'}
    
    # 1. Get NWS Points
    resp = requests.get(f"https://api.weather.gov/points/{LAT},{LON}", headers=headers)
    resp.raise_for_status()
    pts = resp.json()
    city = pts['properties']['relativeLocation']['properties']['city']
    
    # 2. Get Forecasts & Observations with robust error handling
    def safe_get_json(url):
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        return r.json()

    try:
        hourly = safe_get_json(pts['properties']['forecastHourly'])
        daily = safe_get_json(pts['properties']['forecast'])
        stations = safe_get_json(pts['properties']['observationStations'])
        
        obs = {}
        if stations and stations.get('features') and len(stations['features']) > 0:
            obs_url = f"{stations['features'][0]['id']}/observations/latest"
            obs_data = safe_get_json(obs_url)
            if obs_data: obs = obs_data
    except Exception as e:
        st.error(f"NWS Data Sync Error: {e}")
        st.stop()
    
    # 3. Space Weather & Ephemeris
    sun = requests.get(f"https://api.sunrise-sunset.org/json?lat={LAT}&lng={LON}&formatted=0").json()
    kp_resp = requests.get("https://services.swpc.noaa.gov/products/summary-planetary-k-index.json", timeout=5)
    kp = kp_resp.json() if kp_resp.ok else []
    
    return city, hourly, daily, obs, sun, kp

with st.sidebar:
    st.header("System Controls")
    if st.button("🔄 Force Sync"):
        st.cache_data.clear()
        st.toast("Cache cleared. Synchronizing with NWS...")
        st.rerun()
    st.info(f"Lat: {LAT}, Lon: {LON}")

try:
    city, hourly, daily, obs, sun, kp = get_weather_data()
    current = hourly['properties']['periods'][0]
    
    st.title(f"Live Weather: {city}, NV")
    
    # Row 1: Key Metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Temperature", f"{current['temperature']}°F")
    m2.metric("Conditions", current['shortForecast'])
    m3.metric("Humidity", f"{current['relativeHumidity']['value']}%")
    m4.metric("Wind", f"{current['windSpeed']} {current['windDirection']}")
    
    pa = obs.get('properties', {}).get('barometricPressure', {}).get('value')
    inHg = round(pa * 0.0002953, 2) if pa is not None else "N/A"
    m5.metric("Barometer", f"{inHg} inHg")

    # Row 2: Radar and Ephemeris
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("Regional Radar Loop")
        st.image("https://radar.weather.gov/ridge/standard/KRGX_0.gif", use_container_width=True)
    
    with c2:
        st.subheader("Sun & Space")
        sunrise = datetime.fromisoformat(sun['results']['sunrise']).strftime('%I:%M %p')
        sunset = datetime.fromisoformat(sun['results']['sunset']).strftime('%I:%M %p')
        st.write(f"**Sunrise:** {sunrise}")
        st.write(f"**Sunset:** {sunset}")
        current_kp = kp[-1]['kp_index'] if kp else "N/A"
        st.write(f"**Current Kp Index:** {current_kp}")
        st.subheader("Local DOT Cam")
        st.video("https://d2wse2.its.nv.gov:443/renoxcd02/6d2490ff-1896-4369-b7e4-92fd1a542642_hspflirxcd02_public.stream/playlist.m3u8", autoplay=True, muted=True)

    # Row 3: Hourly Slider
    st.subheader("Hourly Forecast (Next 12 Hours)")
    h_cols = st.columns(12)
    hourly_periods = hourly.get('properties', {}).get('periods', [])
    max_h = min(12, len(hourly_periods) - 1)
    for i in range(max_h):
        p = hourly['properties']['periods'][i+1]
        time_label = datetime.fromisoformat(p['startTime']).strftime('%H:00')
        h_cols[i].write(f"**{time_label}**")
        h_cols[i].write(f"{p['temperature']}°")
        h_cols[i].caption(p['shortForecast'])

    # Row 4: 7-Day Forecast
    st.subheader("7-Day Forecast Matrix")
    daily_periods = daily.get('properties', {}).get('periods', [])
    num_days = min(7, len(daily_periods) // 2)
    d_cols = st.columns(num_days)
    for i in range(0, num_days * 2, 2): # Steps of 2 to get daytime periods
        p = daily['properties']['periods'][i]
        d_cols[i//2].write(f"**{p['name']}**")
        d_cols[i//2].write(f"{p['temperature']}°")
        d_cols[i//2].caption(p['shortForecast'])

except Exception as e:
    st.error(f"Failed to load dashboard: {e}")
