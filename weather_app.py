import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Configuration
LAT, LON = 39.2348, -119.5839
GITHUB_DARK_THEME = """
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    [data-testid="stMetricValue"] { color: #58a6ff !important; }
    .stMarkdown h1, .stMarkdown h2 { color: #f0f6fc; }
    div[data-testid="metric-container"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 8px;
    }
    </style>
"""

st.set_page_config(page_title="Andrews Industries Weather", layout="wide")
st.markdown(GITHUB_DARK_THEME, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def get_weather_data():
    # 1. Get NWS Points
    pts = requests.get(f"https://api.weather.gov/points/{LAT},{LON}").json()
    city = pts['properties']['relativeLocation']['properties']['city']
    
    # 2. Get Forecasts & Observations
    hourly = requests.get(pts['properties']['forecastHourly']).json()
    daily = requests.get(pts['properties']['forecast']).json()
    stations = requests.get(pts['properties']['observationStations']).json()
    obs = requests.get(f"{stations['features'][0]['id']}/observations/latest").json()
    
    # 3. Space Weather & Ephemeris
    sun = requests.get(f"https://api.sunrise-sunset.org/json?lat={LAT}&lng={LON}&formatted=0").json()
    kp = requests.get("https://services.swpc.noaa.gov/products/summary-planetary-k-index.json").json()
    
    return city, hourly, daily, obs, sun, kp

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
    
    pa = obs['properties']['barometricPressure']['value']
    inHg = round(pa * 0.0002953, 2) if pa else "N/A"
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
        st.write(f"**Current Kp Index:** {kp[-1]['kp_index']}")
        st.subheader("Local DOT Cam")
        st.image("https://nvroads.com/map/CCTV/714--7")

    # Row 3: Hourly Slider
    st.subheader("Hourly Forecast (Next 12 Hours)")
    h_cols = st.columns(12)
    for i in range(12):
        p = hourly['properties']['periods'][i+1]
        time_label = datetime.fromisoformat(p['startTime']).strftime('%H:00')
        h_cols[i].write(f"**{time_label}**")
        h_cols[i].write(f"{p['temperature']}°")
        h_cols[i].caption(p['shortForecast'])

    # Row 4: 7-Day Forecast
    st.subheader("7-Day Forecast Matrix")
    d_cols = st.columns(7)
    for i in range(0, 14, 2): # Steps of 2 to get daytime periods
        p = daily['properties']['periods'][i]
        d_cols[i//2].write(f"**{p['name']}**")
        d_cols[i//2].write(f"{p['temperature']}°")
        d_cols[i//2].caption(p['shortForecast'])

except Exception as e:
    st.error(f"Failed to load dashboard: {e}")
