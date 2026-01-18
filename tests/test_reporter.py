"""
Unit Tests for Reporter Agent

Tests data gathering, HTML generation, and email sending.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.reporter import ReporterAgent


class TestReporterAgent:
    """Test suite for Reporter Agent"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock Database for testing"""
        mock = Mock()
        mock.get_cached_signals = Mock(return_value=[
            {
                "title": "NVIDIA Breakthrough",
                "source": "TechCrunch",
                "relevance_score": 9,
                "matched_keywords": ["NVIDIA", "AI", "chip"]
            },
            {
                "title": "Tesla Humanoid Update",
                "source": "Bloomberg",
                "relevance_score": 8,
                "matched_keywords": ["Tesla", "humanoid", "robotics"]
            }
        ])
        return mock
    
    @pytest.fixture
    def mock_portfolio(self):
        """Mock PortfolioManager for testing"""
        mock = Mock()
        mock.get_portfolio_summary = Mock(return_value={
            "total_value": 50000,
            "total_return_pct": 25.5,
            "total_return_pct_24h": 2.3,
            "holdings_count": 5
        })
        return mock
    
    @pytest.fixture
    def reporter(self, mock_db, mock_portfolio):
        """Create Reporter instance with mocked dependencies"""
        return ReporterAgent(db=mock_db, portfolio=mock_portfolio)
    
    # ========== Test Data Gathering ==========
    
    def test_gather_report_data(self, reporter, mock_db, mock_portfolio):
        """Test gathering report data"""
        data = reporter._gather_report_data(days_back=7)
        
        assert "report_date" in data
        assert "top_signals" in data
        assert "portfolio_summary" in data
        assert "forecast_summary" in data
        assert "charts" in data
        
        # Verify data structure
        assert len(data["top_signals"]) == 2
        assert data["portfolio_summary"]["total_value"] == 50000
        assert data["forecast_summary"]["age_31_super_bull"] == 150000
    
    def test_gather_report_data_calls_db(self, reporter, mock_db):
        """Test that data gathering calls database correctly"""
        reporter._gather_report_data(days_back=14)
        
        mock_db.get_cached_signals.assert_called_once()
        call_args = mock_db.get_cached_signals.call_args
        assert call_args[1]["limit"] == 5
        assert call_args[1]["days_back"] == 14
    
    def test_gather_report_data_calls_portfolio(self, reporter, mock_portfolio):
        """Test that data gathering calls portfolio manager"""
        reporter._gather_report_data(days_back=7)
        
        mock_portfolio.get_portfolio_summary.assert_called_once()
    
    # ========== Test HTML Generation ==========
    
    def test_generate_html_report(self, reporter):
        """Test HTML report generation"""
        data = {
            "report_date": "January 18, 2026",
            "top_signals": [
                {
                    "title": "Test Signal",
                    "source": "Test Source",
                    "relevance_score": 9,
                    "matched_keywords": ["test", "signal"]
                }
            ],
            "portfolio_summary": {
                "total_value": 50000,
                "total_return_pct": 25.5,
                "total_return_pct_24h": 2.3
            },
            "forecast_summary": {
                "age_31_super_bull": 150000,
                "age_41_super_bull": 1200000,
                "age_51_super_bull": 8000000
            },
            "charts": {}
        }
        
        html = reporter._generate_html_report(data)
        
        assert html is not None
        assert len(html) > 0
        assert "FutureOracle" in html
        assert "January 18, 2026" in html
        assert "Test Signal" in html
        assert "€50,000" in html or "50000" in html
    
    def test_generate_html_report_includes_all_sections(self, reporter):
        """Test that HTML includes all required sections"""
        data = {
            "report_date": "January 18, 2026",
            "top_signals": [],
            "portfolio_summary": {
                "total_value": 0,
                "total_return_pct": 0,
                "total_return_pct_24h": 0
            },
            "forecast_summary": {
                "age_31_super_bull": 0,
                "age_41_super_bull": 0,
                "age_51_super_bull": 0
            },
            "charts": {}
        }
        
        html = reporter._generate_html_report(data)
        
        # Check for section headers
        assert "Top Signals" in html
        assert "Portfolio Snapshot" in html
        assert "Forecast Update" in html
    
    def test_generate_html_report_formats_currency(self, reporter):
        """Test that currency formatting works in template"""
        data = {
            "report_date": "January 18, 2026",
            "top_signals": [],
            "portfolio_summary": {
                "total_value": 123456,
                "total_return_pct": 25.5,
                "total_return_pct_24h": 2.3
            },
            "forecast_summary": {
                "age_31_super_bull": 150000,
                "age_41_super_bull": 1200000,
                "age_51_super_bull": 8000000
            },
            "charts": {}
        }
        
        html = reporter._generate_html_report(data)
        
        # Should format with commas
        assert "€123,456" in html or "123456" in html
    
    # ========== Test Email Sending ==========
    
    @patch("smtplib.SMTP")
    @patch.dict("os.environ", {
        "SMTP_HOST": "smtp.test.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "test@test.com",
        "SMTP_PASSWORD": "testpass"
    })
    def test_send_email_report(self, mock_smtp, reporter):
        """Test sending email report"""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        html_report = "<html><body>Test Report</body></html>"
        
        reporter._send_email_report("recipient@test.com", html_report)
        
        # Verify SMTP was called correctly
        mock_smtp.assert_called_once_with("smtp.test.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@test.com", "testpass")
        mock_server.sendmail.assert_called_once()
    
    @patch.dict("os.environ", {}, clear=True)
    def test_send_email_report_missing_config(self, reporter):
        """Test that missing SMTP config raises error"""
        html_report = "<html><body>Test Report</body></html>"
        
        with pytest.raises(ValueError, match="SMTP configuration"):
            reporter._send_email_report("recipient@test.com", html_report)
    
    # ========== Test Execute Method ==========
    
    @patch("smtplib.SMTP")
    @patch.dict("os.environ", {
        "SMTP_HOST": "smtp.test.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "test@test.com",
        "SMTP_PASSWORD": "testpass",
        "SMTP_RECIPIENT": "default@test.com"
    })
    def test_execute_success_with_email(self, mock_smtp, reporter):
        """Test successful execution with email sending"""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        result = reporter.execute({
            "send_email": True,
            "days_back": 7
        })
        
        assert result["success"] is True
        assert "sent to" in result["message"]
        assert len(result["html_report"]) > 0
        mock_server.sendmail.assert_called_once()
    
    def test_execute_success_without_email(self, reporter):
        """Test successful execution without email sending"""
        result = reporter.execute({
            "send_email": False,
            "days_back": 7
        })
        
        assert result["success"] is True
        assert "email not sent" in result["message"]
        assert len(result["html_report"]) > 0
    
    @patch.dict("os.environ", {"SMTP_RECIPIENT": "default@test.com"})
    def test_execute_uses_default_recipient(self, reporter):
        """Test that execute uses default recipient from env"""
        with patch.object(reporter, "_send_email_report") as mock_send:
            result = reporter.execute({
                "send_email": True
            })
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][0] == "default@test.com"
    
    def test_execute_custom_recipient(self, reporter):
        """Test that execute can use custom recipient"""
        with patch.object(reporter, "_send_email_report") as mock_send:
            result = reporter.execute({
                "send_email": True,
                "recipient_email": "custom@test.com"
            })
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][0] == "custom@test.com"
    
    def test_execute_handles_errors(self, reporter):
        """Test that execute handles errors gracefully"""
        with patch.object(reporter, "_gather_report_data", side_effect=Exception("Test error")):
            result = reporter.execute({})
            
            assert result["success"] is False
            assert "error" in result
            assert "Test error" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
