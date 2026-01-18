#!/usr/bin/env python3
"""
Weekly Intelligence Report Script

Executes the weekly reporting workflow:
1. Reporter Agent compiles weekly data
2. Generates HTML email with top signals, portfolio snapshot, forecasts
3. Sends via SMTP and posts to Discord

Run via cron: 0 20 * * 0 /path/to/venv/bin/python /path/to/scripts/run_weekly.py
"""

import sys
from pathlib import Path
from datetime import datetime
import logging

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Load environment
from dotenv import load_dotenv
load_dotenv(project_root / "config" / ".env")

# Setup logging
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "weekly_report.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("futureoracle.weekly_report")

from agents.reporter import ReporterAgent
from data.db import Database
from core.portfolio import PortfolioManager


def main():
    """Execute weekly report workflow"""
    logger.info("=" * 80)
    logger.info(f"Weekly Intelligence Report Started: {datetime.now()}")
    logger.info("=" * 80)
    
    try:
        # Initialize components
        logger.info("Initializing components...")
        db = Database()
        portfolio = PortfolioManager(db)
        reporter = ReporterAgent(db=db, portfolio=portfolio)
        logger.info("✅ Components initialized")
        
        # Generate and send weekly report
        logger.info("Generating weekly report...")
        result = reporter.execute({
            "send_email": True,
            "days_back": 7
        })
        
        if result["success"]:
            logger.info(f"✅ {result['message']}")
            logger.info(f"   HTML report length: {len(result['html_report'])} characters")
        else:
            logger.error(f"❌ Report generation failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
        
        logger.info("=" * 80)
        logger.info("Weekly report completed successfully")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Weekly report failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
