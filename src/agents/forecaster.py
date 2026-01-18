"""
Forecaster Agent

Generates personalized long-term investment scenarios tied to user's age and contributions.
Uses Grok 4 for optimistic-realistic forecasts with fallback to static calculations.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import re

from agents.base import BaseAgent
from core.grok_client import GrokClient


class ForecasterAgent(BaseAgent):
    """
    Forecaster Agent - Generates personalized investment scenarios.
    
    Creates Base/Bull/Super-Bull forecasts for multiple age milestones
    based on current portfolio value and contribution plan.
    """
    
    def __init__(self, grok_client: Optional[GrokClient] = None):
        """
        Initialize Forecaster Agent.
        
        Args:
            grok_client: Optional GrokClient instance (creates new if None)
        """
        super().__init__(
            name="forecaster",
            role="Long-Term Forecaster",
            goal="Generate personalized long-term investment scenarios",
            backstory="Expert at modeling exponential growth in breakthrough technologies"
        )
        
        # Initialize Grok client
        try:
            self.grok = grok_client or GrokClient()
            self.logger.info("Grok client initialized successfully")
        except Exception as e:
            self.logger.warning(f"Grok client unavailable: {e}")
            self.grok = None
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate personalized investment forecasts.
        
        Args:
            inputs: Dictionary containing:
                - current_age: User's current age (default: 21)
                - current_value: Current portfolio value in € (default: 0)
                - monthly_contribution: Monthly investment in € (default: 300)
                - annual_bonus: Annual bonus investment in € (default: 1000)
                - target_ages: List of target ages (default: [31, 41, 51])
        
        Returns:
            Dictionary with:
                - success: bool
                - grok_available: bool
                - forecasts: List of forecast dictionaries
                - summary: Summary text
                - error: Optional error message
        """
        try:
            # Extract inputs with defaults
            current_age = inputs.get("current_age", 21)
            current_value = inputs.get("current_value", 0)
            monthly_contribution = inputs.get("monthly_contribution", 300)
            annual_bonus = inputs.get("annual_bonus", 1000)
            target_ages = inputs.get("target_ages", [31, 41, 51])
            
            self.logger.info(f"Generating forecasts for age {current_age}, starting value €{current_value:,.0f}")
            
            # Generate forecasts for each target age
            forecasts = []
            for target_age in target_ages:
                years_ahead = target_age - current_age
                if years_ahead <= 0:
                    self.logger.warning(f"Skipping target age {target_age} (not in future)")
                    continue
                
                forecast = self._generate_forecast(
                    current_age=current_age,
                    target_age=target_age,
                    years_ahead=years_ahead,
                    current_value=current_value,
                    monthly_contribution=monthly_contribution,
                    annual_bonus=annual_bonus
                )
                forecasts.append(forecast)
            
            # Generate summary
            summary = self._generate_summary(forecasts, current_age)
            
            return {
                "success": True,
                "grok_available": self.grok is not None,
                "forecasts": forecasts,
                "summary": summary,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Forecast generation failed: {e}")
            return {
                "success": False,
                "grok_available": False,
                "forecasts": [],
                "summary": "",
                "error": str(e)
            }
    
    def _generate_forecast(
        self,
        current_age: int,
        target_age: int,
        years_ahead: int,
        current_value: float,
        monthly_contribution: float,
        annual_bonus: float
    ) -> Dict[str, Any]:
        """
        Generate forecast for a specific target age.
        
        Args:
            current_age: User's current age
            target_age: Target age for forecast
            years_ahead: Years until target age
            current_value: Current portfolio value
            monthly_contribution: Monthly investment
            annual_bonus: Annual bonus investment
        
        Returns:
            Forecast dictionary with Base/Bull/Super-Bull scenarios
        """
        try:
            # Calculate total contributions
            total_contributions = current_value + (monthly_contribution * 12 * years_ahead) + (annual_bonus * years_ahead)
            
            # Try Grok first
            if self.grok:
                try:
                    grok_forecast = self._generate_grok_forecast(
                        current_age=current_age,
                        target_age=target_age,
                        years_ahead=years_ahead,
                        current_value=current_value,
                        monthly_contribution=monthly_contribution,
                        annual_bonus=annual_bonus,
                        total_contributions=total_contributions
                    )
                    if grok_forecast:
                        return grok_forecast
                except Exception as e:
                    self.logger.warning(f"Grok forecast failed, using fallback: {e}")
            
            # Fallback to static calculation
            return self._generate_static_forecast(
                target_age=target_age,
                years_ahead=years_ahead,
                current_value=current_value,
                monthly_contribution=monthly_contribution,
                annual_bonus=annual_bonus,
                total_contributions=total_contributions
            )
            
        except Exception as e:
            self.logger.error(f"Forecast generation failed for age {target_age}: {e}")
            return {
                "target_age": target_age,
                "years_ahead": years_ahead,
                "base_case": 0,
                "bull_case": 0,
                "super_bull_case": 0,
                "error": str(e)
            }
    
    def _generate_grok_forecast(
        self,
        current_age: int,
        target_age: int,
        years_ahead: int,
        current_value: float,
        monthly_contribution: float,
        annual_bonus: float,
        total_contributions: float
    ) -> Optional[Dict[str, Any]]:
        """
        Generate forecast using Grok 4.
        
        Returns:
            Forecast dictionary or None if failed
        """
        try:
            # Build prompt
            prompt = f"""You are a sharp investment forecaster focused on AI/tech/longevity stocks.

Generate realistic portfolio projections for a {current_age}-year-old investor targeting age {target_age} ({years_ahead} years ahead).

**Current Situation:**
- Current portfolio value: €{current_value:,.0f}
- Monthly investment: €{monthly_contribution:,.0f}
- Annual bonus: €{annual_bonus:,.0f}
- Total contributions over {years_ahead} years: €{total_contributions:,.0f}

**Investment Focus:**
- AI infrastructure (NVIDIA, ASML)
- Humanoid robotics (Tesla, Figure AI)
- Longevity biotech (Altos Labs, emerging)
- High-conviction exponential tech

**Task:**
Provide THREE scenarios with final portfolio values at age {target_age}:

1. BASE CASE: Conservative but realistic (early years 40-50% annual, later 25-30%)
2. BULL CASE: Strong tech adoption (early 50-60% annual, later 30-40%)
3. SUPER-BULL CASE: Exponential breakthrough (early 60-70% annual, later 35-45%)

Format your response EXACTLY like this:

BASE CASE: €XXX,XXX
Rationale: [1 sentence]

BULL CASE: €XXX,XXX
Rationale: [1 sentence]

SUPER-BULL CASE: €XXX,XXX
Rationale: [1 sentence]

KEY ASSUMPTIONS: [2-3 bullet points about market drivers]
"""
            
            # Call Grok
            response = self.grok.analyze_with_prompt(prompt)
            
            # Parse response
            parsed = self._parse_grok_forecast(response, target_age, years_ahead)
            
            if parsed:
                self.logger.info(f"Grok forecast generated for age {target_age}")
                return parsed
            else:
                self.logger.warning("Failed to parse Grok forecast response")
                return None
                
        except Exception as e:
            self.logger.error(f"Grok forecast failed: {e}")
            return None
    
    def _parse_grok_forecast(
        self,
        response: str,
        target_age: int,
        years_ahead: int
    ) -> Optional[Dict[str, Any]]:
        """
        Parse Grok forecast response.
        
        Args:
            response: Grok API response text
            target_age: Target age
            years_ahead: Years ahead
        
        Returns:
            Parsed forecast dictionary or None
        """
        try:
            forecast = {
                "target_age": target_age,
                "years_ahead": years_ahead,
                "base_case": 0,
                "base_rationale": "",
                "bull_case": 0,
                "bull_rationale": "",
                "super_bull_case": 0,
                "super_bull_rationale": "",
                "key_assumptions": [],
                "is_grok": True
            }
            
            # Extract BASE CASE
            base_match = re.search(r'BASE CASE:\s*€?([\d,]+)', response, re.IGNORECASE)
            if base_match:
                forecast["base_case"] = self._parse_euro_amount(base_match.group(1))
            
            base_rationale = self._extract_section(response, "BASE CASE:", "BULL CASE:")
            if base_rationale:
                rationale_match = re.search(r'Rationale:\s*(.+?)(?:\n|$)', base_rationale, re.IGNORECASE)
                if rationale_match:
                    forecast["base_rationale"] = rationale_match.group(1).strip()
            
            # Extract BULL CASE
            bull_match = re.search(r'BULL CASE:\s*€?([\d,]+)', response, re.IGNORECASE)
            if bull_match:
                forecast["bull_case"] = self._parse_euro_amount(bull_match.group(1))
            
            bull_rationale = self._extract_section(response, "BULL CASE:", "SUPER-BULL CASE:")
            if bull_rationale:
                rationale_match = re.search(r'Rationale:\s*(.+?)(?:\n|$)', bull_rationale, re.IGNORECASE)
                if rationale_match:
                    forecast["bull_rationale"] = rationale_match.group(1).strip()
            
            # Extract SUPER-BULL CASE
            super_bull_match = re.search(r'SUPER-BULL CASE:\s*€?([\d,]+)', response, re.IGNORECASE)
            if super_bull_match:
                forecast["super_bull_case"] = self._parse_euro_amount(super_bull_match.group(1))
            
            super_bull_rationale = self._extract_section(response, "SUPER-BULL CASE:", "KEY ASSUMPTIONS:")
            if super_bull_rationale:
                rationale_match = re.search(r'Rationale:\s*(.+?)(?:\n|$)', super_bull_rationale, re.IGNORECASE)
                if rationale_match:
                    forecast["super_bull_rationale"] = rationale_match.group(1).strip()
            
            # Extract KEY ASSUMPTIONS
            assumptions_text = self._extract_section(response, "KEY ASSUMPTIONS:", "")
            if assumptions_text:
                assumptions = self._extract_list_items(assumptions_text)
                forecast["key_assumptions"] = assumptions[:3]  # Limit to 3
            
            # Validate we got at least the amounts
            if forecast["base_case"] > 0 and forecast["bull_case"] > 0 and forecast["super_bull_case"] > 0:
                return forecast
            else:
                self.logger.warning("Incomplete Grok forecast, missing case values")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to parse Grok forecast: {e}")
            return None
    
    def _generate_static_forecast(
        self,
        target_age: int,
        years_ahead: int,
        current_value: float,
        monthly_contribution: float,
        annual_bonus: float,
        total_contributions: float
    ) -> Dict[str, Any]:
        """
        Generate forecast using static calculation (fallback).
        
        Uses compound annual growth rates:
        - Base: Early 45%, later 27.5%
        - Bull: Early 55%, later 35%
        - Super-Bull: Early 65%, later 40%
        
        Args:
            target_age: Target age
            years_ahead: Years ahead
            current_value: Current portfolio value
            monthly_contribution: Monthly investment
            annual_bonus: Annual bonus investment
            total_contributions: Total contributions
        
        Returns:
            Forecast dictionary
        """
        try:
            # Define growth rates (early years vs later years)
            # Early = first 10 years or half the period, whichever is less
            early_years = min(10, years_ahead // 2)
            later_years = years_ahead - early_years
            
            # Growth rates
            base_early_rate = 0.45
            base_later_rate = 0.275
            
            bull_early_rate = 0.55
            bull_later_rate = 0.35
            
            super_bull_early_rate = 0.65
            super_bull_later_rate = 0.40
            
            # Calculate for each scenario
            base_case = self._calculate_compound_growth(
                current_value=current_value,
                monthly_contribution=monthly_contribution,
                annual_bonus=annual_bonus,
                early_years=early_years,
                early_rate=base_early_rate,
                later_years=later_years,
                later_rate=base_later_rate
            )
            
            bull_case = self._calculate_compound_growth(
                current_value=current_value,
                monthly_contribution=monthly_contribution,
                annual_bonus=annual_bonus,
                early_years=early_years,
                early_rate=bull_early_rate,
                later_years=later_years,
                later_rate=bull_later_rate
            )
            
            super_bull_case = self._calculate_compound_growth(
                current_value=current_value,
                monthly_contribution=monthly_contribution,
                annual_bonus=annual_bonus,
                early_years=early_years,
                early_rate=super_bull_early_rate,
                later_years=later_years,
                later_rate=super_bull_later_rate
            )
            
            return {
                "target_age": target_age,
                "years_ahead": years_ahead,
                "base_case": round(base_case, 2),
                "base_rationale": f"Conservative growth: {base_early_rate*100:.0f}% early, {base_later_rate*100:.1f}% later",
                "bull_case": round(bull_case, 2),
                "bull_rationale": f"Strong tech adoption: {bull_early_rate*100:.0f}% early, {bull_later_rate*100:.0f}% later",
                "super_bull_case": round(super_bull_case, 2),
                "super_bull_rationale": f"Exponential breakthrough: {super_bull_early_rate*100:.0f}% early, {super_bull_later_rate*100:.0f}% later",
                "key_assumptions": [
                    "AI infrastructure continues exponential growth",
                    "Humanoid robotics reaches commercial scale",
                    "Longevity biotech achieves major breakthroughs"
                ],
                "is_grok": False
            }
            
        except Exception as e:
            self.logger.error(f"Static forecast calculation failed: {e}")
            return {
                "target_age": target_age,
                "years_ahead": years_ahead,
                "base_case": total_contributions,
                "bull_case": total_contributions * 1.5,
                "super_bull_case": total_contributions * 2,
                "error": str(e),
                "is_grok": False
            }
    
    def _calculate_compound_growth(
        self,
        current_value: float,
        monthly_contribution: float,
        annual_bonus: float,
        early_years: int,
        early_rate: float,
        later_years: int,
        later_rate: float
    ) -> float:
        """
        Calculate compound growth with contributions.
        
        Args:
            current_value: Starting portfolio value
            monthly_contribution: Monthly investment
            annual_bonus: Annual bonus investment
            early_years: Number of early years
            early_rate: Annual growth rate for early years
            later_years: Number of later years
            later_rate: Annual growth rate for later years
        
        Returns:
            Final portfolio value
        """
        value = current_value
        
        # Early years
        for year in range(early_years):
            # Add contributions at start of year
            value += (monthly_contribution * 12) + annual_bonus
            # Apply growth
            value *= (1 + early_rate)
        
        # Later years
        for year in range(later_years):
            # Add contributions at start of year
            value += (monthly_contribution * 12) + annual_bonus
            # Apply growth
            value *= (1 + later_rate)
        
        return value
    
    def _generate_summary(self, forecasts: List[Dict[str, Any]], current_age: int) -> str:
        """
        Generate motivational summary text.
        
        Args:
            forecasts: List of forecast dictionaries
            current_age: User's current age
        
        Returns:
            Summary text
        """
        if not forecasts:
            return "No forecasts generated."
        
        try:
            # Get first and last forecast
            first = forecasts[0]
            last = forecasts[-1]
            
            # Calculate multiples
            first_multiple = first["super_bull_case"] / max(first["base_case"], 1)
            last_multiple = last["super_bull_case"] / max(last["base_case"], 1)
            
            summary = f"""Your exponential wealth journey starts now at age {current_age}.

By age {first['target_age']}, your portfolio could reach **€{first['super_bull_case']:,.0f}** in the super-bull case — that's {first_multiple:.1f}x the conservative estimate.

By age {last['target_age']}, you're looking at **€{last['super_bull_case']:,.0f}** if AI/humanoids/longevity deliver on their promise.

The key: Stay invested in breakthrough tech, compound relentlessly, and think in decades. The future is exponential."""
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Summary generation failed: {e}")
            return "Forecasts generated successfully. Review the scenarios below."
    
    def _parse_euro_amount(self, amount_str: str) -> float:
        """Parse euro amount string to float"""
        try:
            # Handle K/M suffixes first
            if "K" in amount_str.upper():
                cleaned = amount_str.upper().replace("K", "").replace(",", "")
                return float(cleaned) * 1000
            elif "M" in amount_str.upper():
                cleaned = amount_str.upper().replace("M", "").replace(",", "")
                return float(cleaned) * 1000000
            else:
                # Remove commas and dots (thousands separators)
                cleaned = amount_str.replace(",", "").replace(".", "")
                return float(cleaned)
        except Exception as e:
            self.logger.error(f"Failed to parse euro amount '{amount_str}': {e}")
            return 0
    
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
                    section = text[start_idx:].strip()
                else:
                    section = text[start_idx:end_idx].strip()
            else:
                section = text[start_idx:].strip()
            
            section = section.lstrip(':').strip()
            return section if section else None
            
        except Exception as e:
            self.logger.error(f"Section extraction failed: {e}")
            return None
    
    def _extract_list_items(self, text: str) -> List[str]:
        """Extract bullet point items from text"""
        try:
            items = []
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('*') or line.startswith('•') or re.match(r'^\d+\.', line)):
                    # Remove markers
                    item = re.sub(r'^[-*•]\s*', '', line).strip()
                    item = re.sub(r'^\d+\.\s*', '', item).strip()
                    if item:
                        items.append(item)
            
            return items
            
        except Exception as e:
            self.logger.error(f"List extraction failed: {e}")
            return []
