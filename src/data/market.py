"""
Market Data Module

Fetches stock market data using yfinance.
Provides real-time quotes, historical data, and company information.
"""

import yfinance as yf
from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime, timedelta
import logging


class MarketDataFetcher:
    """
    Fetches and processes market data for the watchlist.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("futureoracle.market")
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """
        Get current price for a ticker.
        
        Args:
            ticker: Stock ticker symbol (e.g., "NVDA")
            
        Returns:
            Current price or None if unavailable
        """
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="1d")
            if not data.empty:
                return float(data['Close'].iloc[-1])
            return None
        except Exception as e:
            self.logger.error(f"Error fetching price for {ticker}: {e}")
            return None
    
    def get_quote(self, ticker: str) -> Dict[str, Any]:
        """
        Get comprehensive quote data for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with quote data
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            return {
                "ticker": ticker,
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "change": info.get("regularMarketChange"),
                "change_percent": info.get("regularMarketChangePercent"),
                "volume": info.get("volume"),
                "market_cap": info.get("marketCap"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "company_name": info.get("longName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error fetching quote for {ticker}: {e}")
            return {"ticker": ticker, "error": str(e)}
    
    def get_historical_data(
        self,
        ticker: str,
        period: str = "1mo",
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Get historical price data.
        
        Args:
            ticker: Stock ticker symbol
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            
        Returns:
            DataFrame with historical data
        """
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period=period, interval=interval)
            return data
        except Exception as e:
            self.logger.error(f"Error fetching historical data for {ticker}: {e}")
            return pd.DataFrame()
    
    def get_watchlist_snapshot(self, tickers: List[str]) -> List[Dict[str, Any]]:
        """
        Get current snapshot for multiple tickers.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            List of quote dictionaries
        """
        snapshots = []
        for ticker in tickers:
            quote = self.get_quote(ticker)
            snapshots.append(quote)
        
        return snapshots
    
    def calculate_returns(
        self,
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Calculate returns for various time periods.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            Dictionary with return percentages
        """
        try:
            stock = yf.Ticker(ticker)
            
            # Get historical data
            if start_date and end_date:
                data = stock.history(start=start_date, end=end_date)
            else:
                data = stock.history(period="1y")
            
            if data.empty:
                return {}
            
            current_price = data['Close'].iloc[-1]
            
            returns = {
                "1d": self._calc_return(data, days=1, current_price=current_price),
                "1w": self._calc_return(data, days=7, current_price=current_price),
                "1m": self._calc_return(data, days=30, current_price=current_price),
                "3m": self._calc_return(data, days=90, current_price=current_price),
                "6m": self._calc_return(data, days=180, current_price=current_price),
                "1y": self._calc_return(data, days=365, current_price=current_price),
            }
            
            return returns
            
        except Exception as e:
            self.logger.error(f"Error calculating returns for {ticker}: {e}")
            return {}
    
    def _calc_return(
        self,
        data: pd.DataFrame,
        days: int,
        current_price: float
    ) -> Optional[float]:
        """Helper to calculate return for a specific period"""
        try:
            if len(data) < days:
                return None
            past_price = data['Close'].iloc[-days]
            return ((current_price - past_price) / past_price) * 100
        except:
            return None
