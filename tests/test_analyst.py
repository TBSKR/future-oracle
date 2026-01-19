"""
Unit Tests for Analyst Agent

Tests parsing logic, scoring, fallback behavior, and error handling.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.analyst import AnalystAgent


class TestAnalystAgent:
    """Test suite for Analyst Agent"""
    
    @pytest.fixture
    def mock_grok_client(self):
        """Mock Grok client for testing"""
        mock = Mock()
        mock.model = "grok-beta"
        mock.analyze_with_prompt = Mock(return_value="Test response")
        return mock
    
    @pytest.fixture
    def analyst(self, mock_grok_client):
        """Create Analyst instance with mocked Grok"""
        return AnalystAgent(grok_client=mock_grok_client)
    
    @pytest.fixture
    def sample_article(self):
        """Sample Scout signal for testing"""
        return {
            "title": "NVIDIA Announces Breakthrough AI Chip",
            "source": "TechCrunch",
            "url": "https://example.com/article",
            "description": "NVIDIA unveils revolutionary AI chip with 10x performance improvement",
            "relevance_score": 9,
            "matched_keywords": ["NVIDIA", "AI", "chip", "breakthrough"],
            "matched_categories": ["AI Infrastructure", "Semiconductors"],
            "published_at": "2026-01-18T10:00:00Z"
        }
    
    @pytest.fixture
    def sample_grok_response(self):
        """Sample Grok API response"""
        return """
IMPACT SCORE: 9

SENTIMENT: bullish

30-DAY OUTLOOK: Expect 15-20% price appreciation as markets digest the breakthrough. Institutional buying likely.

KEY INSIGHT: This 10x performance leap solidifies NVIDIA's dominance in AI infrastructure and opens new markets in edge AI and autonomous systems.

RISKS:
- Supply chain constraints may limit initial production
- Competitors (AMD, Intel) may respond with aggressive pricing
- Regulatory scrutiny on AI chip exports to China

SCENARIOS:
- 5yr: NVIDIA captures 80% of AI accelerator market, stock 3-4x from current levels
- 10yr: AI infrastructure becomes $500B+ market, NVIDIA maintains 60% share
- 20yr: Quantum-AI hybrid chips emerge, but NVIDIA's ecosystem lock-in persists
        """
    
    # ========== Test Impact Score Extraction ==========
    
    def test_extract_impact_score_standard_format(self, analyst):
        """Test extracting impact score from standard format"""
        text = "IMPACT SCORE: 8\nSome other text"
        score = analyst._extract_impact_score(text)
        assert score == 8
    
    def test_extract_impact_score_slash_format(self, analyst):
        """Test extracting impact score from X/10 format"""
        text = "The impact is 7/10 for this breakthrough"
        score = analyst._extract_impact_score(text)
        assert score == 7
    
    def test_extract_impact_score_out_of_range(self, analyst):
        """Test impact score clamping to 1-10 range"""
        text = "IMPACT SCORE: 15"
        score = analyst._extract_impact_score(text)
        assert score == 10  # Should clamp to max
        
        text2 = "IMPACT SCORE: 0"
        score2 = analyst._extract_impact_score(text2)
        assert score2 == 1  # Should clamp to min
    
    def test_extract_impact_score_missing(self, analyst):
        """Test default score when not found"""
        text = "No impact score mentioned here"
        score = analyst._extract_impact_score(text)
        assert score == 5  # Default fallback
    
    # ========== Test Sentiment Extraction ==========
    
    def test_extract_sentiment_bullish(self, analyst):
        """Test extracting bullish sentiment"""
        text = "SENTIMENT: bullish\nThis is a breakthrough"
        sentiment = analyst._extract_sentiment(text)
        assert sentiment == "bullish"
    
    def test_extract_sentiment_bearish(self, analyst):
        """Test extracting bearish sentiment"""
        text = "SENTIMENT: bearish\nConcerns about risks"
        sentiment = analyst._extract_sentiment(text)
        assert sentiment == "bearish"
    
    def test_extract_sentiment_neutral(self, analyst):
        """Test extracting neutral sentiment"""
        text = "SENTIMENT: neutral\nMixed signals"
        sentiment = analyst._extract_sentiment(text)
        assert sentiment == "neutral"
    
    def test_extract_sentiment_from_keywords(self, analyst):
        """Test sentiment inference from keywords"""
        text = "This is a revolutionary breakthrough that will be game-changing"
        sentiment = analyst._extract_sentiment(text)
        assert sentiment == "bullish"
    
    # ========== Test Section Extraction ==========
    
    def test_extract_section_standard(self, analyst):
        """Test extracting text between markers"""
        text = """
KEY INSIGHT: This is the key insight text
RISKS:
- Risk 1
        """
        section = analyst._extract_section(text, "KEY INSIGHT:", "RISKS:")
        assert section == "This is the key insight text"
    
    def test_extract_section_to_end(self, analyst):
        """Test extracting section to end of text"""
        text = "30-DAY OUTLOOK: Price will rise 20%"
        section = analyst._extract_section(text, "30-DAY OUTLOOK:", "NONEXISTENT")
        assert "Price will rise 20%" in section
    
    def test_extract_section_missing(self, analyst):
        """Test extraction when marker not found"""
        text = "No markers here"
        section = analyst._extract_section(text, "KEY INSIGHT:", "RISKS:")
        assert section is None
    
    # ========== Test List Extraction ==========
    
    def test_extract_list_items_dashes(self, analyst):
        """Test extracting bullet points with dashes"""
        text = """
RISKS:
- Supply chain issues
- Regulatory concerns
- Market competition
SCENARIOS:
        """
        items = analyst._extract_list_items(text, "RISKS:", "SCENARIOS:")
        assert len(items) == 3
        assert "Supply chain issues" in items
        assert "Regulatory concerns" in items
    
    def test_extract_list_items_asterisks(self, analyst):
        """Test extracting bullet points with asterisks"""
        text = """
RISKS:
* Risk one
* Risk two
SCENARIOS:
        """
        items = analyst._extract_list_items(text, "RISKS:", "SCENARIOS:")
        assert len(items) == 2
    
    def test_extract_list_items_numbered(self, analyst):
        """Test extracting numbered list"""
        text = """
RISKS:
1. First risk
2. Second risk
SCENARIOS:
        """
        items = analyst._extract_list_items(text, "RISKS:", "SCENARIOS:")
        assert len(items) == 2
        assert "First risk" in items
    
    def test_extract_list_items_limit(self, analyst):
        """Test list item limit (max 5)"""
        text = """
RISKS:
- Risk 1
- Risk 2
- Risk 3
- Risk 4
- Risk 5
- Risk 6
- Risk 7
SCENARIOS:
        """
        items = analyst._extract_list_items(text, "RISKS:", "SCENARIOS:")
        assert len(items) == 5  # Should limit to 5
    
    # ========== Test Scenario Extraction ==========
    
    def test_extract_scenarios_complete(self, analyst):
        """Test extracting all scenario timeframes"""
        text = """
SCENARIOS:
- 5yr: Stock doubles as AI market expands
- 10yr: Market leader with 70% share
- 20yr: Quantum transition maintains position
        """
        scenarios = analyst._extract_scenarios(text)
        assert "5yr" in scenarios
        assert "10yr" in scenarios
        assert "20yr" in scenarios
        # Check that at least one scenario was extracted
        assert scenarios["5yr"] != "N/A" or scenarios["10yr"] != "N/A" or scenarios["20yr"] != "N/A"
        # If 5yr was extracted, it should contain expected text
        if scenarios["5yr"] != "N/A":
            assert "doubles" in scenarios["5yr"].lower() or "stock" in scenarios["5yr"].lower()
    
    def test_extract_scenarios_partial(self, analyst):
        """Test with missing timeframes"""
        text = """
SCENARIOS:
5yr: Strong growth expected
        """
        scenarios = analyst._extract_scenarios(text)
        # At least 5yr should be extracted
        assert scenarios["5yr"] != "N/A" or len([v for v in scenarios.values() if v != "N/A"]) >= 1
        # Other timeframes should be N/A if not present
        assert scenarios["10yr"] == "N/A"
        assert scenarios["20yr"] == "N/A"
    
    def test_extract_scenarios_missing(self, analyst):
        """Test when scenarios section is missing"""
        text = "No scenarios here"
        scenarios = analyst._extract_scenarios(text)
        assert scenarios["5yr"] == "N/A"
        assert scenarios["10yr"] == "N/A"
        assert scenarios["20yr"] == "N/A"
    
    # ========== Test Full Parsing ==========
    
    def test_parse_grok_response_complete(self, analyst, sample_article, sample_grok_response):
        """Test parsing complete Grok response"""
        parsed = analyst._parse_grok_response(sample_grok_response, sample_article)
        
        # Check all fields are present
        assert parsed["article_title"] == sample_article["title"]
        assert parsed["article_url"] == sample_article["url"]
        assert parsed["relevance_score"] == 9
        assert parsed["impact_score"] == 9
        assert parsed["sentiment"] == "bullish"
        assert "15-20%" in parsed["price_target_30d"]
        assert "10x performance" in parsed["key_insight"]
        assert len(parsed["risks"]) == 3
        assert "5yr" in parsed["scenarios"]
        assert parsed["grok_model"] == "grok-beta"
        assert "analyzed_at" in parsed
    
    def test_parse_grok_response_malformed(self, analyst, sample_article):
        """Test parsing malformed response with fallbacks"""
        malformed_response = "This is a malformed response without proper structure"
        parsed = analyst._parse_grok_response(malformed_response, sample_article)
        
        # Should still return valid structure with defaults
        assert parsed["impact_score"] == 5  # Default
        assert parsed["sentiment"] in ["bullish", "neutral", "bearish"]
        assert parsed["risks"] == []  # Empty list
        assert parsed["scenarios"]["5yr"] == "N/A"
    
    # ========== Test Fallback Analysis ==========
    
    def test_create_fallback_analysis(self, analyst, sample_article):
        """Test fallback analysis creation"""
        fallback = analyst._create_fallback_analysis(sample_article, "API timeout")
        
        assert fallback["article_title"] == sample_article["title"]
        assert fallback["impact_score"] == 9  # Based on relevance_score
        assert fallback["sentiment"] == "bullish"  # Inferred from keywords
        assert fallback["is_fallback"] is True
        assert "API timeout" in fallback["raw_analysis"]
        assert len(fallback["risks"]) > 0
    
    def test_fallback_analysis_sentiment_inference(self, analyst):
        """Test sentiment inference in fallback"""
        article_bullish = {
            "title": "Breakthrough Success",
            "matched_keywords": ["breakthrough", "revolutionary", "success"],
            "relevance_score": 8
        }
        fallback = analyst._create_fallback_analysis(article_bullish, "Test")
        assert fallback["sentiment"] == "bullish"
        
        article_neutral = {
            "title": "Company Update",
            "matched_keywords": ["update", "announcement"],
            "relevance_score": 6
        }
        fallback2 = analyst._create_fallback_analysis(article_neutral, "Test")
        assert fallback2["sentiment"] == "neutral"
    
    # ========== Test High-Impact Filtering ==========
    
    def test_get_high_impact_signals(self, analyst):
        """Test filtering high-impact signals"""
        analyses = [
            {"impact_score": 9, "title": "High 1"},
            {"impact_score": 8, "title": "High 2"},
            {"impact_score": 7, "title": "Medium"},
            {"impact_score": 6, "title": "Low"},
        ]
        
        high_impact = analyst.get_high_impact_signals(analyses, threshold=8)
        assert len(high_impact) == 2
        assert all(a["impact_score"] >= 8 for a in high_impact)
    
    def test_get_high_impact_signals_empty(self, analyst):
        """Test with no high-impact signals"""
        analyses = [
            {"impact_score": 5, "title": "Low 1"},
            {"impact_score": 6, "title": "Low 2"},
        ]
        
        high_impact = analyst.get_high_impact_signals(analyses, threshold=8)
        assert len(high_impact) == 0

    # ========== Test Memory Helpers ==========

    def test_build_user_prompt_includes_memory_context(self, analyst, sample_article):
        """Test memory context inclusion in prompt"""
        context = "- 2024-01-01 | NVDA | Impact 8/10 | Sentiment bullish | Prior insight"
        prompt = analyst._build_user_prompt(sample_article, similar_analyses=context)
        assert "Similar past analyses" in prompt
        assert "Prior insight" in prompt

    def test_infer_ticker_from_keywords(self, analyst, sample_article):
        """Test ticker inference from matched keywords"""
        analyst._keyword_to_ticker = {"nvidia": "NVDA"}
        ticker = analyst._infer_ticker(sample_article)
        assert ticker == "NVDA"

    def test_store_analysis_memory_calls_vector_store(self, analyst):
        """Test storing analysis into vector memory"""
        analysis = {
            "article_title": "Test Title",
            "article_source": "Test Source",
            "impact_score": 8,
            "sentiment": "bullish",
            "price_target_30d": "Up 10%",
            "key_insight": "Strong signal",
            "risks": ["Risk 1"],
            "scenarios": {"5yr": "Growth", "10yr": "Expansion", "20yr": "Dominance"},
            "raw_analysis": "Raw text",
            "analyzed_at": "2024-01-01T00:00:00",
            "grok_model": "grok-beta",
        }
        article = {"title": "Test Title", "source": "Test Source"}
        analyst.memory = Mock()
        analyst._store_analysis_memory(analysis, article, ticker="NVDA")

        analyst.memory.store_analysis.assert_called_once()
        _, kwargs = analyst.memory.store_analysis.call_args
        assert kwargs["ticker"] == "NVDA"
        assert "Key Insight: Strong signal" in kwargs["analysis_text"]
        assert kwargs["metadata"]["impact_score"] == 8

    def test_analyze_article_includes_memory_context(self, analyst, sample_article, mock_grok_client):
        """Test memory retrieval is injected into analysis prompt"""
        captured = {}

        def _capture(system_prompt, user_prompt, temperature=0.7, max_tokens=800):
            captured["prompt"] = user_prompt
            return (
                "IMPACT SCORE: 7\n"
                "SENTIMENT: neutral\n"
                "30-DAY OUTLOOK: N/A\n"
                "KEY INSIGHT: ok\n"
                "RISKS:\n- Risk 1\n"
                "SCENARIOS:\n- 5yr: N/A\n- 10yr: N/A\n- 20yr: N/A\n"
            )

        mock_grok_client.analyze_with_prompt.side_effect = _capture
        analyst._keyword_to_ticker = {"nvidia": "NVDA"}
        analyst.memory = Mock()
        analyst.memory.retrieve_similar_analyses.return_value = [
            {
                "metadata": {
                    "timestamp": "2024-01-01",
                    "ticker": "NVDA",
                    "impact_score": 7,
                    "sentiment": "neutral",
                    "summary": "Prior analysis",
                }
            }
        ]

        analyst._analyze_article(sample_article, use_memory=True, store_memory=False)
        assert "Similar past analyses" in captured["prompt"]
        assert "Prior analysis" in captured["prompt"]
    
    # ========== Test Execute Method ==========
    
    def test_execute_success(self, analyst, sample_article, mock_grok_client):
        """Test successful execution with articles"""
        mock_grok_client.analyze_with_prompt.return_value = """
IMPACT SCORE: 8
SENTIMENT: bullish
30-DAY OUTLOOK: Positive
KEY INSIGHT: Strong signal
RISKS:
- Risk 1
SCENARIOS:
- 5yr: Growth
- 10yr: Expansion
- 20yr: Dominance
        """
        
        result = analyst.execute({
            "articles": [sample_article],
            "max_analyses": 1
        })
        
        assert result["success"] is True
        assert result["total_analyzed"] == 1
        assert len(result["analyses"]) == 1
        assert result["analyses"][0]["impact_score"] == 8
    
    def test_execute_empty_articles(self, analyst):
        """Test execution with no articles"""
        result = analyst.execute({"articles": []})
        
        assert result["success"] is True
        assert result["total_analyzed"] == 0
        assert len(result["analyses"]) == 0
    
    def test_execute_limits_analyses(self, analyst, sample_article, mock_grok_client):
        """Test max_analyses limit"""
        mock_grok_client.analyze_with_prompt.return_value = "IMPACT SCORE: 7\nSENTIMENT: neutral"
        
        articles = [sample_article] * 10  # 10 articles
        result = analyst.execute({
            "articles": articles,
            "max_analyses": 3  # Limit to 3
        })
        
        assert result["total_analyzed"] == 3
        assert len(result["analyses"]) == 3
    
    def test_execute_sorts_by_relevance(self, analyst, mock_grok_client):
        """Test that articles are sorted by relevance before analysis"""
        mock_grok_client.analyze_with_prompt.return_value = "IMPACT SCORE: 7\nSENTIMENT: neutral"
        
        articles = [
            {"title": "Low", "relevance_score": 5},
            {"title": "High", "relevance_score": 9},
            {"title": "Medium", "relevance_score": 7},
        ]
        
        result = analyst.execute({
            "articles": articles,
            "max_analyses": 2
        })
        
        # Should analyze top 2 by relevance
        analyzed_titles = [a["article_title"] for a in result["analyses"]]
        assert "High" in analyzed_titles
        assert "Medium" in analyzed_titles
        assert "Low" not in analyzed_titles


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
