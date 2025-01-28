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
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.base_url = "https://api.coinbase.com/v2"
        self.price_history = {symbol: {'1m': deque(maxlen=500)} for symbol in self.symbols}
        self.signals_history = {symbol: [] for symbol in self.symbols}
        self.last_signal_time = {symbol: datetime.min for symbol in self.symbols}
        
    def fetch_data(self, symbol: str) -> Optional[float]:
        """Fetch spot price data with validation and error handling"""
        try:
            url = f'{self.base_url}/prices/{symbol}/spot'
            response = requests.get(url, timeout=10)
            
            if response.status_code == 429:  # Rate limit handling
                time.sleep(30)  # Back off for 30 seconds
                return self.fetch_data(symbol)
                
            if response.status_code != 200:
                print(f"Error {response.status_code} for {symbol}: {response.text}")
                return None

            data = response.json()
            price = float(data['data']['amount'])
            
            if price <= 0:
                print(f"Invalid price {price} for {symbol}")
                return None
                
            return price

        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None

    def calculate_advanced_indicators(self, prices: List[float]) -> Dict[str, float]:
        """Calculate technical indicators with validation"""
        try:
            if len(prices) < 50:  # Ensure enough data points
                return {}
                
            df = pd.DataFrame(prices, columns=['close'])
            
            # Calculate high and low using close prices for ATR
            df['high'] = df['close'].rolling(2).max()
            df['low'] = df['close'].rolling(2).min()
            
            # Calculate technical indicators
            df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
            df['sma_50'] = ta.trend.sma_indicator(df['close'], window=50)
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            df['atr'] = ta.volatility.AverageTrueRange(
                df['high'], df['low'], df['close']
            ).average_true_range()
            
            macd = ta.trend.MACD(df['close'])
            df['macd_line'] = macd.macd()
            df['signal_line'] = macd.macd_signal()
            
            # Validate indicators
            latest = df.iloc[-1]
            if pd.isna(latest).any():
                print("Invalid indicator calculations")
                return {}
                
            return {
                'rsi': latest['rsi'],
                'macd_line': latest['macd_line'],
                'signal_line': latest['signal_line'],
                'sma_20': latest['sma_20'],
                'sma_50': latest['sma_50'],
                'atr': latest['atr']
            }
        except Exception as e:
            print(f"Error calculating indicators: {e}")
            return {}

    def generate_signal(self, indicators: Dict[str, float], price: float) -> Optional[str]:
        """Generate trading signals with multiple confirmation factors"""
        try:
            if not indicators or price <= 0:
                return None
                
            rsi = indicators['rsi']
            macd_line = indicators['macd_line']
            signal_line = indicators['signal_line']
            sma_20 = indicators['sma_20']
            sma_50 = indicators['sma_50']
            
            # LONG signal conditions
            long_conditions = [
                rsi < 30,  # Oversold
                macd_line > signal_line,  # Bullish MACD crossover
                price > sma_20,  # Price above short-term MA
                sma_20 > sma_50  # Golden cross formation
            ]
            
            # SHORT signal conditions
            short_conditions = [
                rsi > 70,  # Overbought
                macd_line < signal_line,  # Bearish MACD crossover
                price < sma_20,  # Price below short-term MA
                sma_20 < sma_50  # Death cross formation
            ]
            
            # Require multiple confirmations
            if all(long_conditions):
                return "LONG"
            elif all(short_conditions):
                return "SHORT"
                
            return None
                
        except Exception as e:
            print(f"Error generating signal: {e}")
            return None

    def manage_trade(self, symbol: str, signal: str, price: float, indicators: Dict[str, float]):
        """Implement trade management and risk controls"""
        try:
            # Prevent excessive trading
            current_time = datetime.now()
            min_time_between_trades = timedelta(minutes=15)
            
            if (current_time - self.last_signal_time[symbol]) < min_time_between_trades:
                return
                
            # Calculate position size based on ATR
            atr = indicators.get('atr', 0)
            if atr == 0:
                return
                
            # Set stop loss and take profit levels
            stop_loss = price - (2 * atr) if signal == "LONG" else price + (2 * atr)
            take_profit = price + (3 * atr) if signal == "LONG" else price - (3 * atr)
            
            # Calculate risk percentage
            risk_per_trade = 1.0  # 1% risk per trade
            position_size = self.calculate_position_size(price, stop_loss, risk_per_trade)
            
            self.log_trade_details(symbol, signal, price, indicators, stop_loss, take_profit, position_size)
            self.last_signal_time[symbol] = current_time
            
        except Exception as e:
            print(f"Error in trade management: {e}")

    def calculate_position_size(self, price: float, stop_loss: float, risk_percentage: float) -> float:
        """Calculate position size based on risk management"""
        account_size = 10000  # Example account size - adjust as needed
        risk_amount = account_size * (risk_percentage / 100)
        price_difference = abs(price - stop_loss)
        
        if price_difference == 0:
            return 0
            
        return risk_amount / price_difference

    def log_trade_details(self, symbol: str, signal: str, price: float, 
                         indicators: Dict[str, float], stop_loss: float, 
                         take_profit: float, position_size: float):
        """Log trading signals with detailed information"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Clean indicators for logging
        indicators_cleaned = {
            k: float(v) if isinstance(v, np.float64) else v 
            for k, v in indicators.items()
        }
        
        # Color coding for signals
        if signal == "LONG":
            colored_signal = "\033[1;32mLONG\033[0m"
            self.play_sound('LONG')
        else:
            colored_signal = "\033[1;31mSHORT\033[0m"
            self.play_sound('SHORT')
        
        # Print trade details
        print(f"\n{'='*50}")
        print(f"[{timestamp}] {colored_signal} {symbol}")
        print(f"Price: ${price:.2f}")
        print(f"Position Size: {position_size:.4f}")
        print(f"Stop Loss: ${stop_loss:.2f}")
        print(f"Take Profit: ${take_profit:.2f}")
        print(f"Risk/Reward: {abs((take_profit-price)/(stop_loss-price)):.2f}")
        print(f"Indicators: {indicators_cleaned}")
        print(f"{'='*50}\n")

    def play_sound(self, signal_type: str):
        """Play sound alerts for signals"""
        sound_file = {
            'LONG': '/System/Library/Sounds/Glass.aiff',
            'SHORT': '/System/Library/Sounds/Funk.aiff',
        }
        if os.name == 'posix' and signal_type in sound_file:
            os.system(f'afplay {sound_file[signal_type]}')
        elif os.name == 'nt':
            os.system('echo \a')

def main():
    # Initialize with major crypto pairs
    symbols = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'AVAX-USD']
    analyzer = CryptoAnalyzer(symbols)
    print("Starting crypto analysis...")
    
    while True:
        try:
            for symbol in analyzer.symbols:
                price = analyzer.fetch_data(symbol)
                if price is not None:
                    analyzer.price_history[symbol]['1m'].append(price)
                    
                    if len(analyzer.price_history[symbol]['1m']) >= 50:
                        indicators = analyzer.calculate_advanced_indicators(
                            list(analyzer.price_history[symbol]['1m'])
                        )
                        
                        if indicators:
                            signal = analyzer.generate_signal(indicators, price)
                            if signal:
                                analyzer.manage_trade(symbol, signal, price, indicators)
                                
            time.sleep(5)
            
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(30)  # Cool down on error

if __name__ == "__main__":
    main()
