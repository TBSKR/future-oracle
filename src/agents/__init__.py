"""
FutureOracle Agents Module

This module contains all the AI agents that power the FutureOracle system.
Each agent is specialized for a specific task in the intelligence workflow.
"""

from .base import BaseAgent
from .scout import ScoutAgent

# Import agents as they are implemented
# from .orchestrator import OrchestratorAgent
# from .analyst import AnalystAgent
# from .curator import CuratorAgent
# from .reporter import ReporterAgent
# from .guardian import GuardianAgent
# from .forecaster import ForecasterAgent

__all__ = [
    'BaseAgent',
    'ScoutAgent',
    # 'OrchestratorAgent',
    # 'AnalystAgent',
    # 'CuratorAgent',
    # 'ReporterAgent',
    # 'GuardianAgent',
    # 'ForecasterAgent',
]
