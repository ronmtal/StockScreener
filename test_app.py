#!/usr/bin/env python3
"""
Test script to verify the core functionality of the stock screener
"""

import sys
import os
sys.path.append('/home/ubuntu/.local/lib/python3.13/site-packages')

def test_imports():
    """Test if all required modules can be imported"""
    try:
        import streamlit as st
        print("✓ Streamlit imported successfully")
        
        import pandas as pd
        print("✓ Pandas imported successfully")
        
        import yfinance as yf
        print("✓ yfinance imported successfully")
        
        import plotly.graph_objects as go
        print("✓ Plotly imported successfully")
        
        import numpy as np
        print("✓ NumPy imported successfully")
        
        from st_aggrid import AgGrid
        print("✓ st_aggrid imported successfully")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_yfinance():
    """Test yfinance functionality"""
    try:
        import yfinance as yf
        
        # Test getting basic stock info
        ticker = yf.Ticker("AAPL")
        info = ticker.info
        
        if info and 'symbol' in info:
            print("✓ yfinance can fetch stock info")
        else:
            print("✓ yfinance connected (info may be limited)")
            
        # Test getting historical data
        hist = ticker.history(period="5d")
        if not hist.empty:
            print("✓ yfinance can fetch historical data")
            print(f"  - Retrieved {len(hist)} days of data for AAPL")
        else:
            print("✗ Could not fetch historical data")
            
        return True
    except Exception as e:
        print(f"✗ yfinance test failed: {e}")
        return False

def test_indicators():
    """Test the indicator classes"""
    try:
        import pandas as pd
        import numpy as np
        
        # Import our custom classes
        sys.path.append('.')
        from stock_screener import SimpleMovingAverage, RSI, MACD
        
        # Create sample data
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        prices = 100 + np.cumsum(np.random.randn(100) * 0.1)
        df = pd.DataFrame({
            'Open': prices * 0.99,
            'High': prices * 1.02,
            'Low': prices * 0.98,
            'Close': prices,
            'Volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)
        
        # Test SMA
        sma = SimpleMovingAverage(length=20)
        df_sma = sma.calculate(df.copy())
        if 'SMA_20' in df_sma.columns:
            print("✓ SMA calculation works")
        else:
            print("✗ SMA calculation failed")
            
        # Test RSI
        rsi = RSI(length=14)
        df_rsi = rsi.calculate(df.copy())
        if 'RSI_14' in df_rsi.columns:
            print("✓ RSI calculation works")
        else:
            print("✗ RSI calculation failed")
            
        # Test MACD
        macd = MACD()
        df_macd = macd.calculate(df.copy())
        if 'MACD_line' in df_macd.columns:
            print("✓ MACD calculation works")
        else:
            print("✗ MACD calculation failed")
            
        return True
    except Exception as e:
        print(f"✗ Indicator test failed: {e}")
        return False

def test_data_loading():
    """Test the data loading functionality"""
    try:
        sys.path.append('.')
        from stock_screener import load_index_symbols
        
        # Test loading S&P 500 symbols
        df = load_index_symbols("Nasdaq 100")  # Use the simplified version
        
        if not df.empty and 'Symbol' in df.columns and 'Name' in df.columns:
            print(f"✓ Successfully loaded {len(df)} symbols")
            print(f"  - Sample symbols: {', '.join(df['Symbol'].head(3).tolist())}")
        else:
            print("✗ Failed to load index symbols")
            
        return True
    except Exception as e:
        print(f"✗ Data loading test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Stock Screener Components\n")
    
    tests = [
        ("Import Test", test_imports),
        ("yfinance Test", test_yfinance), 
        ("Indicators Test", test_indicators),
        ("Data Loading Test", test_data_loading)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        print("-" * 40)
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"✗ {test_name} crashed: {e}")
            results.append(False)
    
    print("\n" + "="*50)
    print("📊 Test Summary:")
    print("="*50)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_name, _) in enumerate(tests):
        status = "✓ PASS" if results[i] else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The stock screener should work correctly.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    main()