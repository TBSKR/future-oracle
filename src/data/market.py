"""Market Data Module - Uses Finnhub API"""

import streamlit as st
from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime, timedelta
import logging
import os

from data.finnhub_client import FinnhubClient, FinnhubAPIError


class MarketDataFetcher:
    """Fetches market data using Finnhub API with caching"""

    def __init__(self, finnhub_client: Optional[FinnhubClient] = None):
        self.logger = logging.getLogger("futureoracle.market")
        try:
            self.finnhub = finnhub_client or FinnhubClient()
            self._api_key = self.finnhub.api_key
            self._available = True
        except ValueError:
            self.logger.warning("FinnhubClient not available - API key missing")
            self.finnhub = None
            self._api_key = None
            self._available = False

    # ========== CACHED STATIC METHODS ==========

    @staticmethod
    @st.cache_data(ttl=3600)  # 1 hour cache
    def _cached_quote(ticker: str, api_key: str) -> Dict[str, Any]:
        client = FinnhubClient(api_key=api_key)
        return client.get_quote(ticker)

    @staticmethod
    @st.cache_data(ttl=3600)
    def _cached_profile(ticker: str, api_key: str) -> Dict[str, Any]:
        client = FinnhubClient(api_key=api_key)
        return client.get_company_profile(ticker)

    @staticmethod
    @st.cache_data(ttl=3600)
    def _cached_candles(ticker: str, resolution: str, from_ts: int, to_ts: int, api_key: str) -> Dict[str, Any]:
        client = FinnhubClient(api_key=api_key)
        return client.get_candles(ticker, resolution, from_ts, to_ts)

    # ========== PUBLIC METHODS ==========

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get current price for a ticker"""
        if not self._available:
            return None
        try:
            quote = self._cached_quote(ticker, self._api_key)
            return quote.get("c")  # current price
        except Exception as e:
            self.logger.error(f"Error fetching price for {ticker}: {e}")
            return None

    def get_quote(self, ticker: str) -> Dict[str, Any]:
        """Get comprehensive quote data"""
        if not self._available:
            return {"ticker": ticker, "error": "Finnhub API not configured"}
        try:
            quote = self._cached_quote(ticker, self._api_key)
            profile = self._cached_profile(ticker, self._api_key)

            return {
                "ticker": ticker,
                "price": quote.get("c"),
                "change": quote.get("d"),
                "change_percent": quote.get("dp"),
                "volume": None,  # Need candle data for volume
                "market_cap": (profile.get("marketCapitalization") or 0) * 1_000_000,
                "52w_high": None,  # Requires historical calculation
                "52w_low": None,
                "company_name": profile.get("name"),
                "sector": None,  # Not in Finnhub free tier
                "industry": profile.get("finnhubIndustry"),
                "timestamp": datetime.now().isoformat()
            }
        except FinnhubAPIError as e:
            self.logger.error(f"Error fetching quote for {ticker}: {e}")
            return {"ticker": ticker, "error": str(e)}

    def get_historical_data(self, ticker: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        """Get historical OHLCV data"""
        if not self._available:
            return pd.DataFrame()

        period_days = {"1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730}
        interval_res = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "1d": "D", "1wk": "W", "1mo": "M"}

        days = period_days.get(period, 30)
        resolution = interval_res.get(interval, "D")
        to_ts = int(datetime.now().timestamp())
        from_ts = int((datetime.now() - timedelta(days=days)).timestamp())

        try:
            candles = self._cached_candles(ticker, resolution, from_ts, to_ts, self._api_key)
            if candles.get("s") != "ok":
                return pd.DataFrame()

            return pd.DataFrame({
                "Open": candles["o"], "High": candles["h"], "Low": candles["l"],
                "Close": candles["c"], "Volume": candles["v"]
            }, index=pd.to_datetime(candles["t"], unit="s"))
        except Exception as e:
            self.logger.error(f"Error fetching historical data for {ticker}: {e}")
            return pd.DataFrame()

    def get_watchlist_snapshot(self, tickers: List[str]) -> List[Dict[str, Any]]:
        """Get quotes for multiple tickers"""
        return [self.get_quote(t) for t in tickers]

    def calculate_returns(self, ticker: str, start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> Dict[str, float]:
        """Calculate returns for various periods"""
        try:
            data = self.get_historical_data(ticker, period="1y")
            if data.empty:
                return {}

            current = data['Close'].iloc[-1]
            return {
                "1d": self._calc_return(data, 1, current),
                "1w": self._calc_return(data, 7, current),
                "1m": self._calc_return(data, 30, current),
                "3m": self._calc_return(data, 90, current),
                "6m": self._calc_return(data, 180, current),
                "1y": self._calc_return(data, 365, current),
            }
        except Exception as e:
            self.logger.error(f"Error calculating returns for {ticker}: {e}")
            return {}

    def _calc_return(self, data: pd.DataFrame, days: int, current: float) -> Optional[float]:
        try:
            if len(data) < days:
                return None
            past = data['Close'].iloc[-days]
            return ((current - past) / past) * 100
        except:
            return None
