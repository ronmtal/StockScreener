#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Stock Screener Application

A comprehensive stock screening application built with Streamlit that allows
analysis and filtering of stocks from major indices using technical indicators
and financial metrics.

Author: Stock Screener Team
Version: 1.0.0
License: MIT
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode


# ==============================================================================
# CONSTANTS AND CONFIGURATION
# ==============================================================================

FILTER_GROUPS_FILE = "filter_groups.json"
MAX_WORKERS = 10  # Reduced for better stability

# Simplified AVWAP configs (removed dependency on external library)
AVWAP_CONFIGS = [
    {
        "name": "aVWAP #1",
        "show": True,
        "source": "hlc3",
        "color": "#f6c309",
        "anchor_date": "2021-07-21"
    },
    {
        "name": "aVWAP #2",
        "show": True,
        "source": "hlc3",
        "color": "#fb9800",
        "anchor_date": "2021-08-05"
    },
    {
        "name": "aVWAP #3",
        "show": True,
        "source": "hlc3",
        "color": "#fb6500",
        "anchor_date": "2021-09-07"
    },
    {
        "name": "aVWAP #4",
        "show": True,
        "source": "hlc3",
        "color": "#f60c0c",
        "anchor_date": "2021-05-19"
    }
]


# ==============================================================================
# TECHNICAL INDICATOR CLASSES
# ==============================================================================

class SimpleMovingAverage:
    """Simple Moving Average (SMA) technical indicator."""

    def __init__(self, length: int = 20, source: str = 'Close') -> None:
        """
        Initialize Simple Moving Average indicator.

        Args:
            length: Period for SMA calculation
            source: Column name to calculate SMA from
        """
        self.length = length
        self.source = source
        self.sma_col_name = f'SMA_{self.length}'

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate SMA for the given DataFrame.

        Args:
            df: Input DataFrame with OHLC data

        Returns:
            DataFrame with SMA column added
        """
        df[self.sma_col_name] = df[self.source].rolling(
            window=self.length
        ).mean()
        return df

    def get_signals(self, df: pd.DataFrame) -> Dict[str, bool]:
        """
        Get SMA touch signals.

        Args:
            df: DataFrame with SMA data

        Returns:
            Dictionary with signal information
        """
        signals = {}
        if (not df.empty and
                self.sma_col_name in df.columns and
                len(df) > 1):

            for i in range(1, min(3, len(df))):
                prev_row = df.iloc[-i]
                sma_value = prev_row[self.sma_col_name]

                if (prev_row['Low'] <= sma_value <= prev_row['High']):
                    signals['sma_touch'] = True
                    break
            else:
                signals['sma_touch'] = False

        return signals


class RSI:
    """Relative Strength Index (RSI) technical indicator."""

    def __init__(self, length: int = 14, source: str = 'Close') -> None:
        """
        Initialize RSI indicator.

        Args:
            length: Period for RSI calculation
            source: Column name to calculate RSI from
        """
        self.length = length
        self.source = source
        self.rsi_col_name = f'RSI_{self.length}'

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate RSI for the given DataFrame.

        Args:
            df: Input DataFrame with price data

        Returns:
            DataFrame with RSI column added
        """
        delta = df[self.source].diff()
        gain = (delta.where(delta > 0, 0)).rolling(
            window=self.length
        ).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(
            window=self.length
        ).mean()

        rs = gain / loss
        df[self.rsi_col_name] = 100 - (100 / (1 + rs))
        return df

    def get_signals(self, df: pd.DataFrame) -> Dict[str, Union[float, bool]]:
        """
        Get RSI signals.

        Args:
            df: DataFrame with RSI data

        Returns:
            Dictionary with RSI signal information
        """
        signals = {}
        if not df.empty and self.rsi_col_name in df.columns:
            last_rsi = df[self.rsi_col_name].iloc[-1]
            signals['last_rsi'] = last_rsi
            signals['is_overbought'] = last_rsi > 70
            signals['is_oversold'] = last_rsi < 30

        return signals


class MACD:
    """Moving Average Convergence Divergence (MACD) technical indicator."""

    def __init__(self,
                 fast_length: int = 12,
                 slow_length: int = 26,
                 signal_length: int = 9,
                 source: str = 'Close') -> None:
        """
        Initialize MACD indicator.

        Args:
            fast_length: Fast EMA period
            slow_length: Slow EMA period
            signal_length: Signal line EMA period
            source: Column name to calculate MACD from
        """
        self.fast_length = fast_length
        self.slow_length = slow_length
        self.signal_length = signal_length
        self.source = source
        self.macd_line_col = 'MACD_line'
        self.signal_line_col = 'MACD_signal_line'
        self.histogram_col = 'MACD_histogram'

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate MACD for the given DataFrame.

        Args:
            df: Input DataFrame with price data

        Returns:
            DataFrame with MACD columns added
        """
        fast_ema = df[self.source].ewm(
            span=self.fast_length,
            adjust=False
        ).mean()
        slow_ema = df[self.source].ewm(
            span=self.slow_length,
            adjust=False
        ).mean()

        df[self.macd_line_col] = fast_ema - slow_ema
        df[self.signal_line_col] = df[self.macd_line_col].ewm(
            span=self.signal_length,
            adjust=False
        ).mean()
        df[self.histogram_col] = (df[self.macd_line_col] -
                                  df[self.signal_line_col])

        return df

    def get_signals(self, df: pd.DataFrame) -> Dict[str, Union[float, bool]]:
        """
        Get MACD signals.

        Args:
            df: DataFrame with MACD data

        Returns:
            Dictionary with MACD signal information
        """
        signals = {}
        if (not df.empty and
                self.histogram_col in df.columns and
                len(df) > 1):

            last_hist = df[self.histogram_col].iloc[-1]
            prev_hist = df[self.histogram_col].iloc[-2]

            signals['bullish_cross'] = last_hist > 0 and prev_hist <= 0
            signals['bearish_cross'] = last_hist < 0 and prev_hist >= 0
            signals['last_macd_line'] = df[self.macd_line_col].iloc[-1]
            signals['last_signal_line'] = df[self.signal_line_col].iloc[-1]
            signals['last_histogram'] = last_hist

        return signals


# ==============================================================================
# DATA LOADING AND PROCESSING FUNCTIONS
# ==============================================================================

@st.cache_data(ttl=3600)
def load_index_symbols(index_type: str) -> pd.DataFrame:
    """
    Load stock symbols for different indices.

    Args:
        index_type: Type of index to load

    Returns:
        DataFrame with Symbol and Name columns
    """
    try:
        if index_type == "S&P 500":
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            tables = pd.read_html(url)
            df = tables[0][['Symbol', 'Security']].copy()
            df.rename(columns={'Security': 'Name'}, inplace=True)

        elif index_type == "Nasdaq 100":
            # Use a simpler approach for Nasdaq 100
            symbols = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META',
                'AVGO', 'COST', 'NFLX', 'ADBE', 'PEP', 'TMUS', 'CSCO',
                'CMCSA', 'TXN', 'QCOM', 'HON', 'AMGN', 'SBUX'
            ]
            names = [
                'Apple Inc.', 'Microsoft Corporation', 'Alphabet Inc.',
                'Amazon.com Inc.', 'NVIDIA Corporation', 'Tesla Inc.',
                'Meta Platforms Inc.', 'Broadcom Inc.',
                'Costco Wholesale Corporation', 'Netflix Inc.',
                'Adobe Inc.', 'PepsiCo Inc.', 'T-Mobile US Inc.',
                'Cisco Systems Inc.', 'Comcast Corporation',
                'Texas Instruments Incorporated', 'QUALCOMM Incorporated',
                'Honeywell International Inc.', 'Amgen Inc.',
                'Starbucks Corporation'
            ]
            df = pd.DataFrame({'Symbol': symbols, 'Name': names})

        elif index_type == "Dow Jones":
            # Simplified Dow Jones list
            symbols = [
                'AAPL', 'MSFT', 'UNH', 'GS', 'HD', 'CAT', 'MCD', 'AMGN',
                'V', 'BA', 'TRV', 'AXP', 'JPM', 'IBM', 'JNJ', 'WMT',
                'PG', 'CVX', 'MRK', 'DIS'
            ]
            names = [
                'Apple Inc.', 'Microsoft Corporation',
                'UnitedHealth Group Incorporated',
                'The Goldman Sachs Group Inc.', 'The Home Depot Inc.',
                'Caterpillar Inc.', "McDonald's Corporation",
                'Amgen Inc.', 'Visa Inc.', 'The Boeing Company',
                'The Travelers Companies Inc.', 'American Express Company',
                'JPMorgan Chase & Co.',
                'International Business Machines Corporation',
                'Johnson & Johnson', 'Walmart Inc.',
                'The Procter & Gamble Company', 'Chevron Corporation',
                'Merck & Co. Inc.', 'The Walt Disney Company'
            ]
            df = pd.DataFrame({'Symbol': symbols, 'Name': names})

        else:  # Russell 2000 - use a small sample
            symbols = ['IWM', 'VTWO', 'URTY', 'UWM', 'TWM']
            names = [
                'iShares Russell 2000 ETF', 'Vanguard Russell 2000 ETF',
                'ProShares UltraPro Russell2000',
                'ProShares Ultra Russell2000',
                'ProShares UltraShort Russell2000'
            ]
            df = pd.DataFrame({'Symbol': symbols, 'Name': names})

        # Clean symbols
        df['Symbol'] = df['Symbol'].str.replace('.', '-', regex=False)
        return df.dropna().reset_index(drop=True)

    except Exception as e:
        st.error(f"שגיאה בטעינת רשימת המניות: {e}")
        # Return a fallback list of popular stocks
        fallback_symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
            'META', 'NVDA', 'NFLX', 'ADBE', 'CRM'
        ]
        fallback_names = [
            'Apple', 'Microsoft', 'Alphabet', 'Amazon', 'Tesla',
            'Meta', 'NVIDIA', 'Netflix', 'Adobe', 'Salesforce'
        ]
        return pd.DataFrame({
            'Symbol': fallback_symbols,
            'Name': fallback_names
        })


# ==============================================================================
# CANDLESTICK PATTERN FUNCTIONS
# ==============================================================================

def is_doji(row: pd.Series, threshold: float) -> bool:
    """
    Check if candle is a doji pattern.

    Args:
        row: OHLC data row
        threshold: Threshold for doji detection

    Returns:
        True if doji pattern detected
    """
    body = abs(row['Open'] - row['Close'])
    range_total = row['High'] - row['Low']

    if range_total == 0:
        return False

    return body / range_total < threshold / 100


def is_hammer_or_hanging_man(row: pd.Series) -> bool:
    """
    Check if candle is hammer or hanging man pattern.

    Args:
        row: OHLC data row

    Returns:
        True if hammer or hanging man pattern detected
    """
    body = abs(row['Open'] - row['Close'])
    upper_shadow = row['High'] - max(row['Open'], row['Close'])
    lower_shadow = min(row['Open'], row['Close']) - row['Low']

    if body == 0:
        return lower_shadow > upper_shadow * 2

    return lower_shadow >= body * 2 and upper_shadow <= body


# ==============================================================================
# STOCK DATA FETCHING FUNCTIONS
# ==============================================================================

def fetch_stock_data(symbol: str,
                     sma_configs: List[Dict],
                     rsi_config: Dict,
                     macd_config: Dict) -> Dict:
    """
    Fetch and process stock data for a single symbol.

    Args:
        symbol: Stock symbol to fetch
        sma_configs: SMA configuration list
        rsi_config: RSI configuration dictionary
        macd_config: MACD configuration dictionary

    Returns:
        Dictionary with processed stock data
    """
    try:
        ticker = yf.Ticker(symbol)

        # Get basic info
        try:
            info = ticker.info
            if not info:
                return {
                    "symbol": symbol,
                    "error": f"לא נמצא מידע בסיסי עבור {symbol}."
                }
        except Exception:
            # If info fails, try to get basic data anyway
            info = {}

        # Get historical data
        try:
            # Reduced period for faster loading
            df_hist = ticker.history(period="2y")
            if df_hist.empty:
                return {
                    "symbol": symbol,
                    "error": f"לא נמצאו נתונים היסטוריים עבור {symbol}."
                }
        except Exception as e:
            return {
                "symbol": symbol,
                "error": f"שגיאה בקבלת נתונים היסטוריים: {e}"
            }

        # Calculate SMA indicators
        sma_values, sma_signals = {}, {}
        for sma_config in sma_configs:
            if sma_config['enabled']:
                try:
                    sma_indicator = SimpleMovingAverage(
                        length=sma_config['length']
                    )
                    df_with_sma = sma_indicator.calculate(df_hist.copy())

                    if (not df_with_sma.empty and
                            sma_indicator.sma_col_name in df_with_sma.columns):

                        last_sma = df_with_sma[
                            sma_indicator.sma_col_name
                        ].iloc[-1]

                        if pd.notna(last_sma):
                            sma_values[f"SMA_{sma_config['length']}"] = last_sma
                            signals = sma_indicator.get_signals(df_with_sma)
                            touch_key = f"sma_touch_{sma_config['length']}"
                            sma_signals[touch_key] = signals.get(
                                'sma_touch', False
                            )
                except Exception:
                    continue

        # Calculate RSI
        rsi_values, rsi_signals = {}, {}
        if rsi_config['enabled']:
            try:
                rsi_indicator = RSI(length=rsi_config['length'])
                df_with_rsi = rsi_indicator.calculate(df_hist.copy())

                if (not df_with_rsi.empty and
                        rsi_indicator.rsi_col_name in df_with_rsi.columns):

                    last_rsi = df_with_rsi[
                        rsi_indicator.rsi_col_name
                    ].iloc[-1]

                    if pd.notna(last_rsi):
                        rsi_values[f"RSI_{rsi_config['length']}"] = last_rsi
                        rsi_signals = rsi_indicator.get_signals(df_with_rsi)
            except Exception:
                pass

        # Calculate MACD
        macd_values, macd_signals = {}, {}
        if macd_config['enabled']:
            try:
                macd_indicator = MACD(
                    fast_length=macd_config['fast'],
                    slow_length=macd_config['slow'],
                    signal_length=macd_config['signal']
                )
                df_with_macd = macd_indicator.calculate(df_hist.copy())

                if not df_with_macd.empty:
                    macd_raw_signals = macd_indicator.get_signals(df_with_macd)
                    macd_signals.update(macd_raw_signals)
                    macd_values = {
                        k: v for k, v in macd_raw_signals.items()
                        if k.startswith('last_')
                    }
            except Exception:
                pass

        # Candlestick patterns
        is_doji_last = False
        is_hammer_last = False
        is_hanging_man_last = False

        if not df_hist.empty:
            try:
                last_candle = df_hist.iloc[-1]
                if is_doji(last_candle, 5.0):  # Use default threshold
                    is_doji_last = True

                if is_hammer_or_hanging_man(last_candle):
                    if (len(df_hist) >= 4 and
                            all(df_hist['Close'].iloc[-4:-1].diff().dropna() > 0)):
                        is_hanging_man_last = True
                    else:
                        is_hammer_last = True
            except Exception:
                pass

        # Get financial data (simplified)
        try:
            annual_financials = get_financial_statement_data(
                ticker.income_stmt, 'annual'
            )
            quarterly_financials = get_financial_statement_data(
                ticker.quarterly_income_stmt, 'quarterly'
            )

            revenues_list = [
                d['revenue'] for d in annual_financials
                if pd.notna(d['revenue'])
            ]
            net_income_list = [
                d['net_income'] for d in annual_financials
                if pd.notna(d['net_income'])
            ]

            is_both_growing = (
                is_consistently_increasing(revenues_list, 3) and
                is_consistently_increasing(net_income_list, 3)
            )
        except Exception:
            annual_financials = []
            quarterly_financials = []
            revenues_list = []
            net_income_list = []
            is_both_growing = False

        # Get current price
        try:
            price = (info.get("currentPrice") or
                     info.get("regularMarketPrice") or
                     df_hist['Close'].iloc[-1])
        except Exception:
            price = None

        return {
            "symbol": symbol,
            "price": price,
            "pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "market_cap": info.get("marketCap"),
            "pre_market_change_percent": info.get("preMarketChangePercent"),
            "volume": info.get("volume"),
            "average_volume": info.get("averageVolume"),
            "trailing_eps": info.get("trailingEps"),
            "forward_eps": info.get("forwardEps"),
            "annual_financial_data": annual_financials,
            "quarterly_financial_data": quarterly_financials,
            "is_both_growing": is_both_growing,
            "has_avwap_touch": False,  # Simplified - removed AVWAP dependency
            "avwap_series_data": {},
            "sma_values": sma_values,
            "sma_signals": sma_signals,
            "rsi_values": rsi_values,
            "rsi_signals": rsi_signals,
            "macd_values": macd_values,
            "macd_signals": macd_signals,
            "revenues_list_for_filter": revenues_list,
            "net_income_list_for_filter": net_income_list,
            "is_doji_last": is_doji_last,
            "is_hammer_last": is_hammer_last,
            "is_hanging_man_last": is_hanging_man_last
        }

    except Exception as e:
        return {"symbol": symbol, "error": f"שגיאה כללית: {e}"}


def get_financial_statement_data(statement_df: pd.DataFrame,
                                 period: str) -> List[Dict]:
    """
    Extract financial data from income statement.

    Args:
        statement_df: Financial statement DataFrame
        period: 'quarterly' or 'annual'

    Returns:
        List of financial data dictionaries
    """
    try:
        if statement_df is None or statement_df.empty:
            return []

        statement_df = statement_df.T.sort_index(ascending=True)
        financial_data = []

        # Get last few periods
        periods_to_take = 8 if period == 'quarterly' else 5

        for date_idx, row in statement_df.tail(periods_to_take).iterrows():
            try:
                revenue = row.get("Total Revenue", np.nan)
                net_income = row.get("Net Income", np.nan)
                ebitda = row.get("EBITDA", np.nan)

                # Convert to billions if not NaN
                revenue = revenue / 1e9 if pd.notna(revenue) else np.nan
                net_income = net_income / 1e9 if pd.notna(net_income) else np.nan
                ebitda = ebitda / 1e9 if pd.notna(ebitda) else np.nan

                date_str = (f"{date_idx.year}-Q{date_idx.quarter}"
                            if period == 'quarterly'
                            else date_idx.strftime('%Y'))

                financial_data.append({
                    "date": date_str,
                    "revenue": revenue,
                    "net_income": net_income,
                    "ebitda": ebitda,
                })
            except Exception:
                continue

        return financial_data
    except Exception:
        return []


def is_consistently_increasing(data: List[float], years: int = 3) -> bool:
    """
    Check if data is consistently increasing over specified years.

    Args:
        data: List of numeric values
        years: Number of years to check

    Returns:
        True if consistently increasing
    """
    try:
        valid_data = [x for x in data if pd.notna(x) and x is not None]
        if len(valid_data) < years:
            return False

        sub_list = valid_data[-years:]
        return all(sub_list[i] >= sub_list[i - 1]
                   for i in range(1, len(sub_list)))
    except Exception:
        return False


def is_consistently_decreasing(data: List[float], years: int = 3) -> bool:
    """
    Check if data is consistently decreasing over specified years.

    Args:
        data: List of numeric values
        years: Number of years to check

    Returns:
        True if consistently decreasing
    """
    try:
        valid_data = [x for x in data if pd.notna(x) and x is not None]
        if len(valid_data) < years:
            return False

        sub_list = valid_data[-years:]
        return all(sub_list[i] <= sub_list[i - 1]
                   for i in range(1, len(sub_list)))
    except Exception:
        return False


def run_data_fetch_and_process(symbols_df: pd.DataFrame) -> pd.DataFrame:
    """
    Main function to fetch and process data for all symbols.

    Args:
        symbols_df: DataFrame with stock symbols

    Returns:
        DataFrame with processed stock data
    """
    # Limit to first 20 for demo
    symbols_to_process = symbols_df['Symbol'].tolist()[:20]
    total_symbols = len(symbols_to_process)

    if total_symbols == 0:
        return pd.DataFrame()

    st.info(f"מעבד {total_symbols} מניות...")

    status_placeholder = st.empty()
    progress_bar = st.progress(0)
    results, errors = [], []
    symbol_name_map = symbols_df.set_index('Symbol')['Name'].to_dict()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_symbol = {
            executor.submit(
                fetch_stock_data,
                s,
                st.session_state.sma_configs,
                st.session_state.rsi_config,
                st.session_state.macd_config
            ): s
            for s in symbols_to_process
        }

        for i, future in enumerate(as_completed(future_to_symbol), 1):
            symbol = future_to_symbol[future]
            symbol_name = symbol_name_map.get(symbol, symbol)
            status_placeholder.text(
                f"🔍 סורק {i}/{total_symbols}: {symbol_name}"
            )
            progress_bar.progress(i / total_symbols)

            try:
                data = future.result(timeout=30)  # Add timeout
                if "error" in data:
                    errors.append(f"{symbol}: {data['error']}")
                else:
                    results.append(data)
            except Exception as e:
                errors.append(f"חריגה: {symbol}: {e}")

    status_placeholder.empty()
    progress_bar.empty()

    if errors:
        with st.expander(f"נתקבלו {len(errors)} שגיאות."):
            st.warning("\n".join(errors[:10]))  # Show first 10 errors

    if not results:
        st.error("לא נמצאו נתונים תקינים")
        return pd.DataFrame()

    # Process results into DataFrame
    df = pd.DataFrame(results)
    df['Name'] = df['symbol'].map(symbol_name_map).fillna(df['symbol'])

    # Expand nested dictionaries
    for prefix in ['sma', 'rsi', 'macd']:
        values_col = f'{prefix}_values'
        signals_col = f'{prefix}_signals'

        if values_col in df.columns:
            try:
                values_df = df[values_col].apply(pd.Series)
                df = pd.concat([df.drop(columns=[values_col]), values_df],
                               axis=1)
            except Exception:
                pass

        if signals_col in df.columns:
            try:
                signals_df = df[signals_col].apply(pd.Series)
                df = pd.concat([df.drop(columns=[signals_col]), signals_df],
                               axis=1)
            except Exception:
                pass

    # Create final DataFrame with clean columns
    final_data = {
        "Symbol": df["symbol"],
        "Name": df["Name"],
        "Price": df["price"],
        "P/E": df["pe"],
        "Forward P/E": df["forward_pe"],
        "Market Cap (B)": df["market_cap"].apply(
            lambda x: x / 1e9 if pd.notna(x) and x else None
        ),
        "Volume": df["volume"],
        "Average Volume": df["average_volume"],
        "Has AVWAP Touch": df["has_avwap_touch"],
        "Is Both Consistently Growing": df["is_both_growing"],
        "Is Doji Last": df["is_doji_last"],
        "Is Hammer Last": df["is_hammer_last"],
        "Is Hanging Man Last": df["is_hanging_man_last"],
        # Hidden columns for details
        "annual_financial_data": df["annual_financial_data"],
        "quarterly_financial_data": df["quarterly_financial_data"],
        "avwap_series_data": df["avwap_series_data"],
        "revenues_list_for_filter": df["revenues_list_for_filter"],
        "net_income_list_for_filter": df["net_income_list_for_filter"],
    }

    # Add RSI column if enabled
    if st.session_state.rsi_config['enabled']:
        rsi_col = f"RSI_{st.session_state.rsi_config['length']}"
        final_data[rsi_col] = df.get(rsi_col)

    # Add MACD columns if enabled
    if st.session_state.macd_config['enabled']:
        final_data["Bullish MACD Cross"] = df.get("bullish_cross")
        final_data["Bearish MACD Cross"] = df.get("bearish_cross")

    # Add SMA columns
    for sma_config in st.session_state.sma_configs:
        if sma_config['enabled']:
            length = sma_config['length']
            final_data[f'SMA_{length}'] = df.get(f'SMA_{length}')
            final_data[f'sma_touch_{length}'] = df.get(f'sma_touch_{length}')

    result_df = pd.DataFrame(final_data)

    # Clean numeric columns
    numeric_cols = [
        'Price', 'P/E', 'Forward P/E', 'Market Cap (B)',
        'Volume', 'Average Volume'
    ]
    for col in numeric_cols:
        if col in result_df.columns:
            result_df[col] = pd.to_numeric(result_df[col], errors='coerce')

    return result_df.round(2)


# ==============================================================================
# CHART AND VISUALIZATION FUNCTIONS
# ==============================================================================

def calculate_heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Heikin Ashi candles from standard OHLC DataFrame.

    Args:
        df: Standard OHLC DataFrame

    Returns:
        DataFrame with Heikin Ashi values
    """
    try:
        ha_df = pd.DataFrame(index=df.index)
        ha_df['HA_Close'] = (df['Open'] + df['High'] +
                             df['Low'] + df['Close']) / 4
        ha_df['HA_Open'] = 0.0

        for i in range(len(df)):
            if i == 0:
                ha_df.loc[ha_df.index[i], 'HA_Open'] = (
                    (df['Open'].iloc[i] + df['Close'].iloc[i]) / 2
                )
            else:
                ha_df.loc[ha_df.index[i], 'HA_Open'] = (
                    (ha_df['HA_Open'].iloc[i - 1] +
                     ha_df['HA_Close'].iloc[i - 1]) / 2
                )

        ha_df['HA_High'] = df[['High']].join(
            ha_df[['HA_Open', 'HA_Close']]
        ).max(axis=1)
        ha_df['HA_Low'] = df[['Low']].join(
            ha_df[['HA_Open', 'HA_Close']]
        ).min(axis=1)

        return ha_df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=900)
def get_chart_data(symbol: str) -> Optional[pd.DataFrame]:
    """
    Get chart data for a specific symbol.

    Args:
        symbol: Stock symbol

    Returns:
        DataFrame with chart data or None if failed
    """
    try:
        df_hist = yf.Ticker(symbol).history(period="1y")  # Reduced period
        if df_hist.empty:
            return None

        # Add SMA indicators
        for length in st.session_state.chart_sma_lengths:
            df_hist[f'SMA_{length}'] = df_hist['Close'].rolling(
                window=length
            ).mean()

        # Add RSI if enabled
        if st.session_state.rsi_config['enabled']:
            try:
                df_hist = RSI(
                    length=st.session_state.rsi_config['length']
                ).calculate(df_hist)
            except Exception:
                pass

        # Add MACD if enabled
        if st.session_state.macd_config['enabled']:
            try:
                cfg = st.session_state.macd_config
                df_hist = MACD(
                    fast_length=cfg['fast'],
                    slow_length=cfg['slow'],
                    signal_length=cfg['signal']
                ).calculate(df_hist)
            except Exception:
                pass

        # Add candlestick patterns
        try:
            df_hist['is_doji'] = df_hist.apply(
                lambda row: is_doji(row, st.session_state.doji_threshold),
                axis=1
            )
            df_hist['is_hammer_or_hanging_man'] = df_hist.apply(
                is_hammer_or_hanging_man, axis=1
            )
        except Exception:
            pass

        return df_hist
    except Exception:
        return None


# ==============================================================================
# FILTER MANAGEMENT FUNCTIONS
# ==============================================================================

def load_filter_groups() -> Dict[str, List]:
    """
    Load filter groups from file.

    Returns:
        Dictionary of filter groups
    """
    if os.path.exists(FILTER_GROUPS_FILE):
        try:
            with open(FILTER_GROUPS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            st.error("שגיאה בקריאת קובץ הסינונים. משתמש בברירת מחדל.")
    return {"קבוצת סינון 1": []}


def save_filter_groups() -> None:
    """Save filter groups to file."""
    try:
        with open(FILTER_GROUPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.filter_groups, f,
                      indent=4, ensure_ascii=False)
    except IOError as e:
        st.error(f"שגיאה בשמירת קובץ הסינונים: {e}")


def apply_filters_to_df(df: pd.DataFrame,
                        filter_conditions: List[Dict]) -> pd.DataFrame:
    """
    Apply filter conditions to DataFrame.

    Args:
        df: Input DataFrame
        filter_conditions: List of filter condition dictionaries

    Returns:
        Filtered DataFrame
    """
    if df.empty or not filter_conditions:
        return df

    filtered_df = df.copy()

    for condition in filter_conditions:
        if filtered_df.empty:
            break

        try:
            col_name = condition.get("column")
            if not col_name:
                continue

            if "עקביות" in col_name:
                data_col = ("revenues_list_for_filter"
                            if "הכנסות" in col_name
                            else "net_income_list_for_filter")
                func = (is_consistently_decreasing
                        if "(יורדת)" in col_name
                        else is_consistently_increasing)
                filtered_df = filtered_df[
                    filtered_df[data_col].apply(
                        lambda x: func(x, condition.get("years_value", 3))
                    )
                ]

            elif "נגיעה בממוצע נע" in col_name:
                sma_length = condition.get("sma_length")
                if sma_length:
                    touch_col = f'sma_touch_{sma_length}'
                    if touch_col in filtered_df.columns:
                        filtered_df = filtered_df[
                            filtered_df[touch_col]
                        ]

            elif col_name == "חציית MACD שורית":
                if "Bullish MACD Cross" in filtered_df.columns:
                    filtered_df = filtered_df[
                        filtered_df["Bullish MACD Cross"]
                    ]

            elif col_name == "חציית MACD דובית":
                if "Bearish MACD Cross" in filtered_df.columns:
                    filtered_df = filtered_df[
                        filtered_df["Bearish MACD Cross"]
                    ]

            elif col_name == "הכנסות ורווחים עקביים":
                filtered_df = filtered_df[
                    filtered_df["Is Both Consistently Growing"]
                ]

            elif col_name == "נגיעת Auto Anchor VWAP":
                filtered_df = filtered_df[filtered_df["Has AVWAP Touch"]]

            elif col_name == "תבנית נר":
                pattern = condition.get("pattern_value")
                if pattern == "Doji":
                    filtered_df = filtered_df[
                        filtered_df["Is Doji Last"]
                    ]
                elif pattern == "Hammer":
                    filtered_df = filtered_df[
                        filtered_df["Is Hammer Last"]
                    ]
                elif pattern == "Hanging Man":
                    filtered_df = filtered_df[
                        filtered_df["Is Hanging Man Last"]
                    ]

            else:
                # Numeric filters
                col_map = {
                    "מחיר ($)": "Price",
                    "P/E": "P/E",
                    "מכפיל רווח עתידי": "Forward P/E",
                    "שווי שוק (B$)": "Market Cap (B)"
                }

                # Add RSI to map if enabled
                if st.session_state.rsi_config['enabled']:
                    rsi_len = st.session_state.rsi_config['length']
                    col_map[f"RSI ({rsi_len})"] = f"RSI_{rsi_len}"

                # Add SMAs to map
                for sma_config in st.session_state.sma_configs:
                    if sma_config['enabled']:
                        sma_len = sma_config['length']
                        col_map[f"SMA {sma_len}"] = f"SMA_{sma_len}"

                df_col = col_map.get(col_name)
                if df_col and df_col in filtered_df.columns:
                    try:
                        value = float(condition['value'])
                        operator = condition['operator']

                        if operator == '>':
                            filtered_df = filtered_df[filtered_df[df_col] > value]
                        elif operator == '<':
                            filtered_df = filtered_df[filtered_df[df_col] < value]
                        elif operator == '=':
                            filtered_df = filtered_df[filtered_df[df_col] == value]
                        elif operator == '>=':
                            filtered_df = filtered_df[filtered_df[df_col] >= value]
                        elif operator == '<=':
                            filtered_df = filtered_df[filtered_df[df_col] <= value]

                        # Remove NaN values
                        filtered_df = filtered_df.dropna(subset=[df_col])
                    except Exception:
                        continue

        except Exception as e:
            st.warning(f"לא ניתן ליישם תנאי '{condition.get('column')}': {e}")
            continue

    return filtered_df


# ==============================================================================
# USER INTERFACE FUNCTIONS
# ==============================================================================

def initialize_session_state() -> None:
    """Initialize Streamlit session state with default values."""
    defaults = {
        "full_df": None,
        "filtered_df": None,
        "previous_filtered_df": None,
        "selected_symbols": [],
        "view_mode": "table",
        "chart_page_number": 0,
        "filter_groups": load_filter_groups(),
        "add_group_mode": False,
        "rename_group_mode": False,
        "chart_type": "גרף נרות",
        "financial_period": "רבעוני",
        "sma_configs": [
            {'length': 20, 'enabled': True},
            {'length': 50, 'enabled': True},
            {'length': 150, 'enabled': False},
            {'length': 200, 'enabled': False}
        ],
        "chart_sma_lengths": [20, 50],
        "rsi_config": {'length': 14, 'enabled': True},
        "macd_config": {'fast': 12, 'slow': 26, 'signal': 9, 'enabled': True},
        "doji_threshold": 5.0
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Ensure current filter group exists
    if ("current_filter_group" not in st.session_state or
            st.session_state.current_filter_group not in
            st.session_state.filter_groups):
        st.session_state.current_filter_group = list(
            st.session_state.filter_groups.keys()
        )[0]


def setup_sidebar() -> str:
    """
    Setup sidebar with controls and settings.

    Returns:
        Selected index type
    """
    st.sidebar.header("הגדרות סריקה")
    selected_index = st.sidebar.selectbox(
        "בחר מדד",
        ["S&P 500", "Nasdaq 100", "Dow Jones", "Russell 2000"],
        key="sb_index_selection"
    )

    st.sidebar.title("סינון")
    with st.sidebar.expander("ניהול קבוצות סינון", expanded=False):
        setup_filter_group_management()
    with st.sidebar.expander("הגדרת תנאים", expanded=False):
        setup_filter_conditions()

    st.sidebar.title("הגדרות")
    with st.sidebar.expander("אינדיקטורים לחישוב", expanded=False):
        setup_indicators()

    with st.sidebar.expander("הגדרות זיהוי תבניות נרות", expanded=False):
        st.session_state.doji_threshold = st.slider(
            "סף זיהוי Doji (%)",
            0.1, 10.0,
            st.session_state.doji_threshold,
            0.1,
            help="גוף נר קטן מאחוז זה ביחס לטווח הכולל."
        )

    with st.sidebar.expander("הגדרות תצוגה", expanded=False):
        setup_display_settings()

    return selected_index


def setup_indicators() -> None:
    """Setup indicator configuration in sidebar."""
    st.subheader("ממוצעים נעים (SMA)")
    for i, sma_config in enumerate(st.session_state.sma_configs):
        col1, col2 = st.columns([1, 2])
        sma_config['enabled'] = col1.checkbox(
            f"SMA #{i + 1}",
            value=sma_config['enabled'],
            key=f"main_sma_{i}_enabled"
        )
        sma_config['length'] = col2.number_input(
            "אורך",
            1, 500,
            sma_config['length'],
            key=f"main_sma_{i}_length",
            disabled=not sma_config['enabled']
        )

    st.subheader("RSI")
    c1, c2 = st.columns([1, 2])
    st.session_state.rsi_config['enabled'] = c1.checkbox(
        "RSI",
        value=st.session_state.rsi_config['enabled'],
        key="main_rsi_enabled"
    )
    st.session_state.rsi_config['length'] = c2.number_input(
        "אורך",
        1, 100,
        st.session_state.rsi_config['length'],
        key="main_rsi_length",
        disabled=not st.session_state.rsi_config['enabled']
    )

    st.subheader("MACD")
    st.session_state.macd_config['enabled'] = st.checkbox(
        "MACD",
        value=st.session_state.macd_config['enabled'],
        key="main_macd_enabled"
    )
    c1, c2, c3 = st.columns(3)
    st.session_state.macd_config['fast'] = c1.number_input(
        "מהיר",
        1, 100,
        st.session_state.macd_config['fast'],
        key="main_macd_fast",
        disabled=not st.session_state.macd_config['enabled']
    )
    st.session_state.macd_config['slow'] = c2.number_input(
        "איטי",
        1, 100,
        st.session_state.macd_config['slow'],
        key="main_macd_slow",
        disabled=not st.session_state.macd_config['enabled']
    )
    st.session_state.macd_config['signal'] = c3.number_input(
        "סיגנל",
        1, 100,
        st.session_state.macd_config['signal'],
        key="main_macd_signal",
        disabled=not st.session_state.macd_config['enabled']
    )


def setup_display_settings() -> None:
    """Setup display settings in sidebar."""
    st.session_state.chart_type = st.radio(
        "סוג גרף מחיר:",
        ("גרף נרות", "גרף קו", "Heikin Ashi"),
        key="chart_type_radio"
    )
    st.session_state.financial_period = st.radio(
        "תקופת דוחות:",
        ("רבעוני", "שנתי"),
        key="financial_period_radio"
    )

    available_sma_lengths = [
        cfg['length'] for cfg in st.session_state.sma_configs
        if cfg['enabled']
    ]
    st.session_state.chart_sma_lengths = st.multiselect(
        "הצג ממוצעים נעים בגרף:",
        options=available_sma_lengths,
        default=[
            length for length in st.session_state.chart_sma_lengths
            if length in available_sma_lengths
        ],
        key="chart_sma_multiselect"
    )


def setup_filter_group_management() -> None:
    """Setup filter group management UI."""
    group_names = list(st.session_state.filter_groups.keys())
    if not group_names:
        st.session_state.filter_groups["קבוצת סינון 1"] = []
        st.session_state.current_filter_group = "קבוצת סינון 1"
        st.rerun()

    current_index = (
        group_names.index(st.session_state.current_filter_group)
        if st.session_state.current_filter_group in group_names
        else 0
    )
    st.session_state.current_filter_group = st.selectbox(
        "קבוצת סינון פעילה:",
        group_names,
        index=current_index
    )

    col1, col2, col3 = st.columns(3)
    if col1.button("➕", help="הוסף קבוצה חדשה"):
        st.session_state.add_group_mode = True
    if col2.button("✏️", help="שנה שם קבוצה",
                   disabled=len(group_names) == 0):
        st.session_state.rename_group_mode = True
    if col3.button("🗑️", help="מחק קבוצה",
                   disabled=len(group_names) <= 1):
        del st.session_state.filter_groups[
            st.session_state.current_filter_group
        ]
        st.session_state.current_filter_group = list(
            st.session_state.filter_groups.keys()
        )[0]
        save_filter_groups()
        st.rerun()

    # Handle add group mode
    if st.session_state.add_group_mode:
        with st.form("add_group_form"):
            new_group_name = st.text_input("שם קבוצה חדשה:")
            submitted = st.form_submit_button("שמור")
            if submitted and new_group_name:
                if new_group_name not in st.session_state.filter_groups:
                    st.session_state.filter_groups[new_group_name] = []
                    st.session_state.current_filter_group = new_group_name
                    st.session_state.add_group_mode = False
                    save_filter_groups()
                    st.rerun()
                else:
                    st.error("שם קבוצה זה כבר קיים!")

    # Handle rename group mode
    if st.session_state.rename_group_mode:
        with st.form("rename_group_form"):
            new_name = st.text_input(
                "שם חדש לקבוצה:",
                value=st.session_state.current_filter_group
            )
            submitted = st.form_submit_button("שמור שינויים")
            if (submitted and new_name and
                    new_name != st.session_state.current_filter_group):
                if new_name not in st.session_state.filter_groups:
                    st.session_state.filter_groups[new_name] = (
                        st.session_state.filter_groups.pop(
                            st.session_state.current_filter_group
                        )
                    )
                    st.session_state.current_filter_group = new_name
                    st.session_state.rename_group_mode = False
                    save_filter_groups()
                    st.rerun()
                else:
                    st.error("שם קבוצה זה כבר קיים!")


def setup_filter_conditions() -> None:
    """Setup filter conditions UI."""
    active_group = st.session_state.current_filter_group
    if active_group not in st.session_state.filter_groups:
        st.warning("קבוצת הסינון שנבחרה אינה קיימת. נא לבחור קבוצה אחרת.")
        return

    conditions = st.session_state.filter_groups[active_group]
    rsi_len = st.session_state.rsi_config['length']

    column_options = {
        "מחיר ($)": "numeric",
        "P/E": "numeric",
        "מכפיל רווח עתידי": "numeric",
        "שווי שוק (B$)": "numeric",
        f"RSI ({rsi_len})": "numeric",
        "עקביות בהכנסות (עולה)": "growth",
        "עקביות ברווח נקי (עולה)": "growth",
        "עקביות בהכנסות (יורדת)": "growth_decreasing",
        "עקביות ברווח נקי (יורדת)": "growth_decreasing",
        "הכנסות ורווחים עקביים": "boolean",
        "נגיעת Auto Anchor VWAP": "boolean",
        "נגיעה בממוצע נע (SMA)": "sma_touch",
        "חציית MACD שורית": "boolean",
        "חציית MACD דובית": "boolean",
        "תבנית נר": "candlestick_pattern"
    }

    # Add enabled SMAs to options
    for sma_config in st.session_state.sma_configs:
        if sma_config['enabled']:
            column_options[f"SMA {sma_config['length']}"] = "numeric"

    def draw_condition(i: int, condition: Dict) -> None:
        """Draw a single filter condition."""
        col1, col2, col3 = st.columns([4, 4, 1])
        current_column = condition.get("column", "מחיר ($)")
        if current_column not in column_options:
            current_column = "מחיר ($)"

        condition["column"] = col1.selectbox(
            "עמודה",
            list(column_options.keys()),
            key=f"col_{i}",
            index=list(column_options.keys()).index(current_column)
        )

        col_type = column_options[condition["column"]]

        if col_type == "numeric":
            c2_1, c2_2 = col2.columns(2)
            condition["operator"] = c2_1.selectbox(
                "תנאי",
                [">", "<", "=", ">=", "<="],
                key=f"op_{i}",
                index=[">", "<", "=", ">=", "<="].index(
                    condition.get("operator", ">")
                )
            )
            condition["value"] = c2_2.number_input(
                "ערך",
                value=float(condition.get("value", 0)),
                key=f"val_{i}",
                format="%.2f"
            )
        elif col_type in ["growth", "growth_decreasing"]:
            condition["years_value"] = col2.number_input(
                "שנים",
                min_value=2,
                max_value=5,
                value=condition.get("years_value", 3),
                key=f"years_{i}"
            )
        elif col_type == "sma_touch":
            sma_options = [
                cfg['length'] for cfg in st.session_state.sma_configs
                if cfg['enabled']
            ]
            if sma_options:
                condition["sma_length"] = col2.selectbox(
                    "בחר SMA",
                    sma_options,
                    key=f"sma_len_{i}"
                )
            else:
                col2.warning("אין SMA מופעל")
        elif col_type == "candlestick_pattern":
            pattern_options = ["Doji", "Hammer", "Hanging Man"]
            condition["pattern_value"] = col2.selectbox(
                "בחר תבנית",
                pattern_options,
                key=f"pattern_{i}",
                index=pattern_options.index(
                    condition.get("pattern_value", pattern_options[0])
                )
            )

        if col3.button("✖️", key=f"del_{i}", help="מחק תנאי"):
            conditions.pop(i)
            save_filter_groups()
            st.rerun()

    # Draw all conditions
    for i, cond in enumerate(conditions):
        draw_condition(i, cond)

    if st.button("➕ הוסף תנאי"):
        conditions.append({"column": "מחיר ($)", "operator": ">", "value": 0})
        st.rerun()

    save_filter_groups()


def display_main_content(index_df: pd.DataFrame) -> None:
    """
    Display main content area.

    Args:
        index_df: DataFrame with index symbols
    """
    st.title("📊 סורק מניות מתקדם")

    # Action buttons
    c1, c2, c3, c4 = st.columns(4)

    if c1.button("🚀 סרוק נתונים", type="primary",
                 use_container_width=True):
        with st.spinner("סורק נתונים, נא להמתין..."):
            st.session_state.full_df = run_data_fetch_and_process(index_df)
            st.session_state.filtered_df = (
                st.session_state.full_df.copy()
                if st.session_state.full_df is not None
                else None
            )
            st.session_state.previous_filtered_df = None
            st.success("סריקה הושלמה!")
            st.rerun()

    data_exists = (st.session_state.full_df is not None and
                   not st.session_state.full_df.empty)

    if c2.button("🔍 החל סינון", use_container_width=True,
                 disabled=not data_exists):
        st.session_state.previous_filtered_df = (
            st.session_state.filtered_df.copy()
        )
        conditions = st.session_state.filter_groups.get(
            st.session_state.current_filter_group, []
        )
        st.session_state.filtered_df = apply_filters_to_df(
            st.session_state.full_df.copy(), conditions
        )
        if st.session_state.filtered_df.empty:
            st.warning("לא נמצאו מניות התואמות לתנאי הסינון שנבחרו.")
        st.rerun()

    has_previous = st.session_state.previous_filtered_df is not None
    if c3.button("↩️ בטל סינון", use_container_width=True,
                 disabled=not has_previous):
        st.session_state.filtered_df = (
            st.session_state.previous_filtered_df.copy()
        )
        st.session_state.previous_filtered_df = None
        st.rerun()

    if c4.button("🧹 אפס הכל", use_container_width=True,
                 disabled=not data_exists):
        st.session_state.filtered_df = st.session_state.full_df.copy()
        st.session_state.previous_filtered_df = None
        st.rerun()

    # Display data
    if st.session_state.filtered_df is not None:
        display_grid_view()
    else:
        st.info("לחץ על 'סרוק נתונים' כדי להתחיל.")


def display_grid_view() -> None:
    """Display data in grid format."""
    df = st.session_state.filtered_df
    full_df = st.session_state.full_df

    if full_df is not None and not full_df.empty:
        total_stocks = len(full_df)
        filtered_stocks = len(df)
        if filtered_stocks == total_stocks:
            st.subheader(f"📊 מציג {filtered_stocks} מניות (ללא סינון)")
        else:
            st.subheader(f"🔍 נמצאו {filtered_stocks} מתוך {total_stocks} מניות")
            active_group = st.session_state.current_filter_group
            conditions_count = len(
                st.session_state.filter_groups.get(active_group, [])
            )
            st.info(f"סינון פעיל: **{active_group}** ({conditions_count} תנאים)")
    else:
        st.subheader("אין נתונים להצגה")
        return

    if df.empty:
        st.warning("לא נמצאו מניות התואמות לתנאי הסינון.")
        return

    # Prepare DataFrame for display
    display_df = df.copy()

    # Configure AgGrid
    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_selection('multiple', use_checkbox=True)

    # Hide internal columns
    hidden_cols = [
        col for col in display_df.columns
        if ('data' in col.lower() or 'series' in col.lower() or
            'filter' in col.lower() or 'touch' in col.lower() or
            'Cross' in col or 'Last' in col)
    ]
    for col in hidden_cols:
        gb.configure_column(col, hide=True)

    # Display grid
    grid_response = AgGrid(
        display_df,
        gridOptions=gb.build(),
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
        height=400,
        allow_unsafe_jscode=True
    )

    # Handle selected rows
    selected_rows = grid_response.get('selected_rows')
    selected_symbols = []

    if isinstance(selected_rows, pd.DataFrame):
        if not selected_rows.empty:
            selected_symbols = selected_rows['Symbol'].tolist()
    elif selected_rows:
        selected_symbols = [row['Symbol'] for row in selected_rows]

    if selected_symbols:
        st.markdown("---")
        st.subheader("פרטי מניות נבחרות")
        df_indexed = st.session_state.filtered_df.set_index('Symbol')
        for symbol in selected_symbols:
            if symbol in df_indexed.index:
                display_single_stock_details(df_indexed.loc[symbol])


def display_single_stock_details(stock_series: pd.Series) -> None:
    """
    Display detailed information for a single stock.

    Args:
        stock_series: Series with stock data
    """
    symbol = stock_series.name
    st.markdown(f"### {stock_series.get('Name', 'N/A')} ({symbol})")

    # Display price chart
    fig_combined = create_combined_charts(symbol, stock_series)
    if fig_combined:
        st.plotly_chart(fig_combined, use_container_width=True)

    # Display financial chart
    fig_financials = create_financials_chart(stock_series)
    if fig_financials:
        st.plotly_chart(fig_financials, use_container_width=True)

    st.markdown("---")


def create_combined_charts(symbol: str,
                           stock_series: pd.Series) -> Optional[go.Figure]:
    """
    Create combined price and indicator charts.

    Args:
        symbol: Stock symbol
        stock_series: Series with stock data

    Returns:
        Plotly Figure or None if failed
    """
    df_orig = get_chart_data(symbol)
    if df_orig is None or df_orig.empty:
        return go.Figure().update_layout(
            title=f"לא נמצאו נתונים עבור {symbol}"
        )

    df_display = df_orig.copy()
    if st.session_state.chart_type == "Heikin Ashi":
        df_display = calculate_heikin_ashi(df_orig.copy())
        if df_display.empty:
            df_display = df_orig.copy()

    # Calculate subplot configuration
    rows = 1
    subplot_titles = ["גרף מחיר"]
    has_rsi = (st.session_state.rsi_config['enabled'] and
               f"RSI_{st.session_state.rsi_config['length']}" in df_orig.columns)
    has_macd = (st.session_state.macd_config['enabled'] and
                'MACD_line' in df_orig.columns)

    if has_rsi:
        rows += 1
        subplot_titles.append("RSI")
    if has_macd:
        rows += 1
        subplot_titles.append("MACD")

    row_heights = [0.6]
    if has_rsi:
        row_heights.append(0.2)
    if has_macd:
        row_heights.append(0.2)

    # Create subplots
    fig = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=subplot_titles,
        row_heights=row_heights
    )

    # Add price chart
    trace_params = {
        'x': df_display.index,
        'name': 'מחיר',
        'showlegend': False
    }

    if st.session_state.chart_type == "גרף נרות":
        trace_params.update({
            'open': df_orig['Open'],
            'high': df_orig['High'],
            'low': df_orig['Low'],
            'close': df_orig['Close']
        })
        fig.add_trace(go.Candlestick(**trace_params), row=1, col=1)
    elif (st.session_state.chart_type == "Heikin Ashi" and
          not df_display.empty):
        trace_params.update({
            'open': df_display['HA_Open'],
            'high': df_display['HA_High'],
            'low': df_display['HA_Low'],
            'close': df_display['HA_Close']
        })
        fig.add_trace(go.Candlestick(**trace_params), row=1, col=1)
    else:  # Line chart
        trace_params.update({
            'y': df_orig['Close'],
            'mode': 'lines',
            'line': {'color': 'blue'}
        })
        fig.add_trace(go.Scatter(**trace_params), row=1, col=1)

    # Add SMA lines
    colors = ['orange', 'red', 'purple', 'brown', 'pink', 'gray']
    for i, length in enumerate(st.session_state.chart_sma_lengths):
        sma_col = f'SMA_{length}'
        if sma_col in df_orig.columns:
            fig.add_trace(go.Scatter(
                x=df_orig.index,
                y=df_orig[sma_col],
                mode='lines',
                name=f"SMA({length})",
                line=dict(width=1.5, dash='dot',
                          color=colors[i % len(colors)])
            ), row=1, col=1)

    current_row = 2

    # Add RSI subplot
    if has_rsi:
        rsi_col = f"RSI_{st.session_state.rsi_config['length']}"
        fig.add_trace(
            go.Scatter(
                x=df_orig.index,
                y=df_orig[rsi_col],
                name='RSI',
                line=dict(color='purple'),
                showlegend=False
            ),
            row=current_row, col=1
        )
        fig.add_hline(y=70, line_dash="dash", line_color="red",
                      row=current_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green",
                      row=current_row, col=1)
        fig.update_yaxes(range=[0, 100], row=current_row, col=1)
        current_row += 1

    # Add MACD subplot
    if has_macd:
        colors_hist = [
            'green' if val >= 0 else 'red'
            for val in df_orig['MACD_histogram']
        ]
        fig.add_trace(go.Bar(
            x=df_orig.index,
            y=df_orig['MACD_histogram'],
            name='Histogram',
            marker_color=colors_hist,
            showlegend=False,
            opacity=0.7
        ), row=current_row, col=1)

        fig.add_trace(go.Scatter(
            x=df_orig.index,
            y=df_orig['MACD_line'],
            name='MACD',
            line=dict(color='blue', width=2),
            showlegend=False
        ), row=current_row, col=1)

        fig.add_trace(go.Scatter(
            x=df_orig.index,
            y=df_orig['MACD_signal_line'],
            name='Signal',
            line=dict(color='orange', width=2),
            showlegend=False
        ), row=current_row, col=1)

    # Update layout
    fig.update_layout(
        height=600,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis_rangeslider_visible=False
    )

    # Hide x-axis labels for all but last subplot
    for i in range(1, rows):
        fig.update_xaxes(showticklabels=False, row=i, col=1)

    return fig


def create_financials_chart(stock_series: pd.Series) -> go.Figure:
    """
    Create financial data chart.

    Args:
        stock_series: Series with stock financial data

    Returns:
        Plotly Figure with financial chart
    """
    period = st.session_state.financial_period
    data_key = ("quarterly_financial_data" if period == "רבעוני"
                else "annual_financial_data")
    financial_data = stock_series.get(data_key, [])

    fig = go.Figure()
    if not financial_data:
        return fig.update_layout(title=f"אין נתונים פיננסיים ({period})")

    try:
        df = pd.DataFrame(financial_data)
        if df.empty:
            return fig.update_layout(title=f"אין נתונים פיננסיים ({period})")

        # Add revenue bars
        fig.add_trace(go.Bar(
            x=df['date'],
            y=df['revenue'],
            name='הכנסות',
            marker_color='blue'
        ))

        # Add net income bars with conditional coloring
        fig.add_trace(go.Bar(
            x=df['date'],
            y=df['net_income'],
            name='רווח נקי',
            marker_color=[
                'green' if ni >= 0 else 'red'
                for ni in df['net_income']
            ]
        ))

        fig.update_layout(
            barmode='group',
            title=f'דוחות כספיים ({period})',
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
            yaxis_title="מיליארד $"
        )
    except Exception:
        return fig.update_layout(
            title=f"שגיאה בהצגת נתונים פיננסיים ({period})"
        )

    return fig


# ==============================================================================
# MAIN APPLICATION FUNCTION
# ==============================================================================

def main() -> None:
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="סורק מניות", layout="wide")
    initialize_session_state()

    # Handle index selection changes
    current_index_selection = st.session_state.get('sb_index_selection')
    new_selected_index = setup_sidebar()

    if new_selected_index != current_index_selection:
        st.session_state.full_df = None
        st.session_state.filtered_df = None
        st.rerun()

    # Load index symbols
    index_df = load_index_symbols(new_selected_index)
    if index_df.empty:
        st.error(f"לא ניתן לטעון מניות עבור {new_selected_index}.")
        st.stop()

    # Display main content
    display_main_content(index_df)


if __name__ == "__main__":
    main()
