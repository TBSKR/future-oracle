"""
Reporter Agent

Compiles weekly reports with top news, portfolio snapshot, and forecast updates.
Generates stunning HTML emails using Jinja templates and sends via smtplib.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from agents.base import BaseAgent
from data.db import Database
from core.portfolio import PortfolioManager


class ReporterAgent(BaseAgent):
    """
    Reporter Agent - Generates and sends weekly HTML email reports.
    """
    
    def __init__(self, db: Optional[Database] = None, portfolio: Optional[PortfolioManager] = None):
        """
        Initialize Reporter Agent.
        
        Args:
            db: Optional Database instance
            portfolio: Optional PortfolioManager instance
        """
        super().__init__(
            name="reporter",
            role="Weekly Reporter",
            goal="Compile and deliver weekly investment intelligence reports",
            backstory="Expert at synthesizing complex data into actionable insights"
        )
        
        self.db = db or Database()
        self.portfolio = portfolio or PortfolioManager(self.db)
        
        # Initialize Jinja environment
        template_dir = Path(__file__).parent.parent / "templates"
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        self.logger.info(f"Jinja environment initialized from {template_dir}")
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate and send weekly report.
        
        Args:
            inputs: Dictionary containing:
                - send_email: bool (default: True)
                - recipient_email: str (optional, overrides config)
                - days_back: int (default: 7)
        
        Returns:
            Dictionary with:
                - success: bool
                - message: str
                - html_report: str (generated HTML)
                - error: Optional error message
        """
        try:
            send_email = inputs.get("send_email", True)
            days_back = inputs.get("days_back", 7)
            
            self.logger.info("Generating weekly report...")
            
            # 1. Gather data
            report_data = self._gather_report_data(days_back)
            
            # 2. Generate HTML
            html_report = self._generate_html_report(report_data)
            
            # 3. Send email
            if send_email:
                recipient = inputs.get("recipient_email") or os.getenv("SMTP_RECIPIENT")
                if not recipient:
                    raise ValueError("Recipient email not configured")
                
                self._send_email_report(recipient, html_report)
                message = f"Weekly report sent to {recipient}"
            else:
                message = "Weekly report generated successfully (email not sent)"
            
            return {
                "success": True,
                "message": message,
                "html_report": html_report
            }
            
        except Exception as e:
            self.logger.error(f"Report generation failed: {e}")
            return {
                "success": False,
                "message": "Report generation failed",
                "html_report": "",
                "error": str(e)
            }
    
    def _gather_report_data(self, days_back: int) -> Dict[str, Any]:
        """
        Gather all data needed for the weekly report.
        
        Args:
            days_back: Number of days to look back for news
        
        Returns:
            Dictionary with all report data
        """
        try:
            # Get top news/analyses (placeholder - needs Analyst integration)
            # For now, we get top Scout signals
            top_signals = self.db.get_cached_signals(limit=5, days_back=days_back)
            
            # Get portfolio snapshot
            portfolio_summary = self.portfolio.get_portfolio_summary()
            
            # Get forecast update (placeholder - needs Forecaster integration)
            # For now, we use a static example
            forecast_summary = {
                "age_31_super_bull": 150000,
                "age_41_super_bull": 1200000,
                "age_51_super_bull": 8000000
            }
            
            # Generate charts (placeholder - needs chart generation)
            # For now, we use placeholder images
            charts = {
                "portfolio_chart": "path/to/portfolio_chart.png",
                "forecast_chart": "path/to/forecast_chart.png"
            }
            
            return {
                "report_date": datetime.now().strftime("%B %d, %Y"),
                "top_signals": top_signals,
                "portfolio_summary": portfolio_summary,
                "forecast_summary": forecast_summary,
                "charts": charts
            }
            
        except Exception as e:
            self.logger.error(f"Failed to gather report data: {e}")
            raise
    
    def _generate_html_report(self, data: Dict[str, Any]) -> str:
        """
        Generate HTML report from data using Jinja template.
        
        Args:
            data: Report data dictionary
        
        Returns:
            Generated HTML string
        """
        try:
            template = self.jinja_env.get_template("weekly_report.html")
            
            # Add helper functions to template context
            template.globals["format_currency"] = lambda x: f"€{x:,.0f}"
            template.globals["format_percent"] = lambda x: f"{x:.2f}%"
            
            # Render template
            html = template.render(data)
            
            self.logger.info("HTML report generated successfully")
            return html
            
        except Exception as e:
            self.logger.error(f"HTML report generation failed: {e}")
            raise
    
    def _send_email_report(self, recipient: str, html_report: str):
        """
        Send HTML email report via SMTP.
        
        Args:
            recipient: Recipient email address
            html_report: HTML report string
        """
        try:
            # Get SMTP config from environment
            smtp_host = os.getenv("SMTP_HOST")
            smtp_port = int(os.getenv("SMTP_PORT", 587))
            smtp_user = os.getenv("SMTP_USER")
            smtp_password = os.getenv("SMTP_PASSWORD")
            
            if not all([smtp_host, smtp_port, smtp_user, smtp_password]):
                raise ValueError("SMTP configuration not found in environment")
            
            # Create message
            msg = MIMEMultipart("related")
            report_date = datetime.now().strftime("%Y-%m-%d")
            msg["Subject"] = f"🔮 FutureOracle Weekly Report - {report_date}"
            msg["From"] = smtp_user
            msg["To"] = recipient
            
            # Attach HTML
            msg.attach(MIMEText(html_report, "html"))
            
            # Attach images (placeholder - needs real chart paths)
            # self._attach_image(msg, "portfolio_chart", "path/to/portfolio_chart.png")
            # self._attach_image(msg, "forecast_chart", "path/to/forecast_chart.png")
            
            # Send email
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, recipient, msg.as_string())
            
            self.logger.info(f"Email report sent to {recipient}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email report: {e}")
            raise
    
    def _attach_image(self, msg: MIMEMultipart, cid: str, image_path: str):
        """
        Attach image to email with CID for embedding.
        
        Args:
            msg: MIMEMultipart message object
            cid: Content-ID for the image
            image_path: Path to the image file
        """
        try:
            with open(image_path, "rb") as f:
                img = MIMEImage(f.read())
            
            img.add_header("Content-ID", f"<{cid}>")
            msg.attach(img)
            
            self.logger.info(f"Attached image {image_path} with CID {cid}")
            
        except Exception as e:
            self.logger.error(f"Failed to attach image {image_path}: {e}")
