"""
Base Agent Class for FutureOracle

All agents inherit from this base class to ensure consistency
and provide common functionality like logging, error handling,
and configuration management.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from datetime import datetime


class BaseAgent(ABC):
    """
    Abstract base class for all FutureOracle agents.
    
    Attributes:
        name: Agent name (e.g., "Scout", "Analyst")
        role: Agent's role description
        goal: Agent's primary objective
        backstory: Agent's persona/context
        config: Agent-specific configuration from agents.yaml
    """
    
    def __init__(
        self,
        name: str,
        role: str,
        goal: str,
        backstory: str,
        config: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.config = config or {}
        
        # Setup logging
        self.logger = self._setup_logger()
        self.logger.info(f"{self.name} agent initialized")
    
    def _setup_logger(self) -> logging.Logger:
        """Setup agent-specific logger"""
        logger = logging.getLogger(f"futureoracle.agents.{self.name.lower()}")
        logger.setLevel(logging.INFO)
        
        # Create handler if not exists
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's primary task.
        
        Args:
            context: Input data and parameters for the agent
            
        Returns:
            Dictionary containing the agent's output
        """
        pass
    
    def log_execution(self, context: Dict[str, Any], result: Dict[str, Any]):
        """Log agent execution details"""
        self.logger.info(f"Execution started at {datetime.now()}")
        self.logger.debug(f"Context: {context}")
        self.logger.info(f"Execution completed. Result keys: {list(result.keys())}")
    
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle errors during agent execution.
        
        Args:
            error: The exception that occurred
            context: The context in which the error occurred
            
        Returns:
            Error response dictionary
        """
        self.logger.error(f"Error in {self.name} agent: {str(error)}", exc_info=True)
        return {
            "success": False,
            "error": str(error),
            "agent": self.name,
            "timestamp": datetime.now().isoformat()
        }
    
    def __repr__(self) -> str:
        return f"<{self.name}Agent: {self.role}>"
