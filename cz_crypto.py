import requests
import pandas as pd
import numpy as np
import ta
import time
import os
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class CryptoAnalyzer:
    def __init__(self, symbols: List[str], timeframes: List[str] = ['1m', '5m', '15m']):
        # Coinbase API uses CRYPTO-USD format
        self.symbols = symbols  
        self.timeframes = timeframes  # Not used with Coinbase API, keeping for consistency
        self.base_url = "https://api.coinbase.com/v2"
        self.price_history = {
            symbol: {tf: deque(maxlen=500) for tf in timeframes}
            for symbol in self.symbols
        }
        self.signals_history = {symbol: [] for symbol in self.symbols}
        self.last_signal_time = {symbol: datetime.min for symbol in self.symbols}

    def fetch_data(self, symbol: str) -> Optional[float]:
        """Fetch spot price data from Coinbase API"""
        try:
            url = f'{self.base_url}/prices/{symbol}/spot'
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                print(f"Error {response.status_code} for {symbol}: {response.text}")
                return None

            data = response.json()
            if 'data' in data and 'amount' in data['data']:
                return float(data['data']['amount'])
            else:
                print(f"Data format issue for {symbol}: {data}")
                return None

        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None

    def calculate_advanced_indicators(self, prices: List[float]) -> Dict[str, float]:
        """Calculate indicators based on price history"""
        try:
            df = pd.DataFrame(prices, columns=['close'])
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            macd = ta.trend.MACD(df['close'])
            df['macd_line'] = macd.macd()
            df['signal_line'] = macd.macd_signal()
            return {
                'rsi': df['rsi'].iloc[-1],
                'macd_line': df['macd_line'].iloc[-1],
                'signal_line': df['signal_line'].iloc[-1]
            }
        except Exception as e:
            print(f"Error calculating indicators: {e}")
            return {}

    def generate_signal(self, indicators: Dict[str, float]) -> Optional[str]:
        """Generate trading signals based on indicators"""
        try:
            if indicators['rsi'] > 70 and indicators['macd_line'] < indicators['signal_line']:
                return "SHORT"
            elif indicators['rsi'] < 30 and indicators['macd_line'] > indicators['signal_line']:
                return "LONG"
            else:
                return None
        except Exception as e:
            print(f"Error generating signal: {e}")
            return None

    def log_signal(self, symbol: str, signal: str, price: float, indicators: Dict[str, float]):
        """Log trading signals with text color and sound alerts"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        indicators_cleaned = {k: float(v) if isinstance(v, np.float64) else v for k, v in indicators.items()}

        if signal == "LONG":
            colored_signal = "\033[1;32mLONG\033[0m"  # Green text for LONG
            self.play_sound('LONG')
        elif signal == "SHORT":
            colored_signal = "\033[1;31mSHORT\033[0m"  # Red text for SHORT
            self.play_sound('SHORT')
        else:
            colored_signal = signal

        print(f"[{timestamp}] {colored_signal} {symbol} @ {price:.2f}")
        print(f"Indicators: {indicators_cleaned}")

    def play_sound(self, signal_type: str):
        """Play a sound alert for LONG or SHORT signals"""
        sound_file = {
            'LONG': '/System/Library/Sounds/Glass.aiff',
            'SHORT': '/System/Library/Sounds/Funk.aiff',
        }
        if os.name == 'posix' and signal_type in sound_file:
            os.system(f'afplay {sound_file[signal_type]}')
        elif os.name == 'nt':
            frequency = 1000 if signal_type == 'LONG' else 750
            duration = 500
            os.system(f'echo \a')
        else:
            print(f"Sound alert not supported for signal type: {signal_type}")

def main():
    # Ensure symbols match Coinbase's format
    symbols = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'AVAX-USD', 'INJ-USD', 'LINK-USD', 'AR-USD', 'TIA-USD', 'SUI-USD', 'RNDR-USD']
    timeframes = ['1m', '5m', '15m']  # Not used with Coinbase API, keeping for consistency

    analyzer = CryptoAnalyzer(symbols, timeframes)
    print("Starting crypto analysis...")

    while True:
        for symbol in analyzer.symbols:
            price = analyzer.fetch_data(symbol)
            if price is not None:
                analyzer.price_history[symbol]['1m'].append(price)  # Use '1m' as a placeholder
                if len(analyzer.price_history[symbol]['1m']) >= 14:  # Need 14 points for RSI
                    indicators = analyzer.calculate_advanced_indicators(list(analyzer.price_history[symbol]['1m']))
                    signal = analyzer.generate_signal(indicators)
                    if signal:
                        analyzer.log_signal(symbol, signal, price, indicators)
        time.sleep(5)  # Wait between full cycles

if __name__ == "__main__":
    main()