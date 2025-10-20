import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="Asset Correlation Dashboard",
    layout="wide"
)

# --- App Title ---
st.title('Interactive Asset Class Correlation Dashboard')

# --- User Inputs ---
# We removed the API key text box. The slider is now the main input.
rolling_window = st.slider(
    'Select Rolling Window (Days)', 
    min_value=30, 
    max_value=365, 
    value=90,
    step=10
)

# --- Data Fetching Function ---
@st.cache_data
def fetch_all_data(tickers, api_key):
    """
    Fetches historical data for a list of tickers, pausing between
    requests to respect the free plan's rate limit.
    """
    price_data = {}
    
    # We create a status message inside the function for the first load
    status_text = st.empty()
    
    for ticker in tickers:
        status_text.text(f"Fetching data for {ticker}...") 
        try:
            api_ticker = "X:BTCUSD" if ticker == "BTC-USD" else ticker
            url = f"https://api.polygon.io/v2/aggs/ticker/{api_ticker}/range/1/day/2020-01-01/2025-09-19?adjusted=true&sort=asc&limit=50000&apiKey={api_key}"
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
            st.error(f"Error fetching data for {ticker}: {e}")
            return None
            
    status_text.empty() # Clear the "Fetching..." message
    return pd.DataFrame(price_data)

# --- Main App Logic ---
TICKERS = ["SPY", "IWM", "VEA", "VWO", "AGG", "GOVT", "GLD", "DBC", "VNQ", "BTC-USD"]

# Check if the secret key is provided
if "POLYGON_API_KEY" in st.secrets:
    API_KEY = st.secrets["POLYGON_API_KEY"]
    
    # Fetch the data. This will be slow on the app's first-ever load.
    all_prices = fetch_all_data(TICKERS, API_KEY)

    if all_prices is not None and not all_prices.empty:
        st.success("Data loaded successfully!")
        
        # --- Calculations (now happens *after* data is loaded) ---
        daily_returns = all_prices.pct_change().dropna()
        correlation_matrix = daily_returns.tail(rolling_window).corr()

        # --- Display Heatmap ---
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

        # --- Display Pairs ---
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

    else:
        st.error("There was an error loading the data. The API key may be invalid or the service may be down.")
else:
    st.error("App is not configured correctly. Missing API key secret.")