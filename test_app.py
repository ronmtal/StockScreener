#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify the core functionality of the stock screener.

This script tests all major components of the stock screener application
to ensure they work correctly before deployment.

Author: Stock Screener Team
Version: 1.0.0
License: MIT
"""

import sys
from typing import List, Tuple

# Add local packages to path
sys.path.append('/home/ubuntu/.local/lib/python3.13/site-packages')


def test_imports() -> bool:
    """
    Test if all required modules can be imported.

    Returns:
        True if all imports successful, False otherwise
    """
    try:
        import streamlit  # noqa: F401
        print("✓ Streamlit imported successfully")

        import pandas  # noqa: F401
        print("✓ Pandas imported successfully")

        import yfinance  # noqa: F401
        print("✓ yfinance imported successfully")

        import plotly.graph_objects  # noqa: F401
        print("✓ Plotly imported successfully")

        import numpy  # noqa: F401
        print("✓ NumPy imported successfully")

        from st_aggrid import AgGrid  # noqa: F401
        print("✓ st_aggrid imported successfully")

        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_yfinance() -> bool:
    """
    Test yfinance functionality.

    Returns:
        True if yfinance works correctly, False otherwise
    """
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


def test_indicators() -> bool:
    """
    Test the indicator classes.

    Returns:
        True if all indicators work correctly, False otherwise
    """
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
            return False

        # Test RSI
        rsi = RSI(length=14)
        df_rsi = rsi.calculate(df.copy())
        if 'RSI_14' in df_rsi.columns:
            print("✓ RSI calculation works")
        else:
            print("✗ RSI calculation failed")
            return False

        # Test MACD
        macd = MACD()
        df_macd = macd.calculate(df.copy())
        if 'MACD_line' in df_macd.columns:
            print("✓ MACD calculation works")
        else:
            print("✗ MACD calculation failed")
            return False

        return True
    except Exception as e:
        print(f"✗ Indicator test failed: {e}")
        return False


def test_data_loading() -> bool:
    """
    Test the data loading functionality.

    Returns:
        True if data loading works correctly, False otherwise
    """
    try:
        sys.path.append('.')
        from stock_screener import load_index_symbols

        # Test loading Nasdaq 100 symbols (use the simplified version)
        df = load_index_symbols("Nasdaq 100")

        if (not df.empty and
                'Symbol' in df.columns and
                'Name' in df.columns):
            print(f"✓ Successfully loaded {len(df)} symbols")
            sample_symbols = ', '.join(df['Symbol'].head(3).tolist())
            print(f"  - Sample symbols: {sample_symbols}")
            return True
        else:
            print("✗ Failed to load index symbols")
            return False

    except Exception as e:
        print(f"✗ Data loading test failed: {e}")
        return False


def run_test_suite() -> Tuple[List[Tuple[str, bool]], int, int]:
    """
    Run all tests and return results.

    Returns:
        Tuple of (test_results, passed_count, total_count)
    """
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
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} crashed: {e}")
            results.append((test_name, False))

    passed = sum(1 for _, result in results if result)
    total = len(results)

    return results, passed, total


def print_test_summary(results: List[Tuple[str, bool]],
                       passed: int,
                       total: int) -> None:
    """
    Print test summary.

    Args:
        results: List of test results
        passed: Number of passed tests
        total: Total number of tests
    """
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print("=" * 50)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The stock screener should work correctly.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")


def main() -> bool:
    """
    Run all tests and return overall success status.

    Returns:
        True if all tests passed, False otherwise
    """
    print("🧪 Testing Stock Screener Components\n")

    results, passed, total = run_test_suite()
    print_test_summary(results, passed, total)

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
