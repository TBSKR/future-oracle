"""
Portfolio Tracking Module

Manages portfolio holdings, calculates performance metrics,
and provides rebalancing suggestions.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import json

from data.db import Database
from data.market import MarketDataFetcher


class PortfolioManager:
    """
    Manages portfolio holdings and performance tracking.
    
    Supports paper trading mode and real broker integration (future).
    """
    
    def __init__(self, db: Optional[Database] = None):
        """
        Initialize portfolio manager.

        Args:
            db: Database instance (creates new if None)
        """
        self.db = db or Database()
        self.market = MarketDataFetcher()
        self.logger = logging.getLogger("futureoracle.portfolio")

    def get_all_positions(self) -> List[Dict[str, Any]]:
        """
        Get all portfolio positions.

        Returns:
            List of holdings, empty list if none or error
        """
        try:
            holdings = self.db.get_all_holdings()
            return holdings if holdings else []
        except Exception as e:
            self.logger.warning(f"Error fetching positions: {e}")
            return []

    @property
    def position_count(self) -> int:
        """Return the number of positions in the portfolio."""
        positions = self.get_all_positions() or []
        return len(positions)
    
    def add_position(
        self,
        ticker: str,
        shares: float,
        avg_price: float,
        purchase_date: Optional[str] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Add a new position to the portfolio.
        
        Args:
            ticker: Stock ticker symbol
            shares: Number of shares
            avg_price: Average purchase price
            purchase_date: Date of purchase
            notes: Optional notes
        
        Returns:
            Holding ID
        """
        # Check if holding already exists
        existing = self.db.get_holding_by_ticker(ticker)
        
        if existing:
            # Update existing holding (average down/up)
            old_shares = existing["shares"]
            old_avg = existing["avg_price"]
            
            new_shares = old_shares + shares
            new_avg = ((old_shares * old_avg) + (shares * avg_price)) / new_shares
            
            self.db.update_holding(
                holding_id=existing["id"],
                shares=new_shares,
                avg_price=new_avg
            )
            
            self.logger.info(f"Updated {ticker}: {old_shares} -> {new_shares} shares, avg ${new_avg:.2f}")
            return existing["id"]
        else:
            # Add new holding
            holding_id = self.db.add_holding(ticker, shares, avg_price, purchase_date, notes)
            
            # Record transaction
            self.db.add_transaction(
                ticker=ticker,
                transaction_type="BUY",
                shares=shares,
                price=avg_price,
                transaction_date=purchase_date,
                notes=notes
            )
            
            return holding_id
    
    def remove_position(self, ticker: str, shares: Optional[float] = None):
        """
        Remove or reduce a position.
        
        Args:
            ticker: Stock ticker
            shares: Number of shares to sell (None = sell all)
        """
        holding = self.db.get_holding_by_ticker(ticker)
        
        if not holding:
            self.logger.warning(f"No holding found for {ticker}")
            return
        
        current_shares = holding["shares"]
        
        if shares is None or shares >= current_shares:
            # Sell all
            self.db.delete_holding(holding["id"])
            self.logger.info(f"Removed all {current_shares} shares of {ticker}")
        else:
            # Partial sell
            new_shares = current_shares - shares
            self.db.update_holding(holding["id"], shares=new_shares)
            self.logger.info(f"Reduced {ticker}: {current_shares} -> {new_shares} shares")
        
        # Record transaction
        current_price = self.market.get_current_price(ticker) or holding["avg_price"]
        self.db.add_transaction(
            ticker=ticker,
            transaction_type="SELL",
            shares=shares or current_shares,
            price=current_price
        )
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive portfolio summary with current values.
        
        Returns:
            Dictionary with portfolio metrics
        """
        holdings = self.db.get_all_holdings()
        
        if not holdings:
            return {
                "total_value": 0,
                "total_cost": 0,
                "total_return": 0,
                "total_return_pct": 0,
                "positions": [],
                "timestamp": datetime.now().isoformat()
            }
        
        positions = []
        total_value = 0
        total_cost = 0
        
        for holding in holdings:
            ticker = holding["ticker"]
            shares = holding["shares"]
            avg_price = holding["avg_price"]
            cost_basis = shares * avg_price
            
            # Get current price
            current_price = self.market.get_current_price(ticker)
            
            if current_price:
                current_value = shares * current_price
                gain_loss = current_value - cost_basis
                gain_loss_pct = (gain_loss / cost_basis * 100) if cost_basis > 0 else 0
            else:
                current_value = cost_basis
                gain_loss = 0
                gain_loss_pct = 0
                self.logger.warning(f"Could not fetch price for {ticker}, using cost basis")
            
            positions.append({
                "ticker": ticker,
                "shares": shares,
                "avg_price": avg_price,
                "current_price": current_price,
                "cost_basis": cost_basis,
                "current_value": current_value,
                "gain_loss": gain_loss,
                "gain_loss_pct": gain_loss_pct,
                "purchase_date": holding.get("purchase_date"),
                "notes": holding.get("notes")
            })
            
            total_value += current_value
            total_cost += cost_basis
        
        total_return = total_value - total_cost
        total_return_pct = (total_return / total_cost * 100) if total_cost > 0 else 0
        
        # Save snapshot
        self.db.save_portfolio_snapshot(
            total_value=total_value,
            total_cost=total_cost,
            holdings_json=json.dumps(positions)
        )
        
        return {
            "total_value": total_value,
            "total_cost": total_cost,
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            "positions": positions,
            "position_count": len(positions),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_position_details(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific position.
        
        Args:
            ticker: Stock ticker
        
        Returns:
            Position details dictionary
        """
        holding = self.db.get_holding_by_ticker(ticker)
        
        if not holding:
            return None
        
        # Get current market data
        quote = self.market.get_quote(ticker)
        returns = self.market.calculate_returns(ticker)
        
        shares = holding["shares"]
        avg_price = holding["avg_price"]
        cost_basis = shares * avg_price
        
        current_price = quote.get("price") or avg_price
        current_value = shares * current_price
        gain_loss = current_value - cost_basis
        gain_loss_pct = (gain_loss / cost_basis * 100) if cost_basis > 0 else 0
        
        return {
            "ticker": ticker,
            "company_name": quote.get("company_name"),
            "shares": shares,
            "avg_price": avg_price,
            "current_price": current_price,
            "cost_basis": cost_basis,
            "current_value": current_value,
            "gain_loss": gain_loss,
            "gain_loss_pct": gain_loss_pct,
            "market_data": quote,
            "returns": returns,
            "purchase_date": holding.get("purchase_date"),
            "notes": holding.get("notes"),
            "transactions": self.db.get_transactions(ticker=ticker)
        }
    
    def get_performance_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get portfolio performance history.
        
        Args:
            days: Number of days to retrieve
        
        Returns:
            List of historical snapshots
        """
        return self.db.get_portfolio_history(days=days)
    
    def calculate_allocation(self) -> Dict[str, float]:
        """
        Calculate current portfolio allocation by ticker.
        
        Returns:
            Dictionary mapping ticker to allocation percentage
        """
        summary = self.get_portfolio_summary()
        total_value = summary["total_value"]
        
        if total_value == 0:
            return {}
        
        allocation = {}
        for position in summary["positions"]:
            ticker = position["ticker"]
            value = position["current_value"]
            allocation[ticker] = (value / total_value) * 100
        
        return allocation
