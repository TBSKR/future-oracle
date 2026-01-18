"""
Grok API Client

Wrapper for xAI's Grok API (OpenAI-compatible interface).
Handles authentication, rate limiting, retries, and error handling.
"""

import os
from typing import Dict, Any, Optional, List
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
import logging


class GrokClient:
    """
    Client for interacting with xAI's Grok API.
    
    Uses OpenAI-compatible interface for seamless integration.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "grok-beta",
        max_retries: int = 3
    ):
        """
        Initialize Grok client.
        
        Args:
            api_key: xAI API key (defaults to XAI_API_KEY env var)
            base_url: API base URL (defaults to XAI_API_BASE env var)
            model: Model name to use
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        self.base_url = base_url or os.getenv("XAI_API_BASE", "https://api.x.ai/v1")
        self.model = model
        self.max_retries = max_retries
        
        if not self.api_key:
            raise ValueError("XAI_API_KEY not found in environment variables")
        
        # Initialize OpenAI client with xAI endpoint
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        self.logger = logging.getLogger("futureoracle.grok_client")
        self.logger.info(f"GrokClient initialized with model: {self.model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        Generate a chat completion using Grok.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for the API
            
        Returns:
            Generated text response
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            content = response.choices[0].message.content
            self.logger.debug(f"Generated {len(content)} characters")
            return content
            
        except Exception as e:
            self.logger.error(f"Grok API error: {str(e)}")
            raise
    
    def analyze_with_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Convenience method for simple system + user prompt pattern.
        
        Args:
            system_prompt: System message (agent persona/instructions)
            user_prompt: User message (task/question)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def __repr__(self) -> str:
        return f"<GrokClient model={self.model}>"
