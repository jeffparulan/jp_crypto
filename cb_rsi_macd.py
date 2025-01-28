import requests
import pandas as pd
import ta
import time
import os

# List of cryptocurrency trading pairs to monitor (use Coinbase product IDs)
cryptos = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'AVAX-USD', 'APT-USD', 'LINK-USD', 'RNDR-USD', 'SUI-USD', 'AR-USD', 'INJ-USD', 'TIA-USD']

# Paths to default system sounds
LONG_BEEP_FILE = '/System/Library/Sounds/Glass.aiff'  # Example sound for LONG
SHORT_BEEP_FILE = '/System/Library/Sounds/Funk.aiff'  # Example sound for SHORT

# Function to fetch candlestick data from Coinbase Advanced Trade API
def fetch_candlestick_data(product_id, granularity=60):
    """
    Fetch candlestick data from Coinbase Advanced Trade API.
    :param product_id: Trading pair (e.g., BTC-USD)
    :param granularity: Candlestick interval in seconds (e.g., 60 for 1 minute)
    :return: List of close prices
    """
    url = f'https://api.exchange.coinbase.com/products/{product_id}/candles'
    params = {
        'granularity': granularity  # Time interval in seconds (60 = 1 minute)
    }
    headers = {
        'Accept': 'application/json',
    }
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        data = response.json()
        # Extract close prices from candlestick data
        return [candle[4] for candle in data]  # '4' is the close price index
    else:
        return None

# Function to fetch spot price from Coinbase (real-time)
def fetch_spot_price(product_id):
    url = f'https://api.coinbase.com/v2/prices/{product_id}/spot'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return float(data['data']['amount'])
    else:
        return None

# Function to calculate RSI
def calculate_rsi(prices, window=14):
    if len(prices) < window:  # Ensure we have at least `window` data points
        return None
    df = pd.DataFrame(prices, columns=['price'])
    # Calculate the RSI
    df['rsi'] = ta.momentum.RSIIndicator(df['price'], window=window).rsi()
    return df['rsi'].iloc[-1]

# Function to calculate MACD
def calculate_macd(prices):
    if len(prices) < 35:  # Ensure we have enough data for MACD calculation
        return None, None
    df = pd.DataFrame(prices, columns=['price'])
    macd = ta.trend.MACD(df['price'], window_slow=26, window_fast=12, window_sign=9)
    macd_line = macd.macd()
    signal_line = macd.macd_signal()
    return macd_line.iloc[-1], signal_line.iloc[-1]

# Function to produce a long beep sound
def long_beep():
    os.system(f'afplay {LONG_BEEP_FILE}')  # Play the long beep sound file

# Function to produce an alarming beep sound
def alarming_beep():
    os.system(f'afplay {SHORT_BEEP_FILE}')  # Play the short beep sound file

# Function to determine LONG or SHORT based on RSI and MACD
def determine_position(rsi, macd, signal):
    if rsi is None or macd is None or signal is None:
        return 'NO DATA'
    if rsi < 30 and macd > signal:
        long_beep()  # Trigger a long beep sound
        return '\033[1;32mLONG\033[0m <---'  # RSI < 30 and MACD > Signal indicates a buying opportunity
    elif rsi > 70 and macd < signal:
        alarming_beep()  # Trigger an alarming beep sound
        return '\033[1;31mSHORT\033[0m <---'  # RSI > 70 and MACD < Signal indicates a selling opportunity
    else:
        return 'HOLD'  # No strong buy/sell signals

# Main loop to monitor cryptocurrencies
while True:
    for product_id in cryptos:
        prices = fetch_candlestick_data(product_id, granularity=60)  # Fetch 1-minute candles
        
        if prices:
            # Calculate RSI and MACD
            rsi = calculate_rsi(prices)
            macd, signal = calculate_macd(prices)
            
            # Determine position based on RSI and MACD
            position = determine_position(rsi, macd, signal)
            
            # Display meaningful info for LONG or SHORT positions
            if 'LONG' in position or 'SHORT' in position:
                print(f'{product_id}: {position} Latest Price={prices[-1]}, RSI={rsi}, MACD={macd}, Signal={signal}')
            else:
                print(f'{product_id}: Position={position}, Latest Price={prices[-1]}, RSI={rsi}, MACD={macd}, Signal={signal}')
        else:
            # Fallback to real-time spot price if candlestick data fails
            spot_price = fetch_spot_price(product_id)
            if spot_price:
                print(f'{product_id}: Unable to fetch candlestick data. Using Spot Price={spot_price}')
            else:
                print(f'{product_id}: Unable to fetch prices. RSI=None, MACD=None, Position=NO DATA')
    
    print('************************************')
    time.sleep(60)  # Wait for 1 minute before fetching new data
