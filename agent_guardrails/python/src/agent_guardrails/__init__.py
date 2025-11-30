"""
Agent Guardrails SDK

Lightweight safety, permissions, and spend limits for autonomous AI agents.

This SDK provides a zero-custody, zero-network authorization layer for AI agents
interacting with financial operations. Define limits, allowlists, and policies
to safely constrain agent behavior.

Example:
    >>> from agent_guardrails import Agent
    >>>
    >>> agent = Agent.register(wallet="0x123", name="payments_bot")
    >>> agent.set_limit("USDC", "25", "24h")
    >>> agent.allow_action("swap", protocol="UniswapV3")
    >>>
    >>> if agent.authorize("swap", {"token": "USDC", "amount": "5", "protocol": "UniswapV3"}):
    ...     print("Action authorized")
"""

from .agent import Agent
from .types import AgentConfig, LimitConfig, AllowRule, ActionParams
from .errors import AuthorizationError

__version__ = "0.1.0"

__all__ = [
    "Agent",
    "AgentConfig",
    "LimitConfig",
    "AllowRule",
    "ActionParams",
    "AuthorizationError",
]
