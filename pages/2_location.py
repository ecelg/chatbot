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
    # Clean the primary dataframe once
    df_clean = st.session_state['ldf'].copy()
    df_clean['latitude'] = pd.to_numeric(df_clean['latitude'], errors='coerce')
    df_clean['longitude'] = pd.to_numeric(df_clean['longitude'], errors='coerce')
    df_clean = df_clean.dropna(subset=['latitude', 'longitude'])

    # Define the target products for your 3 tabs
    prod1 = "HealthShare Health Information Exchange"
    prod2 = "IRIS for Health"
    
    # Create the 3 navigation tabs
    tab1, tab2, tab3 = st.tabs([prod1, prod2, "Other Products"])
    
    # Helper function to generate table and pydeck map for a filtered dataframe
    def render_tab_content(filtered_df):
        if not filtered_df.empty:
            
            st.subheader("Geographical Distribution")
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=filtered_df,
                get_position="[longitude, latitude]",
                get_color="[220, 50, 50, 160]",  # Translucent reddish marker
                get_radius=60000,
                pickable=True,
            )
            view_state = pdk.ViewState(
                latitude=filtered_df['latitude'].mean(),
                longitude=filtered_df['longitude'].mean(),
                zoom=4,
            )
            st.pydeck_chart(
                pdk.Deck(
                    layers=[layer],
                    initial_view_state=view_state,
                    tooltip={
                        "html": "<b>Org:</b> {organization}<br/>"
                                "<b>Type:</b> {organizationtype}<br/>"
                                "<b>Location:</b> {location}<br/>"
                                "<b>Patients:</b> {patients}<br/>"
                                "<b>Facilities:</b> {facilities}<br/>"                                
                                "<b>Hospitals:</b> {hospitals}<br/>"
                                "<b>Connections:</b> {connections}",
                        "style": {"backgroundColor": "chocolate", "color": "white"}
                    }
                )
            )

            st.subheader("Filtered Data View")
            st.dataframe(filtered_df)

        else:
            st.info("No matching records found for this product selection.")

    # Populate Tab 1: HealthShare HIE
    with tab1:
        df_prod1 = df_clean[df_clean['product'] == prod1]
        render_tab_content(df_prod1)

    # Populate Tab 2: IRIS for Health
    with tab2:
        df_prod2 = df_clean[df_clean['product'] == prod2]
        render_tab_content(df_prod2)

    # Populate Tab 3: Everything else
    with tab3:
        df_other = df_clean[~df_clean['product'].isin([prod1, prod2])]
        render_tab_content(df_other)

# 4. Clear everything
if st.sidebar.button("Clear All Session Data"):
    clear_session()
    st.rerun()

st.sidebar.info("Note: All session data is automatically destroyed when the browser tab is closed.")