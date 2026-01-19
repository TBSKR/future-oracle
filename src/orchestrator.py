"""Chat orchestrator for FutureOracle."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from intents import IntentClassifier, IntentResult
from formatters import format_chat_response
from memory.chat_memory import ChatMemory

from core.grok_client import GrokClient
from data.market import MarketDataFetcher
from data.news import NewsAggregator
from core.portfolio import PortfolioManager


class ChatOrchestrator:
    """Routes chat requests to tools and agents, then formats responses."""

    def __init__(
        self,
        market: Optional[MarketDataFetcher] = None,
        news: Optional[NewsAggregator] = None,
        portfolio: Optional[PortfolioManager] = None,
        grok_client: Optional[GrokClient] = None,
        chat_memory: Optional[ChatMemory] = None,
        crew_available: bool = False,
        crew_factory: Optional[Any] = None,
        scout: Optional[Any] = None,
        analyst: Optional[Any] = None,
        forecaster: Optional[Any] = None,
    ):
        self.intent_classifier = IntentClassifier()
        self.market = market or MarketDataFetcher()
        self.news = news or NewsAggregator()
        self.portfolio = portfolio or PortfolioManager()
        self.grok = grok_client
        self.chat_memory = chat_memory
        self.crew_available = crew_available
        self.crew_factory = crew_factory
        self.scout = scout
        self.analyst = analyst
        self.forecaster = forecaster

    def handle_message(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        session_id = context.get("session_id", "default")
        profile = context.get("user_profile", {}) or {}
        plan = context.get("user_plan", {}) or {}
        known_tickers = context.get("known_tickers", []) or []
        watch_keywords = context.get("watch_keywords", []) or []

        intent_result = self.intent_classifier.classify(message, known_tickers)
        profile = self._update_profile(profile, intent_result)
        plan = self._update_plan(plan, message, intent_result)

        response_payload = self._route_intent(
            message=message,
            intent_result=intent_result,
            profile=profile,
            plan=plan,
            watch_keywords=watch_keywords,
        )

        response_text = format_chat_response(
            tldr=response_payload["tldr"],
            why=response_payload.get("why"),
            assumptions=response_payload.get("assumptions"),
            confidence=response_payload.get("confidence"),
            next_steps=response_payload.get("next"),
            evidence=response_payload.get("evidence"),
            glossary=response_payload.get("glossary"),
            disclaimers=response_payload.get("disclaimers"),
        )

        if self.chat_memory:
            self.chat_memory.store_message(
                session_id=session_id,
                role="user",
                content=message,
                intent=intent_result.intent,
                tickers=intent_result.tickers,
            )
            self.chat_memory.store_message(
                session_id=session_id,
                role="assistant",
                content=response_text,
                intent=intent_result.intent,
                tickers=intent_result.tickers,
                metadata={
                    "confidence": response_payload.get("confidence"),
                    "tldr": response_payload.get("tldr"),
                },
            )
            summary_text = response_payload.get("tldr")
            if summary_text:
                self.chat_memory.store_summary(
                    summary_text=summary_text,
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "intent": intent_result.intent,
                        "tickers": intent_result.tickers,
                        "analysis_type": "chat_summary",
                        "summary": summary_text,
                    },
                )

        return {
            "response": response_text,
            "intent": intent_result.intent,
            "profile": profile,
            "plan": plan,
            "entities": {
                "tickers": intent_result.tickers,
                "timeframe": intent_result.timeframe,
            },
        }

    def _route_intent(
        self,
        message: str,
        intent_result: IntentResult,
        profile: Dict[str, Any],
        plan: Dict[str, Any],
        watch_keywords: List[str],
    ) -> Dict[str, Any]:
        intent = intent_result.intent

        if intent == "daily_brief":
            return self._handle_daily_brief(watch_keywords)
        if intent == "stock_question":
            return self._handle_stock_question(message, intent_result, profile)
        if intent == "forecast":
            return self._handle_forecast(message, plan, profile)
        if intent == "portfolio_summary":
            return self._handle_portfolio_summary(profile)
        if intent == "explain_signal":
            return self._handle_explain_signal(message, intent_result)
        return self._handle_general(message, profile)

    def _handle_daily_brief(self, watch_keywords: List[str]) -> Dict[str, Any]:
        if self.scout and self.analyst:
            scout_result = self.scout.execute({"days_back": 1, "max_results": 10, "min_relevance": 6})
            articles = scout_result.get("articles", []) if scout_result.get("success") else []
            analyst_result = self.analyst.execute({"articles": articles, "max_analyses": 3})
            analyses = analyst_result.get("analyses", []) if analyst_result.get("success") else []
        else:
            keywords = watch_keywords[:12] or ["market", "stocks", "earnings"]
            articles = self.news.fetch_news_for_keywords(
                keywords=keywords,
                days_back=1,
                max_results=5,
            )
            analyses = []

        if not analyses and not articles:
            return {
                "tldr": "No fresh signals surfaced in the last 24 hours.",
                "why": ["Markets look quiet across the watchlist right now."],
                "assumptions": ["Headline coverage may be incomplete."],
                "confidence": "Low",
                "next": "Ask for a deep dive on a ticker or open the Signals tab.",
                "disclaimers": [],
            }

        evidence = []
        why = []
        if analyses:
            top = sorted(analyses, key=lambda a: a.get("impact_score", 0), reverse=True)[:3]
            tldr_titles = [item.get("article_title") for item in top if item.get("article_title")]
            for item in top:
                insight = item.get("key_insight")
                if insight:
                    why.append(insight)
                title = item.get("article_title")
                source = item.get("article_source")
                if title:
                    evidence.append(f"{title} ({source or 'source'})")
            tldr = "; ".join(tldr_titles) if tldr_titles else "Top signals are ready."
            confidence = "Medium" if self.analyst and self.analyst.grok_available else "Low"
        else:
            tldr_titles = [a.get("title") for a in articles[:3] if a.get("title")]
            tldr = "; ".join(tldr_titles) if tldr_titles else "Fresh headlines are in."
            evidence = [
                f"{article.get('title')} ({article.get('source', 'source')})"
                for article in articles[:3]
                if article.get("title")
            ]
            why = ["These headlines may signal near-term catalysts worth tracking."]
            confidence = "Low"

        return {
            "tldr": tldr,
            "why": why or ["Signals highlight where attention is building."],
            "assumptions": ["Coverage is limited to configured sources."],
            "confidence": confidence,
            "next": "Ask for a deeper read on any headline, or switch to Signals for the full list.",
            "evidence": evidence,
            "disclaimers": [],
        }

    def _handle_stock_question(
        self,
        message: str,
        intent_result: IntentResult,
        profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        tickers = intent_result.tickers
        if not tickers:
            return {
                "tldr": "Tell me which ticker you want to explore (e.g., NVDA or TSLA).",
                "why": ["I need a specific ticker to pull price and news context."],
                "assumptions": ["We will focus on the ticker you name."],
                "confidence": "High",
                "next": "Reply with a ticker and your time horizon if you have one.",
                "disclaimers": [],
            }

        ticker = tickers[0]
        quote = self.market.get_quote(ticker)
        price = quote.get("price")
        change = quote.get("change_percent")

        try:
            portfolio_summary = self.portfolio.get_portfolio_summary()
        except Exception:
            portfolio_summary = {}
        holding = next(
            (pos for pos in portfolio_summary.get("positions", []) if pos.get("ticker") == ticker),
            None,
        )

        headlines = self.news.fetch_news_for_keywords(
            keywords=[ticker],
            days_back=7,
            max_results=3,
        )
        headline_titles = [item.get("title") for item in headlines if item.get("title")]

        if self._should_use_crewai(message):
            crew_output = self._run_crewai(
                intent="stock_question",
                tickers=[ticker],
                profile=profile,
                user_prompt=message,
            )
            if crew_output:
                return self._format_crewai_output(
                    crew_output=crew_output,
                    fallback_tldr=f"CrewAI deep analysis for {ticker} is ready.",
                    disclaimers=["Educational only, not financial advice."],
                )

        grok_payload = self._maybe_generate_structured_with_grok(
            system_prompt="You are a cautious, explainable market assistant. Provide educational, risk-framed context only.",
            user_prompt=self._build_stock_prompt(message, ticker, quote, holding, headline_titles, profile),
        )

        if grok_payload:
            grok_payload.setdefault(
                "disclaimers",
                ["Educational only, not financial advice."],
            )
            return grok_payload

        price_text = f"${price:.2f}" if isinstance(price, (int, float)) else "N/A"
        change_text = f"{change:+.1f}%" if isinstance(change, (int, float)) else "N/A"
        position_text = (
            f"You already hold {holding['shares']:.2f} shares."
            if holding
            else "No existing position found in your portfolio."
        )

        return {
            "tldr": f"{ticker} is at {price_text} ({change_text}). I can’t advise on buying, but here’s the context.",
            "why": [
                position_text,
                "Recent headlines suggest where momentum is forming.",
            ],
            "assumptions": [
                "Price and headlines reflect the latest available data.",
                "No broader macro constraints are considered here.",
            ],
            "confidence": "Medium" if price else "Low",
            "next": "Ask for a deep-dive, risk framing, or a comparison against another ticker.",
            "evidence": [title for title in headline_titles] if headline_titles else [],
            "disclaimers": ["Educational only, not financial advice."],
        }

    def _should_use_crewai(self, message: str) -> bool:
        if not self.crew_available or not self.crew_factory:
            return False
        return bool(re.search(r"\b(deep|detailed|full|analysis|compare)\b", message.lower()))

    def _run_crewai(
        self,
        intent: str,
        tickers: List[str],
        profile: Dict[str, Any],
        user_prompt: str,
    ) -> Optional[str]:
        if not self.crew_factory:
            return None
        try:
            crew = self.crew_factory(
                {
                    "intent": intent,
                    "tickers": tickers,
                    "risk_profile": profile.get("risk", "medium"),
                    "user_prompt": user_prompt,
                }
            )
            result = crew.kickoff()
            return str(result)
        except Exception:
            return None

    def _format_crewai_output(
        self,
        crew_output: str,
        fallback_tldr: str,
        disclaimers: List[str],
    ) -> Dict[str, Any]:
        grok_payload = self._maybe_generate_structured_with_grok(
            system_prompt="Summarize CrewAI output into an explainable, user-friendly response.",
            user_prompt=f"Crew output:\n{crew_output}",
        )
        if grok_payload:
            grok_payload.setdefault("disclaimers", disclaimers)
            return grok_payload

        evidence = [line.strip() for line in crew_output.splitlines() if line.strip()][:4]
        return {
            "tldr": fallback_tldr,
            "why": ["CrewAI surfaced deeper context across sources."],
            "assumptions": ["CrewAI output reflects its source inputs."],
            "confidence": "Medium",
            "next": "Ask a follow-up or request a comparison.",
            "evidence": evidence,
            "disclaimers": disclaimers,
        }

    def _handle_forecast(self, message: str, plan: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
        required_fields = ["current_age", "current_value", "monthly_contribution"]
        missing = [field for field in required_fields if field not in plan]

        if missing:
            missing_label = ", ".join(missing)
            return {
                "tldr": "I can forecast once I have your age, current portfolio value, and monthly contribution.",
                "why": ["Those inputs anchor the growth scenarios."],
                "assumptions": ["Defaults are intentionally avoided to keep forecasts honest."],
                "confidence": "High",
                "next": f"Share {missing_label}. Example: 'I'm 32 with €15,000 and invest €300/month.'",
                "disclaimers": ["Educational only, not financial advice."],
            }

        if not self.forecaster:
            return {
                "tldr": "Forecasting is unavailable in this environment.",
                "why": ["The forecaster agent is not configured."],
                "assumptions": ["Enable the forecaster agent to compute scenarios."],
                "confidence": "Low",
                "next": "Install dependencies or open Forecasts for manual inputs.",
                "disclaimers": ["Educational only, not financial advice."],
            }

        result = self.forecaster.execute(
            {
                "current_age": plan["current_age"],
                "current_value": plan["current_value"],
                "monthly_contribution": plan["monthly_contribution"],
                "annual_bonus": plan.get("annual_bonus", 1000),
                "target_ages": plan.get(
                    "target_ages",
                    [plan["current_age"] + 10, plan["current_age"] + 20, plan["current_age"] + 30],
                ),
            }
        )

        if not result.get("success"):
            return {
                "tldr": "Forecasting failed on this run.",
                "why": ["The forecaster agent returned an error."],
                "assumptions": ["Inputs may need adjustment."],
                "confidence": "Low",
                "next": "Try again or adjust your inputs.",
                "disclaimers": ["Educational only, not financial advice."],
            }

        forecasts = result.get("forecasts", [])
        evidence = []
        for forecast in forecasts[:2]:
            evidence.append(
                f"Age {forecast.get('target_age')}: base €{forecast.get('base_case'):,.0f}, "
                f"bull €{forecast.get('bull_case'):,.0f}, super-bull €{forecast.get('super_bull_case'):,.0f}"
            )

        assumptions = []
        if forecasts:
            assumptions = forecasts[0].get("key_assumptions", [])[:3]

        return {
            "tldr": result.get("summary", "Forecasts generated."),
            "why": [
                f"Scenarios align with a {profile.get('risk', 'medium')} risk posture.",
                "Long-term outcomes are sensitive to contributions and compounding rates.",
            ],
            "assumptions": assumptions or ["Contribution plan remains steady."],
            "confidence": "Medium" if result.get("grok_available") else "Low",
            "next": "Ask for a specific milestone or adjust your monthly contribution.",
            "evidence": evidence,
            "disclaimers": ["Educational only, not financial advice."],
        }

    def _handle_portfolio_summary(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        try:
            summary = self.portfolio.get_portfolio_summary()
        except Exception:
            summary = {"total_value": 0, "positions": []}
        total_value = summary.get("total_value", 0)
        positions = summary.get("positions", [])

        evidence = []
        for pos in positions[:3]:
            evidence.append(
                f"{pos.get('ticker')}: {pos.get('shares', 0):.2f} shares, "
                f"€{pos.get('current_value', 0):,.0f}"
            )

        return {
            "tldr": f"Portfolio value is €{total_value:,.0f} across {len(positions)} positions.",
            "why": ["Concentration and exposure shape risk and opportunity."],
            "assumptions": ["Prices reflect the latest market data."],
            "confidence": "Medium",
            "next": "Ask to drill into a position or open Portfolio for details.",
            "evidence": evidence,
            "disclaimers": ["Educational only, not financial advice."],
        }

    def _handle_explain_signal(self, message: str, intent_result: IntentResult) -> Dict[str, Any]:
        ticker = intent_result.tickers[0] if intent_result.tickers else None
        headlines = []
        if ticker:
            headlines = self.news.fetch_news_for_keywords([ticker], days_back=7, max_results=2)
        headline_titles = [item.get("title") for item in headlines if item.get("title")]

        grok_payload = self._maybe_generate_structured_with_grok(
            system_prompt="You explain market signals in simple, beginner-friendly language.",
            user_prompt=self._build_explain_prompt(message, headline_titles),
        )
        if grok_payload:
            return grok_payload

        tldr = headline_titles[0] if headline_titles else "Share the signal you want explained."
        glossary = ["Catalyst: a trigger that can move price.", "Volatility: how much prices swing."]
        return {
            "tldr": tldr,
            "why": ["Signals help you decide what to research next."],
            "assumptions": ["Headlines capture the core signal."],
            "confidence": "Low" if not headline_titles else "Medium",
            "next": "Ask me to define a specific term or compare two signals.",
            "evidence": headline_titles,
            "glossary": glossary,
            "disclaimers": [],
        }

    def _handle_general(self, message: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        grok_payload = self._maybe_generate_structured_with_grok(
            system_prompt="You are a helpful market assistant focused on clarity and safety.",
            user_prompt=f"User message: {message}\nProfile: {profile}",
        )
        if grok_payload:
            return grok_payload

        return {
            "tldr": "I can help with market context, forecasts, or portfolio insights.",
            "why": ["Chat-first flow keeps decisions transparent and guided."],
            "assumptions": ["You want a concise, explainable response."],
            "confidence": "Medium",
            "next": "Try: “What happened today?” or “Should I buy NVDA?”",
            "disclaimers": [],
        }

    def _maybe_generate_structured_with_grok(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Optional[Dict[str, Any]]:
        if not self.grok:
            return None
        prompt = (
            f"{user_prompt}\n\n"
            "Return JSON with keys: tldr, why, assumptions, confidence, next, evidence, glossary, disclaimers.\n"
            "The value for why, assumptions, evidence, glossary, disclaimers should be a list of strings."
        )
        try:
            response = self.grok.analyze_with_prompt(
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=0.4,
                max_tokens=400,
            )
        except Exception:
            return None

        payload = self._extract_json(response)
        if not payload:
            return None
        return payload

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.S)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None

    def _build_stock_prompt(
        self,
        message: str,
        ticker: str,
        quote: Dict[str, Any],
        holding: Optional[Dict[str, Any]],
        headline_titles: List[str],
        profile: Dict[str, Any],
    ) -> str:
        return (
            f"User question: {message}\n"
            f"Ticker: {ticker}\n"
            f"Quote: {quote}\n"
            f"Holding: {holding}\n"
            f"Recent headlines: {headline_titles}\n"
            f"User profile: {profile}\n"
            "Respond with risk-framed, educational context only."
        )

    def _build_explain_prompt(self, message: str, headline_titles: List[str]) -> str:
        return (
            f"User request: {message}\n"
            f"Relevant headlines: {headline_titles}\n"
            "Explain like I'm new. Include 2-3 glossary terms."
        )

    def _update_profile(self, profile: Dict[str, Any], intent_result: IntentResult) -> Dict[str, Any]:
        updated = dict(profile)
        if intent_result.risk_profile:
            updated["risk"] = intent_result.risk_profile
        if intent_result.horizon:
            updated["horizon"] = intent_result.horizon
        return updated

    def _update_plan(self, plan: Dict[str, Any], message: str, intent_result: IntentResult) -> Dict[str, Any]:
        updated = dict(plan)
        if intent_result.monthly_contribution:
            updated["monthly_contribution"] = intent_result.monthly_contribution

        age_match = re.search(r"\b(?:i am|i'm|age)\s*(\d{2})\b", message.lower())
        if age_match:
            updated["current_age"] = int(age_match.group(1))

        value_match = re.search(
            r"(?:current value|portfolio value|have)\s*(?:€|\$)\s?([0-9,]+)",
            message.lower(),
        )
        if value_match:
            updated["current_value"] = float(value_match.group(1).replace(",", ""))

        targets_match = re.search(r"target ages?\s*[:\-]?\s*([0-9,\s]+)", message.lower())
        if targets_match:
            raw = targets_match.group(1)
            targets = [int(val) for val in re.findall(r"\d{2}", raw)]
            if targets:
                updated["target_ages"] = targets

        return updated
