"""Finnhub API Client - Reliable market data source"""

import os
import time
import logging
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import deque
import requests
from tenacity import retry, stop_after_attempt, wait_exponential


class FinnhubAPIError(Exception):
    """Custom exception for Finnhub API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ThreadSafeRateLimiter:
    """
    Thread-safe rate limiter for API calls.
    
    Uses a sliding window approach with a lock to safely coordinate
    rate limiting across multiple threads.
    """
    
    def __init__(self, calls_per_minute: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_minute: Maximum API calls allowed per minute (default 60)
        """
        self._lock = threading.Lock()
        self._call_times: deque = deque(maxlen=calls_per_minute)
        self._rate_limit = calls_per_minute
        self._rate_window = 60  # seconds
        self._logger = logging.getLogger("futureoracle.rate_limiter")
    
    def acquire(self) -> None:
        """
        Block until a request slot is available.
        
        Thread-safe: uses a lock to coordinate access across threads.
        """
        with self._lock:
            now = time.time()
            
            # Remove timestamps outside the window
            while self._call_times and now - self._call_times[0] > self._rate_window:
                self._call_times.popleft()
            
            # If at limit, calculate sleep time and wait
            if len(self._call_times) >= self._rate_limit:
                sleep_time = self._rate_window - (now - self._call_times[0]) + 0.1
                if sleep_time > 0:
                    self._logger.warning(f"Rate limit reached, sleeping {sleep_time:.2f}s")
                    # Release lock while sleeping so other threads can check
                    self._lock.release()
                    try:
                        time.sleep(sleep_time)
                    finally:
                        self._lock.acquire()
                    # Re-check after sleep
                    now = time.time()
                    while self._call_times and now - self._call_times[0] > self._rate_window:
                        self._call_times.popleft()
            
            # Record this call
            self._call_times.append(time.time())
    
    @property
    def calls_remaining(self) -> int:
        """Get approximate number of calls remaining in current window."""
        with self._lock:
            now = time.time()
            # Count calls within window
            active_calls = sum(1 for t in self._call_times if now - t <= self._rate_window)
            return max(0, self._rate_limit - active_calls)


class FinnhubClient:
    """
    Client for Finnhub.io Market Data API.
    Free tier: 60 API calls/minute
    """

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(
        self, 
        api_key: Optional[str] = None,
        rate_limiter: Optional[ThreadSafeRateLimiter] = None
    ):
        """
        Initialize Finnhub client.
        
        Args:
            api_key: Finnhub API key (defaults to FINNHUB_API_KEY env var)
            rate_limiter: Optional shared ThreadSafeRateLimiter for cross-thread coordination.
                          If not provided, creates an instance-local limiter.
        """
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY")
        if not self.api_key:
            raise ValueError("FINNHUB_API_KEY not found")

        self.logger = logging.getLogger("futureoracle.finnhub")
        self._session = requests.Session()

        # Use shared rate limiter if provided, otherwise create instance-local one
        self._rate_limiter = rate_limiter or ThreadSafeRateLimiter(calls_per_minute=60)

    def _check_rate_limit(self):
        """Enforce rate limiting using the rate limiter."""
        self._rate_limiter.acquire()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to Finnhub API"""
        self._check_rate_limit()
        url = f"{self.BASE_URL}{endpoint}"
        params = params or {}
        params["token"] = self.api_key

        try:
            response = self._session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"Finnhub HTTP error: {e}")
            raise FinnhubAPIError(str(e), response.status_code)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Finnhub request error: {e}")
            raise FinnhubAPIError(str(e))

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote: c=current, d=change, dp=change%, h=high, l=low, o=open, pc=prev close"""
        return self._make_request("/quote", {"symbol": symbol})

    def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """Get company profile: name, marketCapitalization (millions), finnhubIndustry, logo, weburl"""
        return self._make_request("/stock/profile2", {"symbol": symbol})

    def get_news(self, symbol: str, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get company news: headline, source, datetime, url, summary"""
        to_date = to_date or datetime.now()
        from_date = from_date or (to_date - timedelta(days=7))
        return self._make_request("/company-news", {
            "symbol": symbol,
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d")
        })

    def get_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Get social sentiment: buzz, sentiment scores, companyNewsScore"""
        return self._make_request("/news-sentiment", {"symbol": symbol})

    def get_recommendation_trends(self, symbol: str) -> List[Dict[str, Any]]:
        """Get analyst recommendations: buy, hold, sell, strongBuy, strongSell counts"""
        return self._make_request("/stock/recommendation", {"symbol": symbol})

    def get_candles(self, symbol: str, resolution: str = "D",
                    from_timestamp: Optional[int] = None, to_timestamp: Optional[int] = None) -> Dict[str, Any]:
        """Get OHLCV candles. Resolution: 1, 5, 15, 30, 60, D, W, M"""
        to_ts = to_timestamp or int(datetime.now().timestamp())
        from_ts = from_timestamp or int((datetime.now() - timedelta(days=30)).timestamp())
        return self._make_request("/stock/candle", {
            "symbol": symbol, "resolution": resolution,
            "from": from_ts, "to": to_ts
        })
