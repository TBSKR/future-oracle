"""
Database Module

SQLite database for portfolio tracking, holdings, and historical data.
"""

import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import logging
import os


class Database:
    """
    SQLite database manager for FutureOracle.
    
    Handles portfolio holdings, transactions, and historical snapshots.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file (defaults to data/futureoracle.db)
        """
        if db_path is None:
            db_path = os.getenv("DATABASE_PATH", "data/futureoracle.db")
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("futureoracle.database")
        self.conn = None
        
        self._connect()
        self._initialize_schema()
    
    def _connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access
        self.logger.info(f"Connected to database: {self.db_path}")
    
    def _initialize_schema(self):
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Holdings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                shares REAL NOT NULL,
                avg_price REAL NOT NULL,
                purchase_date TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                transaction_type TEXT NOT NULL,  -- BUY, SELL
                shares REAL NOT NULL,
                price REAL NOT NULL,
                transaction_date TEXT NOT NULL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Portfolio snapshots table (for historical tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date TEXT NOT NULL,
                total_value REAL NOT NULL,
                total_cost REAL NOT NULL,
                total_return_pct REAL,
                holdings_json TEXT,  -- JSON string of all holdings
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Scout signals cache (optional, for dashboard performance)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scout_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                source TEXT,
                url TEXT UNIQUE,
                summary TEXT,
                relevance_score INTEGER,
                matched_keywords TEXT,  -- JSON array
                published_at TEXT,
                fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Chat history (assistive memory fallback when vector memory is unavailable)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                intent TEXT,
                tickers TEXT,
                metadata_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()
        self.logger.info("Database schema initialized")
    
    # ========== Holdings CRUD ==========
    
    def add_holding(
        self,
        ticker: str,
        shares: float,
        avg_price: float,
        purchase_date: Optional[str] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Add a new holding to the portfolio.
        
        Args:
            ticker: Stock ticker symbol
            shares: Number of shares
            avg_price: Average purchase price
            purchase_date: Date of purchase (ISO format)
            notes: Optional notes
        
        Returns:
            ID of the inserted holding
        """
        cursor = self.conn.cursor()
        
        if purchase_date is None:
            purchase_date = datetime.now().date().isoformat()
        
        cursor.execute("""
            INSERT INTO holdings (ticker, shares, avg_price, purchase_date, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (ticker, shares, avg_price, purchase_date, notes))
        
        self.conn.commit()
        holding_id = cursor.lastrowid
        
        self.logger.info(f"Added holding: {shares} shares of {ticker} at ${avg_price}")
        return holding_id
    
    def get_all_holdings(self) -> List[Dict[str, Any]]:
        """
        Get all current holdings.
        
        Returns:
            List of holding dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM holdings ORDER BY ticker")
        
        holdings = []
        for row in cursor.fetchall():
            holdings.append(dict(row))
        
        return holdings
    
    def get_holding_by_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get holding for a specific ticker"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM holdings WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()
        
        return dict(row) if row else None
    
    def update_holding(
        self,
        holding_id: int,
        shares: Optional[float] = None,
        avg_price: Optional[float] = None,
        notes: Optional[str] = None
    ):
        """Update an existing holding"""
        cursor = self.conn.cursor()
        
        updates = []
        params = []
        
        if shares is not None:
            updates.append("shares = ?")
            params.append(shares)
        
        if avg_price is not None:
            updates.append("avg_price = ?")
            params.append(avg_price)
        
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        
        params.append(holding_id)
        
        query = f"UPDATE holdings SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        self.conn.commit()
        
        self.logger.info(f"Updated holding ID {holding_id}")
    
    def delete_holding(self, holding_id: int):
        """Delete a holding"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM holdings WHERE id = ?", (holding_id,))
        self.conn.commit()
        
        self.logger.info(f"Deleted holding ID {holding_id}")
    
    # ========== Transactions ==========
    
    def add_transaction(
        self,
        ticker: str,
        transaction_type: str,
        shares: float,
        price: float,
        transaction_date: Optional[str] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Record a transaction (BUY or SELL).
        
        Args:
            ticker: Stock ticker
            transaction_type: "BUY" or "SELL"
            shares: Number of shares
            price: Price per share
            transaction_date: Date of transaction (ISO format)
            notes: Optional notes
        
        Returns:
            Transaction ID
        """
        cursor = self.conn.cursor()
        
        if transaction_date is None:
            transaction_date = datetime.now().date().isoformat()
        
        cursor.execute("""
            INSERT INTO transactions (ticker, transaction_type, shares, price, transaction_date, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ticker, transaction_type.upper(), shares, price, transaction_date, notes))
        
        self.conn.commit()
        transaction_id = cursor.lastrowid
        
        self.logger.info(f"Recorded {transaction_type}: {shares} shares of {ticker} at ${price}")
        return transaction_id
    
    def get_transactions(
        self,
        ticker: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get transaction history.
        
        Args:
            ticker: Filter by ticker (optional)
            limit: Maximum number of transactions to return
        
        Returns:
            List of transaction dictionaries
        """
        cursor = self.conn.cursor()
        
        if ticker:
            cursor.execute("""
                SELECT * FROM transactions 
                WHERE ticker = ? 
                ORDER BY transaction_date DESC 
                LIMIT ?
            """, (ticker, limit))
        else:
            cursor.execute("""
                SELECT * FROM transactions 
                ORDER BY transaction_date DESC 
                LIMIT ?
            """, (limit,))
        
        transactions = []
        for row in cursor.fetchall():
            transactions.append(dict(row))
        
        return transactions
    
    # ========== Portfolio Snapshots ==========
    
    def save_portfolio_snapshot(
        self,
        total_value: float,
        total_cost: float,
        holdings_json: str
    ):
        """
        Save a portfolio snapshot for historical tracking.
        
        Args:
            total_value: Current total portfolio value
            total_cost: Total cost basis
            holdings_json: JSON string of all holdings
        """
        cursor = self.conn.cursor()
        
        total_return_pct = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
        
        cursor.execute("""
            INSERT INTO portfolio_snapshots (snapshot_date, total_value, total_cost, total_return_pct, holdings_json)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime.now().date().isoformat(), total_value, total_cost, total_return_pct, holdings_json))
        
        self.conn.commit()
        self.logger.info(f"Saved portfolio snapshot: ${total_value:.2f}")
    
    def get_portfolio_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get portfolio snapshots for the last N days"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM portfolio_snapshots 
            ORDER BY snapshot_date DESC 
            LIMIT ?
        """, (days,))
        
        snapshots = []
        for row in cursor.fetchall():
            snapshots.append(dict(row))
        
        return snapshots
    
    # ========== Scout Signals Cache ==========
    
    def cache_scout_signal(self, signal: Dict[str, Any]):
        """Cache a scout signal for dashboard performance"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO scout_signals 
                (title, source, url, summary, relevance_score, matched_keywords, published_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.get("title"),
                signal.get("source"),
                signal.get("url"),
                signal.get("description"),
                signal.get("relevance_score"),
                str(signal.get("matched_keywords", [])),
                signal.get("published_at")
            ))
            self.conn.commit()
        except sqlite3.IntegrityError:
            # URL already exists, skip
            pass
    
    def get_cached_signals(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get cached scout signals"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM scout_signals 
            ORDER BY fetched_at DESC 
            LIMIT ?
        """, (limit,))
        
        signals = []
        for row in cursor.fetchall():
            signals.append(dict(row))
        
        return signals
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")

    # ========== Chat History ==========

    def save_chat_message(
        self,
        session_id: str,
        role: str,
        content: str,
        intent: Optional[str] = None,
        tickers: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Persist a chat message for local fallback memory."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO chat_history (session_id, role, content, intent, tickers, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            role,
            content,
            intent,
            ",".join(tickers or []),
            str(metadata or {}),
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_recent_chat_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent chat messages for a session."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM chat_history
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (session_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    def search_chat_messages(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Basic LIKE search for fallback chat memory."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM chat_history
            WHERE content LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (f"%{query_text}%", limit))
        return [dict(row) for row in cursor.fetchall()]
