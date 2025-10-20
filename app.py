import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="Asset Correlation MVP",
    layout="wide"
)

# --- App Title ---
st.title('Interactive Asset Class Correlation Dashboard')

# --- User Inputs ---
API_KEY = st.text_input("Enter your Polygon.io API Key:", type="password")
TICKERS = ["SPY", "IWM", "VEA", "VWO", "AGG", "GOVT", "GLD", "DBC", "VNQ", "BTC-USD"]
rolling_window = st.slider(
    'Select Rolling Window (Days)', 
    min_value=30, 
    max_value=365, 
    value=90,
    step=10
)

# --- Data Fetching Function (FIXED) ---
@st.cache_data
# FIX #1: We removed the '_status_element' argument.
# This function is now "pure" and only returns data.
def fetch_all_data(tickers, api_key):
    """
    Fetches historical data for a list of tickers, pausing between
    requests to respect the free plan's rate limit.
    """
    price_data = {}
    for ticker in tickers:
        # FIX #2: The line writing to the status element is REMOVED from the loop.
        try:
            api_ticker = "X:BTCUSD" if ticker == "BTC-USD" else ticker
            url = f"https.api.polygon.io/v2/aggs/ticker/{api_ticker}/range/1/day/2020-01-01/2025-09-19?adjusted=true&sort=asc&limit=50000&apiKey={api_key}"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data.get("resultsCount", 0) > 0:
                df = pd.DataFrame(data['results'])
                df['date'] = pd.to_datetime(df['t'], unit='ms')
                price_data[ticker] = df.set_index('date')['c']
            else:
                st.warning(f"No data found for {ticker}.")
                
            time.sleep(13) 
            
        except requests.exceptions.RequestException as e:
            # We can't write to st.error here, so we'll just return None
            # and let the main app logic handle the error display.
            print(f"Error fetching data for {ticker}: {e}") # Log to terminal
            return None
    return pd.DataFrame(price_data)

# --- Main App Logic ---
status_text = st.empty()

if API_KEY:
    # FIX #3: We show a single "waiting" message *before* calling the cached function.
    status_text.text("Fetching all asset data... This may take over 2 minutes on the first load. Please wait.")
    
    # We call the simplified function.
    all_prices = fetch_all_data(TICKERS, API_KEY)

    if all_prices is not None and not all_prices.empty:
        status_text.success("Data fetched successfully!")
        
        daily_returns = all_prices.pct_change().dropna()
        correlation_matrix = daily_returns.tail(rolling_window).corr()

        st.subheader(f'Interactive {rolling_window}-Day Correlation Heatmap')
        fig = px.imshow(
            correlation_matrix,
            text_auto=True, 
            aspect="auto",
            color_continuous_scale='RdBu',
            labels=dict(color="Correlation")
        )
        fig.update_layout(title_text=f'Asset Class Correlation ({rolling_window}-Day)', title_x=0.5)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader(f'Top 5 Most & Least Correlated Pairs (Last {rolling_window} Days)')
        corr_pairs = correlation_matrix.unstack().sort_values(ascending=False)
        corr_pairs = corr_pairs[corr_pairs != 1.0].drop_duplicates()

        col1, col2 = st.columns(2)
        with col1:
            st.write("**Most Correlated:**")
            st.dataframe(corr_pairs.head(5))
        with col2:
            st.write("**Least Correlated:**")
            st.dataframe(corr_pairs.tail(5))

    elif all_prices is None and API_KEY:
        status_text.error("Data fetching failed. Check terminal for error (or check API key).")
else:
    status_text.warning("Please enter your API key above to begin.")