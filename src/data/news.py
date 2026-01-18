"""
News Aggregation Module

Fetches news from multiple sources:
- NewsAPI
- RSS feeds
- X/Twitter (future)
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from newsapi import NewsApiClient
import feedparser
import requests


class NewsAggregator:
    """
    Aggregates news from multiple sources for watchlist monitoring.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("futureoracle.news")
        
        # Initialize NewsAPI client
        api_key = os.getenv("NEWSAPI_KEY")
        self.newsapi = NewsApiClient(api_key=api_key) if api_key else None
        
        # RSS feeds from config
        rss_feeds_str = os.getenv("RSS_FEEDS", "")
        self.rss_feeds = [f.strip() for f in rss_feeds_str.split(",") if f.strip()]
    
    def fetch_news_for_keywords(
        self,
        keywords: List[str],
        days_back: int = 1,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Fetch news articles matching keywords.
        
        Args:
            keywords: List of keywords to search for
            days_back: How many days back to search
            max_results: Maximum number of results to return
            
        Returns:
            List of news article dictionaries
        """
        all_articles = []
        
        # Fetch from NewsAPI
        if self.newsapi:
            newsapi_articles = self._fetch_from_newsapi(keywords, days_back, max_results)
            all_articles.extend(newsapi_articles)
        
        # Fetch from RSS feeds
        rss_articles = self._fetch_from_rss(keywords)
        all_articles.extend(rss_articles)
        
        # Deduplicate and sort by date
        all_articles = self._deduplicate_articles(all_articles)
        all_articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)
        
        return all_articles[:max_results]
    
    def _fetch_from_newsapi(
        self,
        keywords: List[str],
        days_back: int,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Fetch articles from NewsAPI"""
        articles = []
        
        try:
            # Calculate date range
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days_back)
            
            # Build query
            query = " OR ".join(keywords)
            
            # Fetch articles
            response = self.newsapi.get_everything(
                q=query,
                from_param=from_date.strftime("%Y-%m-%d"),
                to=to_date.strftime("%Y-%m-%d"),
                language="en",
                sort_by="publishedAt",
                page_size=max_results
            )
            
            # Parse response
            for article in response.get("articles", []):
                articles.append({
                    "title": article.get("title"),
                    "description": article.get("description"),
                    "url": article.get("url"),
                    "source": article.get("source", {}).get("name"),
                    "published_at": article.get("publishedAt"),
                    "content": article.get("content"),
                    "image_url": article.get("urlToImage"),
                    "source_type": "newsapi"
                })
            
            self.logger.info(f"Fetched {len(articles)} articles from NewsAPI")
            
        except Exception as e:
            self.logger.error(f"Error fetching from NewsAPI: {e}")
        
        return articles
    
    def _fetch_from_rss(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Fetch articles from RSS feeds"""
        articles = []
        
        for feed_url in self.rss_feeds:
            try:
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries:
                    # Check if any keyword matches
                    title = entry.get("title", "").lower()
                    summary = entry.get("summary", "").lower()
                    
                    if any(kw.lower() in title or kw.lower() in summary for kw in keywords):
                        articles.append({
                            "title": entry.get("title"),
                            "description": entry.get("summary"),
                            "url": entry.get("link"),
                            "source": feed.feed.get("title", "RSS"),
                            "published_at": entry.get("published", entry.get("updated")),
                            "content": entry.get("content", [{}])[0].get("value") if entry.get("content") else None,
                            "source_type": "rss"
                        })
                
                self.logger.info(f"Fetched {len(articles)} articles from RSS: {feed_url}")
                
            except Exception as e:
                self.logger.error(f"Error fetching RSS feed {feed_url}: {e}")
        
        return articles
    
    def _deduplicate_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate articles based on URL"""
        seen_urls = set()
        unique_articles = []
        
        for article in articles:
            url = article.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)
        
        return unique_articles
    
    def fetch_company_news(
        self,
        company_name: str,
        ticker: str,
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Fetch news for a specific company.
        
        Args:
            company_name: Full company name
            ticker: Stock ticker
            days_back: Days to look back
            
        Returns:
            List of news articles
        """
        keywords = [company_name, ticker]
        return self.fetch_news_for_keywords(keywords, days_back)
