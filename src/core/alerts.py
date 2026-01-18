"""
Alerting System

Manages high-impact signal alerts and notifications.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import os

from data.db import Database


class AlertManager:
    """
    Manages high-impact signal alerts and notifications.
    
    Logs alerts to database and can send notifications via Discord/email.
    """
    
    def __init__(self, db: Optional[Database] = None):
        """
        Initialize alert manager.
        
        Args:
            db: Database instance (creates new if None)
        """
        self.db = db or Database()
        self.logger = logging.getLogger("futureoracle.alerts")
        
        # Initialize alerts table
        self._initialize_alerts_table()
    
    def _initialize_alerts_table(self):
        """Create alerts table if it doesn't exist"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT,
                    impact_score INTEGER,
                    article_url TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    acknowledged BOOLEAN DEFAULT 0
                )
            """)
            self.db.conn.commit()
            self.logger.info("Alerts table initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize alerts table: {e}")
    
    def create_high_impact_alert(
        self,
        analysis: Dict[str, Any],
        threshold: int = 8
    ) -> Optional[int]:
        """
        Create alert for high-impact signal.
        
        Args:
            analysis: Analyst output dictionary
            threshold: Minimum impact score for alert
        
        Returns:
            Alert ID if created, None otherwise
        """
        impact_score = analysis.get("impact_score", 0)
        
        if impact_score < threshold:
            return None
        
        try:
            # Determine severity
            if impact_score >= 9:
                severity = "CRITICAL"
            elif impact_score >= 8:
                severity = "HIGH"
            else:
                severity = "MEDIUM"
            
            # Build alert message
            title = f"High-Impact Signal: {analysis.get('article_title', 'Unknown')}"
            
            message = f"""
Impact Score: {impact_score}/10
Sentiment: {analysis.get('sentiment', 'N/A').upper()}
Source: {analysis.get('article_source', 'Unknown')}

Key Insight:
{analysis.get('key_insight', 'N/A')}

30-Day Outlook:
{analysis.get('price_target_30d', 'N/A')}

Risk Flags:
{self._format_list(analysis.get('risks', []))}

Long-Term Scenarios:
{self._format_scenarios(analysis.get('scenarios', {}))}
            """.strip()
            
            # Store metadata as JSON string
            import json
            metadata = json.dumps({
                "relevance_score": analysis.get("relevance_score"),
                "analyzed_at": analysis.get("analyzed_at"),
                "grok_model": analysis.get("grok_model"),
                "is_fallback": analysis.get("is_fallback", False)
            })
            
            # Insert alert
            cursor = self.db.conn.cursor()
            cursor.execute("""
                INSERT INTO alerts (alert_type, severity, title, message, impact_score, article_url, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "HIGH_IMPACT_SIGNAL",
                severity,
                title,
                message,
                impact_score,
                analysis.get("article_url"),
                metadata
            ))
            
            self.db.conn.commit()
            alert_id = cursor.lastrowid
            
            self.logger.info(f"Created {severity} alert (ID: {alert_id}) for impact score {impact_score}/10")
            
            # Send notifications if configured
            self._send_notifications(severity, title, message, analysis.get("article_url"))
            
            return alert_id
            
        except Exception as e:
            self.logger.error(f"Failed to create alert: {e}")
            return None
    
    def get_recent_alerts(
        self,
        hours: int = 24,
        min_severity: str = "MEDIUM",
        unacknowledged_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get recent alerts.
        
        Args:
            hours: Number of hours to look back
            min_severity: Minimum severity level (MEDIUM, HIGH, CRITICAL)
            unacknowledged_only: Only return unacknowledged alerts
        
        Returns:
            List of alert dictionaries
        """
        try:
            cursor = self.db.conn.cursor()
            
            # Build query
            query = """
                SELECT * FROM alerts 
                WHERE datetime(created_at) >= datetime('now', '-' || ? || ' hours')
            """
            params = [hours]
            
            # Severity filter
            severity_levels = {"MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
            min_level = severity_levels.get(min_severity, 1)
            
            if min_level >= 2:
                query += " AND severity IN ('HIGH', 'CRITICAL')"
            elif min_level >= 3:
                query += " AND severity = 'CRITICAL'"
            
            # Acknowledged filter
            if unacknowledged_only:
                query += " AND acknowledged = 0"
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            
            alerts = []
            for row in cursor.fetchall():
                alerts.append(dict(row))
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Failed to get recent alerts: {e}")
            return []
    
    def acknowledge_alert(self, alert_id: int):
        """Mark alert as acknowledged"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("""
                UPDATE alerts SET acknowledged = 1 WHERE id = ?
            """, (alert_id,))
            self.db.conn.commit()
            self.logger.info(f"Acknowledged alert ID {alert_id}")
        except Exception as e:
            self.logger.error(f"Failed to acknowledge alert: {e}")
    
    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get summary of recent alerts.
        
        Args:
            hours: Number of hours to look back
        
        Returns:
            Summary dictionary with counts by severity
        """
        try:
            cursor = self.db.conn.cursor()
            
            cursor.execute("""
                SELECT 
                    severity,
                    COUNT(*) as count,
                    SUM(CASE WHEN acknowledged = 0 THEN 1 ELSE 0 END) as unacknowledged
                FROM alerts
                WHERE datetime(created_at) >= datetime('now', '-' || ? || ' hours')
                GROUP BY severity
            """, (hours,))
            
            summary = {
                "total": 0,
                "unacknowledged": 0,
                "by_severity": {}
            }
            
            for row in cursor.fetchall():
                severity = row["severity"]
                count = row["count"]
                unack = row["unacknowledged"]
                
                summary["total"] += count
                summary["unacknowledged"] += unack
                summary["by_severity"][severity] = {
                    "count": count,
                    "unacknowledged": unack
                }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get alert summary: {e}")
            return {"total": 0, "unacknowledged": 0, "by_severity": {}}
    
    def _send_notifications(self, severity: str, title: str, message: str, url: Optional[str] = None):
        """
        Send notifications via configured channels.
        
        Args:
            severity: Alert severity
            title: Alert title
            message: Alert message
            url: Optional article URL
        """
        # Discord webhook
        discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        if discord_webhook:
            try:
                self._send_discord_notification(discord_webhook, severity, title, message, url)
            except Exception as e:
                self.logger.error(f"Failed to send Discord notification: {e}")
        
        # Email (future implementation)
        # smtp_config = os.getenv("SMTP_CONFIG")
        # if smtp_config:
        #     self._send_email_notification(...)
    
    def _send_discord_notification(
        self,
        webhook_url: str,
        severity: str,
        title: str,
        message: str,
        url: Optional[str] = None
    ):
        """Send notification to Discord webhook"""
        try:
            import requests
            
            # Color based on severity
            colors = {
                "CRITICAL": 0xFF0000,  # Red
                "HIGH": 0xFF6600,      # Orange
                "MEDIUM": 0xFFCC00     # Yellow
            }
            color = colors.get(severity, 0xFFCC00)
            
            # Build embed
            embed = {
                "title": f"🚨 {title}",
                "description": message[:2000],  # Discord limit
                "color": color,
                "timestamp": datetime.now().isoformat(),
                "footer": {"text": "FutureOracle Alert System"}
            }
            
            if url:
                embed["url"] = url
            
            payload = {
                "embeds": [embed]
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            self.logger.info(f"Sent Discord notification for {severity} alert")
            
        except Exception as e:
            self.logger.error(f"Discord notification failed: {e}")
            raise
    
    def _format_list(self, items: List[str]) -> str:
        """Format list items for message"""
        if not items:
            return "None"
        return "\n".join(f"- {item}" for item in items)
    
    def _format_scenarios(self, scenarios: Dict[str, str]) -> str:
        """Format scenarios for message"""
        if not scenarios:
            return "N/A"
        
        lines = []
        for timeframe, scenario in scenarios.items():
            if scenario and scenario != "N/A":
                lines.append(f"- {timeframe}: {scenario}")
        
        return "\n".join(lines) if lines else "N/A"
