import requests
import pandas as pd
import ta
import time
import os
from collections import deque
from datetime import datetime, timedelta

# List of cryptocurrency symbols to monitor
cryptos = ['SUI-USD', 'AVAX-USD', 'ETH-USD', 'BTC-USD', 'APT-USD', 'SOL-USD', 'AR-USD', 'INJ-USD', 'TIA-USD', 'LINK-USD', 'RNDR-USD']

# Paths to default system sounds
LONG_BEEP_FILE = '/System/Library/Sounds/Glass.aiff'
SHORT_BEEP_FILE = '/System/Library/Sounds/Funk.aiff'

class ColorPrinter:
    @staticmethod
    def print_info(message):
        print(f"\033[94m[INFO] {message}\033[0m")

    @staticmethod
    def print_warning(message):
        print(f"\033[93m[WARNING] {message}\033[0m")

    @staticmethod
    def print_long(message):
        print(f"\033[92m[LONG] {message}\033[0m")

    @staticmethod
    def print_short(message):
        print(f"\033[91m[SHORT] {message}\033[0m")

# Function to fetch real-time data from Coinbase with retry logic
def fetch_data(symbol, max_retries=3):
    url = f'https://api.coinbase.com/v2/prices/{symbol}/spot'
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if 'data' in data and 'amount' in data['data']:
                return float(data['data']['amount'])
            else:
                ColorPrinter.print_warning(f"Data format issue for {symbol}: {data}")
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                ColorPrinter.print_warning(f"Failed to fetch data for {symbol} after {max_retries} attempts: {e}")
                return None
            time.sleep(2 ** attempt)  # Exponential backoff
    return None

# Function to calculate indicators with robustness checks
def calculate_indicators(prices):
    if len(prices) < 26:  # Ensure we have enough data for MACD
        return None, None, None, None, None, None, None
    
    df = pd.DataFrame(prices, columns=['price'])
    
    # RSI
    df['rsi'] = ta.momentum.RSIIndicator(df['price'], window=14).rsi()
    rsi = df['rsi'].rolling(window=3).mean().iloc[-1]  # Smoothed RSI

    # MACD
    macd = ta.trend.MACD(df['price'])
    macd_line = macd.macd().rolling(window=3).mean().iloc[-1]
    macd_signal = macd.macd_signal().rolling(window=3).mean().iloc[-1]

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(df['price'], window=20, window_dev=2)
    bb_high = bb.bollinger_hband().iloc[-1]
    bb_low = bb.bollinger_lband().iloc[-1]

    # Stochastic Oscillator
    stoch = ta.momentum.StochasticOscillator(df['price'], df['price'], df['price'], window=14, smooth_window=3)
    stoch_line = stoch.stoch().rolling(window=3).mean().iloc[-1]
    stoch_signal = stoch.stoch_signal().rolling(window=3).mean().iloc[-1]

    return rsi, macd_line, macd_signal, bb_high, bb_low, stoch_line, stoch_signal

# Function to play sound
def play_sound(file_path):
    os.system(f"afplay {file_path}")

# Function to log trading signals
def log_signal(symbol, action, price, indicators):
    with open('trading_log.txt', 'a') as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {symbol} - {action} - Price: {price} - Indicators: {indicators}\n")

# Main function to monitor and trade cryptocurrencies
def main():
    price_history = {symbol: deque(maxlen=300) for symbol in cryptos}  # Larger buffer
    active_positions = {symbol: None for symbol in cryptos}
    last_update = {symbol: None for symbol in cryptos}

    while True:
        for symbol in cryptos:
            try:
                #ColorPrinter.print_info(f"Fetching data for {symbol}")
                price = fetch_data(symbol)
                if price is not None:
                    current_time = datetime.now()
                    last_update[symbol] = current_time
                    price_history[symbol].append(price)
                    ColorPrinter.print_info(f"Fetched price for {symbol}: {price}")

                    # Only calculate if we have enough data and data is recent
                    if len(price_history[symbol]) >= 26 and (current_time - last_update[symbol] < timedelta(minutes=10)):  # Ensure data isn't too old
                        rsi, macd, macd_signal, bb_high, bb_low, stoch, stoch_signal = calculate_indicators(list(price_history[symbol]))
                        
                        if None not in [rsi, macd, macd_signal, bb_high, bb_low, stoch, stoch_signal]:
                            indicators = {
                                'RSI': str(rsi),
                                'MACD': str(macd),
                                'MACD Signal': str(macd_signal),
                                'Bollinger High': str(bb_high),
                                'Bollinger Low': str(bb_low),
                                'Stochastic Line': str(stoch),
                                'Stochastic Signal': str(stoch_signal)
                            }
                            ColorPrinter.print_info(f"{symbol} Indicators: {indicators}")

                            # Convert the indicator values to float for proper comparison
                            rsi = float(indicators['RSI'])
                            macd = float(indicators['MACD'])
                            macd_signal = float(indicators['MACD Signal'])
                            bb_high = float(indicators['Bollinger High'])
                            bb_low = float(indicators['Bollinger Low'])
                            stoch_line = float(indicators['Stochastic Line'])
                            stoch_signal = float(indicators['Stochastic Signal'])

                            # Determine trading signals
                            if rsi < 40 and macd > macd_signal and price < bb_low and stoch_line < 20:
                                if active_positions[symbol] != 'LONG':
                                    ColorPrinter.print_long(f"LONG signal for {symbol} at price {price}")
                                    play_sound(LONG_BEEP_FILE)
                                    log_signal(symbol, 'LONG', price, indicators)
                                    active_positions[symbol] = 'LONG'
                            elif rsi > 60 and macd < macd_signal and price > bb_high and stoch_line > 80:
                                if active_positions[symbol] != 'SHORT':
                                    ColorPrinter.print_short(f"SHORT signal for {symbol} at price {price}")
                                    play_sound(SHORT_BEEP_FILE)
                                    log_signal(symbol, 'SHORT', price, indicators)
                                    active_positions[symbol] = 'SHORT'
                            else:
                                active_positions[symbol] = None
                        else:
                            ColorPrinter.print_warning(f"Could not calculate indicators for {symbol}")
            except Exception as e:
                ColorPrinter.print_warning(f"An error occurred for {symbol}: {e}")

        time.sleep(10)  # Check every 2 seconds

if __name__ == "__main__":
    main()
