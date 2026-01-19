"""
Scout Agent - Breakthrough Signal Hunter

Monitors news sources (NewsAPI, RSS, X/Twitter) for breakthrough signals
in target categories: humanoid robotics, longevity, AGI, semiconductors.

Filters noise and surfaces only high-relevance items for the Analyst Agent.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import yaml
from pathlib import Path
import re

from .base import BaseAgent
from data.news import NewsAggregator


class ScoutAgent(BaseAgent):
    """
    Scout Agent: Breakthrough Signal Hunter
    
    Scans news sources and filters for breakthrough signals matching
    the watchlist and breakthrough keywords.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # Load watchlist configuration
        config_path = Path(__file__).parent.parent.parent / "config" / "watchlist.yaml"
        with open(config_path, "r") as f:
            self.watchlist_config = yaml.safe_load(f)
        
        super().__init__(
            name="Scout",
            role="Breakthrough Signal Hunter",
            goal="Monitor news/RSS/X for breakthrough signals in target categories",
            backstory="""You are a signal detection specialist. Your mission: scan thousands 
            of news items daily and surface only the breakthrough moments—humanoid robot demos, 
            longevity trial results, AGI capability leaps, semiconductor breakthroughs. 
            You filter noise ruthlessly.""",
            config=config or {}
        )
        
        # Initialize news aggregator
        self.news_aggregator = NewsAggregator()
        
        # Extract all keywords from watchlist
        self.all_keywords = self._extract_all_keywords()
        
        self.logger.info(f"Scout Agent initialized with {len(self.all_keywords)} keywords")
    
    def _extract_all_keywords(self) -> List[str]:
        """Extract all keywords from watchlist configuration"""
        keywords = []
        
        # Public stocks keywords
        for stock in self.watchlist_config.get("public_stocks", []):
            keywords.extend(stock.get("keywords", []))
            keywords.append(stock.get("ticker"))
            keywords.append(stock.get("name"))
        
        # Private companies keywords
        for company in self.watchlist_config.get("private_companies", []):
            keywords.extend(company.get("keywords", []))
            keywords.append(company.get("name"))
        
        # Breakthrough keywords
        breakthrough = self.watchlist_config.get("breakthrough_keywords", {})
        for category, kws in breakthrough.items():
            keywords.extend(kws)
        
        # Remove duplicates and None values
        keywords = list(set([k for k in keywords if k]))
        
        return keywords
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Scout Agent workflow.
        
        Args:
            context: Dictionary with optional parameters:
                - days_back: Number of days to look back (default: 1)
                - max_results: Maximum results to return (default: 20)
                - min_relevance: Minimum relevance score (default: 6)
        
        Returns:
            Dictionary with filtered and scored news items
        """
        try:
            days_back = context.get("days_back", 1)
            max_results = context.get("max_results", 20)
            min_relevance = context.get("min_relevance", 6)
            
            self.logger.info(f"Fetching news for past {days_back} days")
            
            # Fetch news for all keywords
            raw_articles = self.news_aggregator.fetch_news_for_keywords(
                keywords=self.all_keywords,
                days_back=days_back,
                max_results=max_results * 2  # Fetch more, then filter
            )
            
            self.logger.info(f"Fetched {len(raw_articles)} raw articles")
            
            # Score and filter articles
            scored_articles = []
            for article in raw_articles:
                scored = self._score_article(article)
                if scored["relevance_score"] >= min_relevance:
                    scored_articles.append(scored)
            
            # Sort by relevance score
            scored_articles.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            # Limit to max_results
            scored_articles = scored_articles[:max_results]
            
            self.logger.info(f"Filtered to {len(scored_articles)} high-relevance articles")
            
            result = {
                "success": True,
                "articles": scored_articles,
                "total_fetched": len(raw_articles),
                "total_filtered": len(scored_articles),
                "timestamp": datetime.now().isoformat(),
                "agent": self.name
            }
            
            self.log_execution(context, result)
            return result
            
        except Exception as e:
            return self.handle_error(e, context)
    
    def _score_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score article relevance based on keyword matching and breakthrough signals.
        
        Scoring logic:
        - Base score: 5
        - +2 for each public stock keyword match
        - +3 for each private company keyword match
        - +3 for each breakthrough keyword match
        - +1 for title match (vs description only)
        - Cap at 10
        
        Args:
            article: Raw article dictionary
        
        Returns:
            Article with added relevance_score and matched_keywords
        """
        title = (article.get("title") or "").lower()
        description = (article.get("description") or "").lower()
        content = (article.get("content") or "").lower()
        
        full_text = f"{title} {description} {content}"
        
        score = 5  # Base score
        matched_keywords = []
        matched_categories = set()
        
        # Check public stocks
        for stock in self.watchlist_config.get("public_stocks", []):
            for keyword in stock.get("keywords", []):
                if keyword.lower() in full_text:
                    score += 2
                    matched_keywords.append(keyword)
                    matched_categories.add(stock.get("category"))
                    if keyword.lower() in title:
                        score += 1  # Bonus for title match
        
        # Check private companies
        for company in self.watchlist_config.get("private_companies", []):
            for keyword in company.get("keywords", []):
                if keyword.lower() in full_text:
                    score += 3  # Higher weight for private companies
                    matched_keywords.append(keyword)
                    matched_categories.add(company.get("category"))
                    if keyword.lower() in title:
                        score += 1
        
        # Check breakthrough keywords
        breakthrough = self.watchlist_config.get("breakthrough_keywords", {})
        for category, keywords in breakthrough.items():
            for keyword in keywords:
                if keyword.lower() in full_text:
                    score += 3  # High weight for breakthrough signals
                    matched_keywords.append(keyword)
                    matched_categories.add(f"breakthrough_{category}")
                    if keyword.lower() in title:
                        score += 1
        
        # Cap score at 10
        score = min(score, 10)
        
        # Remove duplicate keywords
        matched_keywords = list(set(matched_keywords))
        
        # Add scoring metadata to article
        scored_article = article.copy()
        scored_article.update({
            "relevance_score": score,
            "matched_keywords": matched_keywords,
            "matched_categories": list(matched_categories),
            "scored_at": datetime.now().isoformat()
        })
        
        return scored_article
    
    def get_top_signals(
        self,
        days_back: int = 7,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Convenience method to get top N breakthrough signals.
        
        Args:
            days_back: Days to look back
            top_n: Number of top signals to return
        
        Returns:
            List of top-scored articles
        """
        result = self.execute({
            "days_back": days_back,
            "max_results": top_n * 2,
            "min_relevance": 7  # Higher threshold for "top" signals
        })
        
        if result.get("success"):
            return result.get("articles", [])[:top_n]
        return []
