"""
Unit Tests for Forecaster Agent

Tests scenario calculations, Grok parsing, fallback behavior, and error handling.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.forecaster import ForecasterAgent


class TestForecasterAgent:
    """Test suite for Forecaster Agent"""
    
    @pytest.fixture
    def mock_grok_client(self):
        """Mock Grok client for testing"""
        mock = Mock()
        mock.model = "grok-beta"
        mock.analyze_with_prompt = Mock(return_value="Test response")
        return mock
    
    @pytest.fixture
    def forecaster(self, mock_grok_client):
        """Create Forecaster instance with mocked Grok"""
        return ForecasterAgent(grok_client=mock_grok_client)
    
    @pytest.fixture
    def sample_grok_response(self):
        """Sample Grok API response"""
        return """
BASE CASE: €150,000
Rationale: Conservative growth with steady AI adoption

BULL CASE: €350,000
Rationale: Strong tech sector performance and market expansion

SUPER-BULL CASE: €750,000
Rationale: Exponential breakthrough in AI/robotics/longevity

KEY ASSUMPTIONS:
- AI infrastructure continues exponential growth
- Humanoid robotics reaches commercial scale
- Longevity biotech achieves major breakthroughs
        """
    
    # ========== Test Euro Amount Parsing ==========
    
    def test_parse_euro_amount_standard(self, forecaster):
        """Test parsing standard euro amount"""
        assert forecaster._parse_euro_amount("150000") == 150000
        assert forecaster._parse_euro_amount("1500") == 1500
    
    def test_parse_euro_amount_with_commas(self, forecaster):
        """Test parsing euro amount with commas"""
        assert forecaster._parse_euro_amount("150,000") == 150000
        assert forecaster._parse_euro_amount("1,500,000") == 1500000
    
    def test_parse_euro_amount_with_k_suffix(self, forecaster):
        """Test parsing euro amount with K suffix"""
        assert forecaster._parse_euro_amount("150K") == 150000
        assert forecaster._parse_euro_amount("15k") == 15000
    
    def test_parse_euro_amount_with_m_suffix(self, forecaster):
        """Test parsing euro amount with M suffix"""
        assert forecaster._parse_euro_amount("1.5M") == 1500000
        assert forecaster._parse_euro_amount("2m") == 2000000
    
    def test_parse_euro_amount_invalid(self, forecaster):
        """Test parsing invalid euro amount returns 0"""
        assert forecaster._parse_euro_amount("invalid") == 0
        assert forecaster._parse_euro_amount("") == 0
    
    # ========== Test Grok Forecast Parsing ==========
    
    def test_parse_grok_forecast_complete(self, forecaster, sample_grok_response):
        """Test parsing complete Grok response"""
        parsed = forecaster._parse_grok_forecast(sample_grok_response, target_age=31, years_ahead=10)
        
        assert parsed is not None
        assert parsed["target_age"] == 31
        assert parsed["years_ahead"] == 10
        assert parsed["base_case"] == 150000
        assert parsed["bull_case"] == 350000
        assert parsed["super_bull_case"] == 750000
        assert "Conservative growth" in parsed["base_rationale"]
        assert "Strong tech sector" in parsed["bull_rationale"]
        assert "Exponential breakthrough" in parsed["super_bull_rationale"]
        assert len(parsed["key_assumptions"]) == 3
        assert parsed["is_grok"] is True
    
    def test_parse_grok_forecast_missing_amounts(self, forecaster):
        """Test parsing Grok response with missing amounts returns None"""
        incomplete_response = """
BASE CASE: Conservative growth
BULL CASE: Strong growth
SUPER-BULL CASE: Exponential growth
        """
        parsed = forecaster._parse_grok_forecast(incomplete_response, target_age=31, years_ahead=10)
        assert parsed is None
    
    def test_parse_grok_forecast_partial_rationales(self, forecaster):
        """Test parsing with missing rationales (amounts are enough)"""
        response = """
BASE CASE: €100,000
BULL CASE: €250,000
SUPER-BULL CASE: €500,000
        """
        parsed = forecaster._parse_grok_forecast(response, target_age=31, years_ahead=10)
        
        assert parsed is not None
        assert parsed["base_case"] == 100000
        assert parsed["bull_case"] == 250000
        assert parsed["super_bull_case"] == 500000
        assert parsed["base_rationale"] == ""  # Missing rationale
    
    # ========== Test Static Forecast Calculation ==========
    
    def test_static_forecast_calculation(self, forecaster):
        """Test static forecast calculation"""
        forecast = forecaster._generate_static_forecast(
            target_age=31,
            years_ahead=10,
            current_value=10000,
            monthly_contribution=300,
            annual_bonus=1000,
            total_contributions=47000  # 10000 + (300*12*10) + (1000*10)
        )
        
        assert forecast["target_age"] == 31
        assert forecast["years_ahead"] == 10
        assert forecast["base_case"] > 0
        assert forecast["bull_case"] > forecast["base_case"]
        assert forecast["super_bull_case"] > forecast["bull_case"]
        assert forecast["is_grok"] is False
        assert len(forecast["key_assumptions"]) == 3
    
    def test_static_forecast_zero_starting_value(self, forecaster):
        """Test static forecast with zero starting value"""
        forecast = forecaster._generate_static_forecast(
            target_age=31,
            years_ahead=10,
            current_value=0,
            monthly_contribution=300,
            annual_bonus=1000,
            total_contributions=37000  # (300*12*10) + (1000*10)
        )
        
        assert forecast["base_case"] > 0
        assert forecast["bull_case"] > 0
        assert forecast["super_bull_case"] > 0
    
    # ========== Test Compound Growth Calculation ==========
    
    def test_calculate_compound_growth_basic(self, forecaster):
        """Test basic compound growth calculation"""
        result = forecaster._calculate_compound_growth(
            current_value=10000,
            monthly_contribution=0,
            annual_bonus=0,
            early_years=10,
            early_rate=0.50,  # 50% annual
            later_years=0,
            later_rate=0
        )
        
        # 10000 * (1.5)^10 ≈ 576,650
        assert result > 500000
        assert result < 600000
    
    def test_calculate_compound_growth_with_contributions(self, forecaster):
        """Test compound growth with monthly contributions"""
        result = forecaster._calculate_compound_growth(
            current_value=0,
            monthly_contribution=300,
            annual_bonus=1000,
            early_years=5,
            early_rate=0.50,
            later_years=5,
            later_rate=0.30
        )
        
        # Should be significantly higher than total contributions (50k)
        assert result > 50000
        assert result > 100000  # Growth should more than double contributions
    
    def test_calculate_compound_growth_two_phases(self, forecaster):
        """Test compound growth with early and later phases"""
        result = forecaster._calculate_compound_growth(
            current_value=10000,
            monthly_contribution=300,
            annual_bonus=1000,
            early_years=5,
            early_rate=0.60,
            later_years=5,
            later_rate=0.35
        )
        
        assert result > 10000  # Must be greater than starting value
        assert result > 50000  # Should include growth
    
    # ========== Test Execute Method ==========
    
    def test_execute_success(self, forecaster, mock_grok_client):
        """Test successful execution"""
        mock_grok_client.analyze_with_prompt.return_value = """
BASE CASE: €150,000
BULL CASE: €350,000
SUPER-BULL CASE: €750,000
        """
        
        result = forecaster.execute({
            "current_age": 21,
            "current_value": 10000,
            "monthly_contribution": 300,
            "annual_bonus": 1000,
            "target_ages": [31, 41]
        })
        
        assert result["success"] is True
        assert result["grok_available"] is True
        assert len(result["forecasts"]) == 2
        assert result["forecasts"][0]["target_age"] == 31
        assert result["forecasts"][1]["target_age"] == 41
        assert "summary" in result
    
    def test_execute_defaults(self, forecaster):
        """Test execution with default values"""
        result = forecaster.execute({})
        
        assert result["success"] is True
        assert len(result["forecasts"]) == 3  # Default: [31, 41, 51]
        assert result["forecasts"][0]["target_age"] == 31
    
    def test_execute_filters_past_ages(self, forecaster):
        """Test that past target ages are filtered out"""
        result = forecaster.execute({
            "current_age": 35,
            "target_ages": [31, 41, 51]  # 31 is in the past
        })
        
        assert result["success"] is True
        assert len(result["forecasts"]) == 2  # Only 41 and 51
        assert result["forecasts"][0]["target_age"] == 41
    
    def test_execute_no_grok_uses_fallback(self, forecaster):
        """Test that execution uses fallback when Grok unavailable"""
        forecaster_no_grok = ForecasterAgent(grok_client=None)
        
        result = forecaster_no_grok.execute({
            "current_age": 21,
            "target_ages": [31]
        })
        
        assert result["success"] is True
        assert result["grok_available"] is False
        assert len(result["forecasts"]) == 1
        assert result["forecasts"][0]["is_grok"] is False
    
    # ========== Test Summary Generation ==========
    
    def test_generate_summary(self, forecaster):
        """Test summary generation"""
        forecasts = [
            {
                "target_age": 31,
                "years_ahead": 10,
                "base_case": 100000,
                "super_bull_case": 300000
            },
            {
                "target_age": 51,
                "years_ahead": 30,
                "base_case": 1000000,
                "super_bull_case": 5000000
            }
        ]
        
        summary = forecaster._generate_summary(forecasts, current_age=21)
        
        assert "age 21" in summary.lower()
        assert "age 31" in summary
        assert "300,000" in summary or "300000" in summary
        assert "age 51" in summary
        assert "5,000,000" in summary or "5000000" in summary
    
    def test_generate_summary_empty_forecasts(self, forecaster):
        """Test summary with no forecasts"""
        summary = forecaster._generate_summary([], current_age=21)
        assert "No forecasts" in summary
    
    # ========== Test Section Extraction ==========
    
    def test_extract_section_standard(self, forecaster):
        """Test extracting text between markers"""
        text = """
BASE CASE: €150,000
Rationale: Conservative growth
BULL CASE: €350,000
        """
        section = forecaster._extract_section(text, "BASE CASE:", "BULL CASE:")
        assert section is not None
        assert "150,000" in section
        assert "Conservative growth" in section
    
    def test_extract_section_to_end(self, forecaster):
        """Test extracting section to end of text"""
        text = "KEY ASSUMPTIONS: AI growth, robotics, longevity"
        section = forecaster._extract_section(text, "KEY ASSUMPTIONS:", "")
        assert section is not None
        assert "AI growth" in section
    
    def test_extract_section_missing(self, forecaster):
        """Test extraction when marker not found"""
        text = "No markers here"
        section = forecaster._extract_section(text, "BASE CASE:", "BULL CASE:")
        assert section is None
    
    # ========== Test List Extraction ==========
    
    def test_extract_list_items_dashes(self, forecaster):
        """Test extracting bullet points with dashes"""
        text = """
- AI infrastructure growth
- Humanoid robotics scale
- Longevity breakthroughs
        """
        items = forecaster._extract_list_items(text)
        assert len(items) == 3
        assert "AI infrastructure" in items[0]
        assert "Humanoid robotics" in items[1]
        assert "Longevity breakthroughs" in items[2]
    
    def test_extract_list_items_asterisks(self, forecaster):
        """Test extracting bullet points with asterisks"""
        text = """
* Item one
* Item two
        """
        items = forecaster._extract_list_items(text)
        assert len(items) == 2
    
    def test_extract_list_items_numbered(self, forecaster):
        """Test extracting numbered list"""
        text = """
1. First item
2. Second item
3. Third item
        """
        items = forecaster._extract_list_items(text)
        assert len(items) == 3
        assert "First item" in items[0]
        assert "Second item" in items[1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
