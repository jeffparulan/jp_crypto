import requests
import pandas as pd
import ta
import time
import os

# List of cryptocurrency trading pairs to monitor (use Coinbase product IDs)
cryptos = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'AVAX-USD', 'APT-USD', 'LINK-USD', 'RNDR-USD']

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
        print(f"Error fetching data for {product_id}: {response.json()}")
        return None

# Function to calculate RSI
def calculate_rsi(prices):
    if len(prices) < 14:  # Ensure we have at least 14 data points
        return None
    df = pd.DataFrame(prices, columns=['price'])
    df['rsi'] = ta.momentum.RSIIndicator(df['price'], window=14).rsi()
    return df['rsi'].iloc[-1]

# Function to produce a long beep sound
def long_beep():
    os.system(f'afplay {LONG_BEEP_FILE}')  # Play the long beep sound file

# Function to produce an alarming beep sound
def alarming_beep():
    os.system(f'afplay {SHORT_BEEP_FILE}')  # Play the short beep sound file

# Function to determine LONG or SHORT
def determine_position(rsi):
    if rsi is None:
        return 'NO DATA'
    if rsi < 30:
        long_beep()  # Trigger a long beep sound
        return '\033[1;32mLONG\033[0m <---'  # RSI < 30 indicates oversold conditions
    elif rsi > 70:
        alarming_beep()  # Trigger an alarming beep sound
        return '\033[1;31mSHORT\033[0m <---'  # RSI > 70 indicates overbought conditions
    else:
        return 'HOLD'  # RSI between 30 and 70 indicates neutral conditions

# Main loop to monitor cryptocurrencies
while True:
    for product_id in cryptos:
        prices = fetch_candlestick_data(product_id, granularity=60)  # Fetch 1-minute candles
        if prices:
            rsi = calculate_rsi(prices)
            position = determine_position(rsi)
            if 'LONG' in position or 'SHORT' in position:
                print(f'---> {product_id}: {position} Latest Price={prices[-1]}, RSI={rsi}')
            else:
                print(f'{product_id}: Position={position}, Latest Price={prices[-1]}, RSI={rsi}')
        else:
            print(f'{product_id}: Unable to fetch prices. RSI=None, Position=NO DATA')
    print('************************************')
    time.sleep(10)  # Wait for 1 minute before fetching new data
