# 📊 Advanced Stock Screener

A comprehensive stock screening application built with Streamlit that allows you to analyze and filter stocks from major indices using technical indicators and financial metrics.

## 🚀 Features

### Technical Indicators
- **Simple Moving Averages (SMA)**: Configurable periods (20, 50, 150, 200)
- **RSI (Relative Strength Index)**: Configurable period (default 14)
- **MACD**: Configurable fast, slow, and signal periods
- **Candlestick Pattern Detection**: Doji, Hammer, Hanging Man patterns

### Stock Indices Support
- S&P 500
- Nasdaq 100
- Dow Jones Industrial Average
- Russell 2000

### Filtering Capabilities
- Price-based filters
- P/E ratio filters
- Market capitalization filters
- Technical indicator filters
- Financial growth consistency filters
- Candlestick pattern filters

### Visualization
- Interactive price charts with candlesticks, line charts, and Heikin Ashi
- Technical indicator overlays
- Financial performance charts
- Multi-timeframe analysis

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

1. **Clone or download the files**:
   ```bash
   # Make sure you have these files:
   # - stock_screener.py
   # - requirements.txt
   # - README.md
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   If you encounter permission issues, use:
   ```bash
   pip install --user -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   streamlit run stock_screener.py
   ```

   The application will open in your browser at `http://localhost:8501`

## 📖 Usage Guide

### 1. Getting Started
1. **Select an Index**: Choose from S&P 500, Nasdaq 100, Dow Jones, or Russell 2000 in the sidebar
2. **Configure Indicators**: Set up your preferred technical indicators in the Settings section
3. **Scan Data**: Click the "🚀 סרוק נתונים" (Scan Data) button to fetch current stock data

### 2. Setting Up Filters
1. **Create Filter Groups**: Organize your screening criteria into named groups
2. **Add Conditions**: Set up filtering conditions based on:
   - Price ranges
   - P/E ratios
   - Market capitalization
   - Technical indicators (RSI, SMA touches, MACD crossovers)
   - Financial growth patterns
   - Candlestick patterns

### 3. Analyzing Results
1. **Apply Filters**: Click "🔍 החל סינון" (Apply Filter) to screen stocks
2. **Review Results**: Browse the filtered stock list in the interactive table
3. **Select Stocks**: Check boxes next to stocks for detailed analysis
4. **View Charts**: Selected stocks will display detailed price and financial charts

### 4. Advanced Features
- **Multiple Chart Types**: Switch between candlestick, line, and Heikin Ashi charts
- **Custom Timeframes**: View quarterly or annual financial data
- **Export Capabilities**: Filter results can be exported for further analysis

## 🔧 Configuration Options

### Technical Indicators
- **SMA Periods**: Enable/disable and configure different moving average periods
- **RSI Length**: Adjust the RSI calculation period
- **MACD Parameters**: Customize fast, slow, and signal line periods
- **Doji Threshold**: Set sensitivity for Doji pattern detection

### Display Settings
- **Chart Type**: Choose between candlestick, line, or Heikin Ashi charts
- **Financial Period**: Select quarterly or annual financial data display
- **SMA Overlays**: Choose which moving averages to display on charts

## 📊 Key Metrics Displayed

### Basic Information
- Stock Symbol and Company Name
- Current Price
- P/E Ratio (Trailing and Forward)
- Market Capitalization
- Trading Volume

### Technical Indicators
- Simple Moving Averages (configurable periods)
- RSI values with overbought/oversold signals
- MACD line, signal line, and histogram
- Bullish/Bearish crossover signals

### Financial Health
- Revenue growth consistency
- Net income growth consistency
- Quarterly and annual financial trends

### Pattern Recognition
- Doji candlestick patterns
- Hammer patterns
- Hanging Man patterns
- SMA touch detection

## 🚨 Important Notes

### Data Sources
- **Stock Data**: Yahoo Finance (via yfinance library)
- **Index Compositions**: Wikipedia and other public sources
- **Update Frequency**: Data is cached for performance but refreshed periodically

### Limitations
- **Demo Mode**: Currently limited to first 20 stocks per index for performance
- **Rate Limits**: Yahoo Finance may impose rate limits on data requests
- **Market Hours**: Some data may be delayed during market hours

### Performance Tips
- **Batch Processing**: The app processes multiple stocks simultaneously
- **Caching**: Results are cached to improve response times
- **Error Handling**: Failed stock fetches are logged and skipped

## 🛡️ Error Handling

The application includes comprehensive error handling for:
- Network connectivity issues
- Invalid stock symbols
- Missing financial data
- API rate limiting
- Data parsing errors

Errors are displayed in expandable sections with detailed information.

## 🔄 Updates and Maintenance

### Regular Updates
- Stock lists are refreshed automatically
- Technical indicators are recalculated with each scan
- Financial data is updated when available

### Troubleshooting
1. **Import Errors**: Ensure all dependencies are installed
2. **Network Issues**: Check internet connectivity
3. **Performance Issues**: Reduce the number of stocks being processed
4. **Display Issues**: Try refreshing the browser

## 📝 File Structure

```
stock_screener/
├── stock_screener.py      # Main application file
├── requirements.txt       # Python dependencies
├── README.md             # This documentation
├── test_app.py           # Test script
└── filter_groups.json   # Filter configurations (created automatically)
```

## 🧪 Testing

Run the test script to verify functionality:
```bash
python3 test_app.py
```

This will test:
- Module imports
- Data fetching capabilities
- Technical indicator calculations
- Stock symbol loading

## 🤝 Contributing

This is a demonstration application. For production use, consider:
- Expanding to more stock indices
- Adding more technical indicators
- Implementing real-time data feeds
- Adding portfolio management features
- Improving error handling and logging

## 📄 License

This project is provided as-is for educational and demonstration purposes.

## ⚠️ Disclaimer

This application is for educational and informational purposes only. It should not be considered as financial advice. Always consult with qualified financial professionals before making investment decisions.

---

**Happy Stock Screening! 📈**