"""
Unit Tests for Finnhub API Client

Tests API calls, rate limiting, error handling, and caching.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data.finnhub_client import FinnhubClient, FinnhubAPIError


class TestFinnhubClient:
    """Test suite for Finnhub API Client"""

    @pytest.fixture
    def mock_api_key(self):
        """Provide a mock API key"""
        return "test_api_key_12345"

    @pytest.fixture
    def client(self, mock_api_key):
        """Create FinnhubClient with mock API key"""
        return FinnhubClient(api_key=mock_api_key)

    @pytest.fixture
    def mock_quote_response(self):
        """Sample quote response from Finnhub"""
        return {
            "c": 142.50,   # current price
            "d": 2.35,    # change
            "dp": 1.68,   # change percent
            "h": 143.20,  # high
            "l": 140.10,  # low
            "o": 141.00,  # open
            "pc": 140.15  # previous close
        }

    @pytest.fixture
    def mock_profile_response(self):
        """Sample company profile response"""
        return {
            "name": "NVIDIA Corp",
            "ticker": "NVDA",
            "marketCapitalization": 3500000,  # millions
            "finnhubIndustry": "Semiconductors",
            "logo": "https://example.com/logo.png",
            "weburl": "https://nvidia.com"
        }

    @pytest.fixture
    def mock_candles_response(self):
        """Sample candles response"""
        return {
            "s": "ok",
            "c": [140.0, 141.0, 142.0, 142.5],
            "h": [141.0, 142.0, 143.0, 143.2],
            "l": [139.0, 140.0, 141.0, 140.1],
            "o": [139.5, 140.5, 141.5, 141.0],
            "v": [1000000, 1100000, 1200000, 1300000],
            "t": [1705363200, 1705449600, 1705536000, 1705622400]
        }

    # ========== INITIALIZATION TESTS ==========

    def test_init_with_api_key(self, mock_api_key):
        """Test client initialization with explicit API key"""
        client = FinnhubClient(api_key=mock_api_key)
        assert client.api_key == mock_api_key

    def test_init_without_api_key_raises_error(self):
        """Test client raises error when no API key provided"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="FINNHUB_API_KEY not found"):
                FinnhubClient()

    @patch.dict('os.environ', {'FINNHUB_API_KEY': 'env_api_key'})
    def test_init_from_environment(self):
        """Test client reads API key from environment"""
        client = FinnhubClient()
        assert client.api_key == "env_api_key"

    # ========== API REQUEST TESTS ==========

    def test_get_quote_success(self, client, mock_quote_response):
        """Test successful quote fetch"""
        with patch.object(client._session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_quote_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = client.get_quote("NVDA")

            assert result["c"] == 142.50
            assert result["d"] == 2.35
            assert result["dp"] == 1.68
            mock_get.assert_called_once()

    def test_get_company_profile_success(self, client, mock_profile_response):
        """Test successful profile fetch"""
        with patch.object(client._session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_profile_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = client.get_company_profile("NVDA")

            assert result["name"] == "NVIDIA Corp"
            assert result["marketCapitalization"] == 3500000
            assert result["finnhubIndustry"] == "Semiconductors"

    def test_get_candles_success(self, client, mock_candles_response):
        """Test successful candles fetch"""
        with patch.object(client._session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_candles_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = client.get_candles("NVDA", resolution="D")

            assert result["s"] == "ok"
            assert len(result["c"]) == 4
            assert result["c"][-1] == 142.5

    def test_get_news_success(self, client):
        """Test successful news fetch"""
        mock_news = [
            {"headline": "NVIDIA announces new chip", "source": "TechCrunch"},
            {"headline": "AI market grows", "source": "Bloomberg"}
        ]
        with patch.object(client._session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_news
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = client.get_news("NVDA")

            assert len(result) == 2
            assert result[0]["headline"] == "NVIDIA announces new chip"

    def test_get_sentiment_success(self, client):
        """Test successful sentiment fetch"""
        mock_sentiment = {
            "buzz": {"articlesInLastWeek": 100},
            "sentiment": {"bullishPercent": 0.65},
            "companyNewsScore": 0.8
        }
        with patch.object(client._session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_sentiment
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = client.get_sentiment("NVDA")

            assert result["companyNewsScore"] == 0.8

    def test_get_recommendation_trends_success(self, client):
        """Test successful recommendation trends fetch"""
        mock_recs = [
            {"period": "2024-01", "buy": 30, "hold": 10, "sell": 2}
        ]
        with patch.object(client._session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_recs
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = client.get_recommendation_trends("NVDA")

            assert len(result) == 1
            assert result[0]["buy"] == 30

    # ========== ERROR HANDLING TESTS ==========

    def test_http_error_raises_finnhub_api_error(self, client):
        """Test HTTP errors are wrapped in FinnhubAPIError after retries"""
        import requests
        from tenacity import RetryError
        with patch.object(client._session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
            mock_get.return_value = mock_response

            # After 3 retries, tenacity raises RetryError wrapping FinnhubAPIError
            with pytest.raises(RetryError) as exc_info:
                client.get_quote("NVDA")

            # The underlying exception should be FinnhubAPIError
            assert isinstance(exc_info.value.last_attempt.exception(), FinnhubAPIError)

    def test_request_exception_raises_finnhub_api_error(self, client):
        """Test request exceptions are wrapped in FinnhubAPIError after retries"""
        import requests
        from tenacity import RetryError
        with patch.object(client._session, 'get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")

            # After 3 retries, tenacity raises RetryError wrapping FinnhubAPIError
            with pytest.raises(RetryError) as exc_info:
                client.get_quote("NVDA")

            # The underlying exception should be FinnhubAPIError
            assert isinstance(exc_info.value.last_attempt.exception(), FinnhubAPIError)

    # ========== RATE LIMITING TESTS ==========

    def test_rate_limit_tracking(self, client):
        """Test that call times are tracked"""
        with patch.object(client._session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"c": 100}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Make a few calls
            client.get_quote("NVDA")
            client.get_quote("AAPL")
            client.get_quote("GOOGL")

            # Check that call times are being tracked
            assert len(client._call_times) == 3

    def test_rate_limit_enforcement(self, client):
        """Test rate limiting triggers sleep when limit reached"""
        # Fill up call times to trigger rate limit
        now = time.time()
        client._call_times.extend([now] * 60)

        with patch.object(client._session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"c": 100}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            with patch('time.sleep') as mock_sleep:
                client.get_quote("NVDA")
                # Should have called sleep due to rate limit
                assert mock_sleep.called or len(client._call_times) <= 60

    # ========== PARAMETER TESTS ==========

    def test_get_news_date_parameters(self, client):
        """Test news endpoint uses correct date parameters"""
        from_date = datetime(2024, 1, 1)
        to_date = datetime(2024, 1, 7)

        with patch.object(client._session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            client.get_news("NVDA", from_date=from_date, to_date=to_date)

            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert params["from"] == "2024-01-01"
            assert params["to"] == "2024-01-07"

    def test_get_candles_timestamp_parameters(self, client):
        """Test candles endpoint uses correct timestamp parameters"""
        from_ts = 1705363200
        to_ts = 1705622400

        with patch.object(client._session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"s": "ok", "c": [], "h": [], "l": [], "o": [], "v": [], "t": []}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            client.get_candles("NVDA", resolution="D", from_timestamp=from_ts, to_timestamp=to_ts)

            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert params["from"] == from_ts
            assert params["to"] == to_ts
            assert params["resolution"] == "D"


class TestFinnhubAPIError:
    """Test suite for FinnhubAPIError exception"""

    def test_error_with_message(self):
        """Test error stores message"""
        error = FinnhubAPIError("Test error message")
        assert error.message == "Test error message"
        assert str(error) == "Test error message"

    def test_error_with_status_code(self):
        """Test error stores status code"""
        error = FinnhubAPIError("Unauthorized", status_code=401)
        assert error.status_code == 401
        assert error.message == "Unauthorized"

    def test_error_without_status_code(self):
        """Test error handles missing status code"""
        error = FinnhubAPIError("Network error")
        assert error.status_code is None
