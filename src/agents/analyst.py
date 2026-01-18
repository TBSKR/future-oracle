"""
Analyst Agent - Deep Alpha Investment Analyst

Uses Grok 4 to generate deep investment insights from Scout signals.
Produces impact scores, price predictions, risk flags, and long-term scenarios.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base import BaseAgent
from core.grok_client import GrokClient


class AnalystAgent(BaseAgent):
    """
    Analyst Agent: Deep Alpha Investment Analyst
    
    Takes Scout signals and generates Grok-powered investment analysis
    with impact scoring, price predictions, and scenario modeling.
    """
    
    def __init__(self, grok_client: Optional[GrokClient] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name="Analyst",
            role="Deep Alpha Investment Analyst",
            goal="Generate deep investment insights and impact predictions using Grok 4",
            backstory="""You are a sharp, optimistic-realistic investment analyst focused on 
            exponential technologies (AI, humanoids, longevity). You rate impact, predict price 
            movements, flag risks, and model long-term scenarios. You stay grounded in evidence 
            while thinking in decades.""",
            config=config or {}
        )
        
        # Initialize Grok client
        try:
            self.grok = grok_client or GrokClient()
            self.grok_available = True
            self.logger.info("Grok client initialized successfully")
        except Exception as e:
            self.grok = None
            self.grok_available = False
            self.logger.warning(f"Grok client unavailable: {e}")
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Analyst Agent workflow.
        
        Args:
            context: Dictionary with:
                - articles: List of Scout signal dictionaries
                - max_analyses: Maximum number of articles to analyze (default: 5)
        
        Returns:
            Dictionary with analyzed articles
        """
        try:
            articles = context.get("articles", [])
            max_analyses = context.get("max_analyses", 5)
            
            if not articles:
                self.logger.warning("No articles provided for analysis")
                return {
                    "success": True,
                    "analyses": [],
                    "total_analyzed": 0,
                    "timestamp": datetime.now().isoformat(),
                    "agent": self.name
                }
            
            # Limit to top N articles by relevance score
            articles_to_analyze = sorted(
                articles, 
                key=lambda x: x.get("relevance_score", 0), 
                reverse=True
            )[:max_analyses]
            
            self.logger.info(f"Analyzing top {len(articles_to_analyze)} articles")
            
            # Analyze each article
            analyses = []
            for article in articles_to_analyze:
                try:
                    analysis = self._analyze_article(article)
                    analyses.append(analysis)
                except Exception as e:
                    self.logger.error(f"Failed to analyze article '{article.get('title', 'Unknown')}': {e}")
                    # Add fallback analysis
                    analyses.append(self._create_fallback_analysis(article, str(e)))
            
            result = {
                "success": True,
                "analyses": analyses,
                "total_analyzed": len(analyses),
                "grok_available": self.grok_available,
                "timestamp": datetime.now().isoformat(),
                "agent": self.name
            }
            
            self.log_execution(context, result)
            return result
            
        except Exception as e:
            return self.handle_error(e, context)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception)
    )
    def _analyze_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single article using Grok.
        
        Args:
            article: Scout signal dictionary
        
        Returns:
            Analysis dictionary with structured output
        """
        if not self.grok_available:
            return self._create_fallback_analysis(article, "Grok API unavailable")
        
        # Build analysis prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(article)
        
        # Call Grok API
        try:
            response = self.grok.analyze_with_prompt(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=800
            )
            
            # Parse response into structured format
            parsed = self._parse_grok_response(response, article)
            
            self.logger.info(f"Analyzed: {article.get('title', 'Unknown')} - Impact: {parsed['impact_score']}/10")
            
            return parsed
            
        except Exception as e:
            self.logger.error(f"Grok API call failed: {e}")
            raise
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for Grok"""
        return """You are a sharp, optimistic-realistic investment analyst focused on exponential technologies: 
AI, humanoid robotics, longevity biotech, and semiconductors.

Your analysis style:
- Rate breakthrough impact on a scale of 1-10 (10 = civilization-changing)
- Predict short-term price impact (30-day outlook)
- Flag key risks that could invalidate the thesis
- Model long-term scenarios (5yr, 10yr, 20yr upside)
- Stay grounded in evidence while thinking in decades
- Be concise but insightful

Always provide:
1. Impact Score (1-10)
2. Sentiment (bullish/neutral/bearish)
3. 30-day price outlook
4. Key insight (1-2 sentences)
5. Risk flags (2-3 bullet points)
6. Long-term scenarios (brief)"""
    
    def _build_user_prompt(self, article: Dict[str, Any]) -> str:
        """Build user prompt for specific article"""
        title = article.get("title", "Unknown")
        description = article.get("description", "No description")
        source = article.get("source", "Unknown")
        keywords = ", ".join(article.get("matched_keywords", [])[:5])
        categories = ", ".join(article.get("matched_categories", [])[:3])
        
        return f"""Analyze this breakthrough signal for investment implications:

**Title:** {title}
**Source:** {source}
**Summary:** {description}
**Matched Keywords:** {keywords}
**Categories:** {categories}

Provide your analysis in this format:

IMPACT SCORE: [1-10]
SENTIMENT: [bullish/neutral/bearish]
30-DAY OUTLOOK: [brief price prediction]
KEY INSIGHT: [1-2 sentence takeaway]
RISKS:
- [Risk 1]
- [Risk 2]
SCENARIOS:
- 5yr: [brief upside]
- 10yr: [brief upside]
- 20yr: [brief upside]"""
    
    def _parse_grok_response(self, response: str, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Grok's text response into structured format.
        
        Args:
            response: Raw Grok response text
            article: Original article data
        
        Returns:
            Structured analysis dictionary
        """
        # Extract impact score
        impact_score = self._extract_impact_score(response)
        
        # Extract sentiment
        sentiment = self._extract_sentiment(response)
        
        # Extract 30-day outlook
        price_target_30d = self._extract_section(response, "30-DAY OUTLOOK", "KEY INSIGHT")
        
        # Extract key insight
        key_insight = self._extract_section(response, "KEY INSIGHT", "RISKS")
        
        # Extract risks
        risks = self._extract_list_items(response, "RISKS:", "SCENARIOS:")
        
        # Extract scenarios
        scenarios = self._extract_scenarios(response)
        
        # Build structured output
        analysis = {
            "article_title": article.get("title"),
            "article_url": article.get("url"),
            "article_source": article.get("source"),
            "relevance_score": article.get("relevance_score", 0),
            "impact_score": impact_score,
            "sentiment": sentiment,
            "price_target_30d": price_target_30d.strip() if price_target_30d else "No prediction",
            "key_insight": key_insight.strip() if key_insight else "Analysis pending",
            "risks": risks,
            "scenarios": scenarios,
            "raw_analysis": response,
            "analyzed_at": datetime.now().isoformat(),
            "grok_model": self.grok.model if self.grok else "N/A"
        }
        
        return analysis
    
    def _extract_impact_score(self, text: str) -> int:
        """Extract impact score from response"""
        try:
            # Look for "IMPACT SCORE: X" or "Impact: X/10"
            match = re.search(r'IMPACT\s*SCORE[:\s]+(\d+)', text, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                return max(1, min(10, score))  # Clamp to 1-10
            
            # Fallback: look for X/10 pattern
            match = re.search(r'(\d+)\s*/\s*10', text)
            if match:
                score = int(match.group(1))
                return max(1, min(10, score))
            
            # Default to 5 if not found
            self.logger.warning("Could not extract impact score, defaulting to 5")
            return 5
        except Exception as e:
            self.logger.error(f"Error extracting impact score: {e}")
            return 5
    
    def _extract_sentiment(self, text: str) -> str:
        """Extract sentiment from response"""
        text_lower = text.lower()
        
        if "sentiment: bullish" in text_lower or "bullish" in text_lower[:200]:
            return "bullish"
        elif "sentiment: bearish" in text_lower or "bearish" in text_lower[:200]:
            return "bearish"
        elif "sentiment: neutral" in text_lower or "neutral" in text_lower[:200]:
            return "neutral"
        
        # Default based on common positive/negative words
        if any(word in text_lower for word in ["breakthrough", "revolutionary", "game-changing", "massive"]):
            return "bullish"
        elif any(word in text_lower for word in ["concern", "risk", "challenge", "uncertain"]):
            return "neutral"
        
        return "neutral"
    
    def _extract_section(self, text: str, start_marker: str, end_marker: str) -> Optional[str]:
        """Extract text between two markers"""
        try:
            start_idx = text.find(start_marker)
            if start_idx == -1:
                return None
            
            start_idx += len(start_marker)
            
            if end_marker:
                end_idx = text.find(end_marker, start_idx)
                if end_idx == -1:
                    # Take rest of text
                    section = text[start_idx:].strip()
                else:
                    section = text[start_idx:end_idx].strip()
            else:
                # No end marker, take rest of text
                section = text[start_idx:].strip()
            
            # Clean up
            section = section.lstrip(':').strip()
            return section if section else None
            
        except Exception as e:
            self.logger.error(f"Error extracting section {start_marker}: {e}")
            return None
    
    def _extract_list_items(self, text: str, start_marker: str, end_marker: str) -> List[str]:
        """Extract bullet point list items"""
        try:
            section = self._extract_section(text, start_marker, end_marker)
            if not section:
                return []
            
            # Split by newlines and filter for bullet points
            lines = section.split('\n')
            items = []
            
            for line in lines:
                line = line.strip()
                # Match lines starting with -, *, •, or numbers
                if line and (line.startswith('-') or line.startswith('*') or line.startswith('•') or re.match(r'^\d+\.', line)):                    # Remove bullet point markers
                    item = re.sub(r'^[-*•]\s*', '', line).strip()
                    item = re.sub(r'^\d+\.\s*', '', item).strip()
                    if item:
                        items.append(item)
            
            return items[:5]  # Limit to 5 items
            
        except Exception as e:
            self.logger.error(f"Error extracting list items: {e}")
            return []
    
    def _extract_scenarios(self, text: str) -> Dict[str, str]:
        """Extract scenario predictions"""
        scenarios = {}
        
        try:
            # Look for SCENARIOS section
            scenarios_text = self._extract_section(text, "SCENARIOS:", "")
            if not scenarios_text:
                return {"5yr": "N/A", "10yr": "N/A", "20yr": "N/A"}
            
            # Extract each timeframe
            for timeframe in ["5yr", "10yr", "20yr"]:
                # Try multiple patterns
                patterns = [
                    rf'-\s*{timeframe}[:\s]+([^\n]+)',  # Dash format: - 5yr: text
                    rf'{timeframe}[:\s]+([^\n]+)',      # Direct format: 5yr: text
                ]
                
                found = False
                for pattern in patterns:
                    match = re.search(pattern, scenarios_text, re.IGNORECASE)
                    if match:
                        scenarios[timeframe] = match.group(1).strip()
                        found = True
                        break
                
                if not found:
                    scenarios[timeframe] = "N/A"
            
            return scenarios
            
        except Exception as e:
            self.logger.error(f"Error extracting scenarios: {e}")
            return {"5yr": "N/A", "10yr": "N/A", "20yr": "N/A"}
    
    def _create_fallback_analysis(self, article: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
        """
        Create fallback analysis when Grok API fails.
        
        Args:
            article: Original article data
            error_msg: Error message
        
        Returns:
            Basic analysis dictionary
        """
        # Use relevance score as proxy for impact
        relevance = article.get("relevance_score", 5)
        impact_score = min(10, max(1, relevance))
        
        # Determine sentiment from keywords
        keywords = [k.lower() for k in article.get("matched_keywords", [])]
        sentiment = "neutral"
        if any(word in keywords for word in ["breakthrough", "revolutionary", "success", "approval"]):
            sentiment = "bullish"
        
        return {
            "article_title": article.get("title"),
            "article_url": article.get("url"),
            "article_source": article.get("source"),
            "relevance_score": relevance,
            "impact_score": impact_score,
            "sentiment": sentiment,
            "price_target_30d": "Analysis unavailable",
            "key_insight": f"High-relevance signal ({relevance}/10) - Grok analysis pending",
            "risks": ["API unavailable - manual review recommended"],
            "scenarios": {"5yr": "N/A", "10yr": "N/A", "20yr": "N/A"},
            "raw_analysis": f"Fallback analysis (Grok unavailable: {error_msg})",
            "analyzed_at": datetime.now().isoformat(),
            "grok_model": "fallback",
            "is_fallback": True
        }
    
    def get_high_impact_signals(self, analyses: List[Dict[str, Any]], threshold: int = 8) -> List[Dict[str, Any]]:
        """
        Filter analyses for high-impact signals.
        
        Args:
            analyses: List of analysis dictionaries
            threshold: Minimum impact score (default: 8)
        
        Returns:
            List of high-impact analyses
        """
        return [a for a in analyses if a.get("impact_score", 0) >= threshold]
