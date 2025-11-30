"""
Type definitions for Agent Guardrails SDK.

This module defines all core data models using Pydantic v2 for validation and serialization.
All amounts are represented as Decimal to avoid floating-point precision issues.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


class LimitConfig(BaseModel):
    """
    Configuration for a spending limit on a specific asset.

    Attributes:
        asset: Asset symbol (e.g., "USDC", "ETH")
        amount: Maximum amount allowed within the time window
        window_seconds: Time window in seconds for the limit
    """
    asset: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)
    window_seconds: int = Field(..., gt=0)

    @field_validator('amount', mode='before')
    @classmethod
    def convert_to_decimal(cls, v: Any) -> Decimal:
        """Convert string or numeric input to Decimal."""
        if isinstance(v, Decimal):
            return v
        return Decimal(str(v))

    class Config:
        json_encoders = {
            Decimal: str
        }


class AllowRule(BaseModel):
    """
    Rule defining an allowed action with optional constraints.

    Attributes:
        action_type: Type of action (e.g., "swap", "transfer", "stake")
        constraints: Key-value pairs that must match for authorization
    """
    action_type: str = Field(..., min_length=1)
    constraints: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            Decimal: str
        }


class AgentConfig(BaseModel):
    """
    Complete configuration for an agent.

    Attributes:
        agent_id: Unique identifier for the agent
        wallet: Wallet address associated with the agent
        name: Optional human-readable name
        metadata: Optional additional metadata
        limits: Spending limits keyed by asset symbol
        allow_rules: List of allowed action rules
    """
    agent_id: str = Field(..., min_length=1)
    wallet: str = Field(..., min_length=1)
    name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    limits: Dict[str, LimitConfig] = Field(default_factory=dict)
    allow_rules: List[AllowRule] = Field(default_factory=list)

    class Config:
        json_encoders = {
            Decimal: str
        }


class ActionParams(BaseModel):
    """
    Parameters for an action to be authorized.

    This model supports both structured fields and arbitrary additional parameters.

    Attributes:
        asset: Optional asset symbol
        amount: Optional amount as Decimal
        protocol: Optional protocol identifier
        chain_id: Optional blockchain ID
        to_address: Optional destination address
        extra: Additional parameters passed as dict
    """
    asset: Optional[str] = None
    amount: Optional[Decimal] = None
    protocol: Optional[str] = None
    chain_id: Optional[int] = None
    to_address: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('amount', mode='before')
    @classmethod
    def convert_to_decimal(cls, v: Any) -> Optional[Decimal]:
        """Convert string or numeric input to Decimal."""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v
        return Decimal(str(v))

    @classmethod
    def from_dict(cls, params: Dict[str, Any]) -> 'ActionParams':
        """
        Create ActionParams from a raw dictionary.

        Known fields are mapped to structured attributes,
        unknown fields are stored in extra.
        """
        known_fields = {'asset', 'amount', 'protocol', 'chain_id', 'to_address'}
        structured = {k: v for k, v in params.items() if k in known_fields}
        extra = {k: v for k, v in params.items() if k not in known_fields}
        structured['extra'] = extra
        return cls(**structured)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a flat dictionary for comparison.

        Returns all non-None structured fields plus extra fields.
        """
        result = {}
        if self.asset is not None:
            result['asset'] = self.asset
        if self.amount is not None:
            result['amount'] = str(self.amount)
        if self.protocol is not None:
            result['protocol'] = self.protocol
        if self.chain_id is not None:
            result['chain_id'] = self.chain_id
        if self.to_address is not None:
            result['to_address'] = self.to_address
        result.update(self.extra)
        return result

    class Config:
        json_encoders = {
            Decimal: str
        }


class LogEntry(BaseModel):
    """
    Audit log entry for an authorization decision.

    Attributes:
        timestamp: ISO 8601 formatted timestamp
        agent_id: Agent that requested authorization
        action_type: Type of action requested
        params: Parameters of the action
        allowed: Whether the action was allowed
        reason: Optional reason for denial
    """
    timestamp: str
    agent_id: str
    action_type: str
    params: Dict[str, Any]
    allowed: bool
    reason: Optional[str] = None

    @classmethod
    def create(
        cls,
        agent_id: str,
        action_type: str,
        params: Dict[str, Any],
        allowed: bool,
        reason: Optional[str] = None,
    ) -> 'LogEntry':
        """Create a log entry with current timestamp."""
        return cls(
            timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            agent_id=agent_id,
            action_type=action_type,
            params=params,
            allowed=allowed,
            reason=reason,
        )

    class Config:
        json_encoders = {
            Decimal: str
        }
