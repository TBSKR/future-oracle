"""
FutureOracle Agents Module

This module contains all the AI agents that power the FutureOracle system.
Each agent is specialized for a specific task in the intelligence workflow.
"""

from .base import BaseAgent
from .scout import ScoutAgent
from .analyst import AnalystAgent
from .forecaster import ForecasterAgent

# Import agents as they are implemented
# from .orchestrator import OrchestratorAgent
# from .curator import CuratorAgent
from .reporter import ReporterAgent
# from .guardian import GuardianAgent

__all__ = [
    'BaseAgent',
    'ScoutAgent',
    'AnalystAgent',
    'ForecasterAgent',
    # 'OrchestratorAgent',
    # 'CuratorAgent',
    'ReporterAgent',
    # 'GuardianAgent',
]
