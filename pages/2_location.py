import streamlit as st
import pandas as pd
import requests
from io import StringIO # Don't forget this import!
import pydeck as pdk  # Ensure pip install pydeck

# Function to wipe session data
def clear_session():
    for key in list(st.session_state.keys()):
        del st.session_state[key]

uploaded_file = st.sidebar.file_uploader("Upload credentials.txt", type=["txt"])
if uploaded_file and 'creds' not in st.session_state:
    content = uploaded_file.read().decode("utf-8")
    creds = {}
    for line in content.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            creds[k.strip()] = v.strip()
    st.session_state['creds'] = creds
    st.success("Credentials stored in session!")

if 'creds' in st.session_state:
    if st.button("showcredential"):
        c = st.session_state['creds']
        baseurl=str(c.get('str'))
        token=str(c.get('token'))
        #URL = f"http://{baseurl}/csp/myrest/event/7"
        URL = f"http://{baseurl}/csp/ibiapi/location/all"
        AUTH_HEADER = f"Basic {token}" # Replace with your actual encoded credentials
        try:
            headers = {
                'Authorization': AUTH_HEADER
            }
            response = requests.get(URL, headers=headers)
            # Check if request was successful
            if response.status_code == 200:
                # Display result in a large text area
                st.success(f"Success! Status Code: {response.status_code}")
                # 2. Create the DataFrame
                raw_text = response.text
                # FIX: Wrap the text in StringIO so pandas doesn't think it's a filename
                df = pd.read_csv(StringIO(raw_text))
                st.session_state['ldf']=df
            else:
                st.error(f"Failed to fetch data. Status Code: {response.status_code}")
                st.text(response.text)
        except Exception as e:
            st.error(f"An error occurred: {e}")

if 'ldf' in st.session_state:
    df = st.session_state['ldf'].copy()
    
    st.subheader("Map View")
    # Clean data: drop rows missing lat/lon, convert to numeric format
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df = df.dropna(subset=['latitude', 'longitude'])
    
    if not df.empty:
        # Configure the data map layer
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position="[longitude, latitude]",
            get_color="[200, 30, 0, 160]",
            get_radius=50000,  # Radius size in meters
            pickable=True,     # Must be True for tooltips to function
        )
        
        # Center view around map coordinates
        view_state = pdk.ViewState(
            latitude=df['latitude'].mean(),
            longitude=df['longitude'].mean(),
            zoom=4,
            pitch=0,
        )
        
        # Build pydeck container with custom HTML tooltips
        st.pydeck_chart(
            pdk.Deck(
                layers=[layer],
                initial_view_state=view_state,
                tooltip={
                    "html": "<b>Org:</b> {organization}<br/>"
                            "<b>Type:</b> {organizationtype}<br/>"
                            "<b>Location:</b> {location}<br/>"
                            "<b>Patients:</b> {patients}<br/>"
                            "<b>Product:</b> {product}<br/>"
                            "<b>Connections:</b> {connections}",
                    "style": {"backgroundColor": "chocolate", "color": "white"}
                }
            )
        )

        st.subheader("Data Table View")
        st.dataframe(df)
    else:
        st.warning("No valid coordinate data available to render the map.")

# 4. Clear everything
if st.sidebar.button("Clear All Session Data"):
    clear_session()
    st.rerun()

st.sidebar.info("Note: All session data is automatically destroyed when the browser tab is closed.")