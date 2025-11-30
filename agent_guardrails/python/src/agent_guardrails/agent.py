"""
Agent class for Agent Guardrails SDK.

This module provides the main Agent class that orchestrates
registration, policy management, and authorization.
"""

import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .types import AgentConfig, AllowRule, LimitConfig, LogEntry, ActionParams
from .storage import StorageDriver, JsonFileStorage
from .policies import (
    parse_time_window,
    is_action_allowed_by_rules,
    is_within_limits,
)


class Agent:
    """
    Agent represents an autonomous entity with spending limits and action constraints.

    The Agent class provides the primary interface for:
    - Registering agents with wallet addresses
    - Setting spending limits per asset
    - Defining allowed actions with constraints
    - Authorizing actions deterministically
    - Accessing audit logs

    All authorization decisions are deterministic, fail-safe, and logged locally.
    """

    def __init__(self, agent_id: str, storage: Optional[StorageDriver] = None):
        """
        Initialize an Agent instance.

        Args:
            agent_id: Unique identifier for this agent
            storage: Optional storage driver (defaults to JsonFileStorage)
        """
        self.agent_id = agent_id
        self.storage = storage if storage is not None else JsonFileStorage()
        self._config: Optional[AgentConfig] = None

    @classmethod
    def register(
        cls,
        wallet: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        storage: Optional[StorageDriver] = None,
    ) -> 'Agent':
        """
        Register a new agent with the specified wallet address.

        Creates a new agent configuration with a unique ID and saves it to storage.

        Args:
            wallet: Wallet address associated with this agent
            name: Optional human-readable name
            metadata: Optional additional metadata
            storage: Optional custom storage driver

        Returns:
            Initialized Agent instance

        Example:
            >>> agent = Agent.register(wallet="0x123", name="payments_bot")
        """
        agent_id = str(uuid.uuid4())

        config = AgentConfig(
            agent_id=agent_id,
            wallet=wallet,
            name=name,
            metadata=metadata or {},
            limits={},
            allow_rules=[],
        )

        storage_driver = storage if storage is not None else JsonFileStorage()
        storage_driver.save_agent(config)

        agent = cls(agent_id=agent_id, storage=storage_driver)
        agent._config = config
        return agent

    def _load_config(self) -> AgentConfig:
        """
        Load agent configuration from storage.

        Returns:
            Agent configuration

        Raises:
            RuntimeError: If agent configuration cannot be loaded
        """
        if self._config is None:
            self._config = self.storage.load_agent(self.agent_id)

        if self._config is None:
            raise RuntimeError(f"Agent {self.agent_id} not found in storage")

        return self._config

    def _save_config(self) -> None:
        """Save current agent configuration to storage."""
        if self._config is not None:
            self.storage.save_agent(self._config)

    def set_limit(
        self,
        asset: str,
        amount: str | float,
        window: str
    ) -> None:
        """
        Set or update a spending limit for an asset.

        Args:
            asset: Asset symbol (e.g., "USDC", "ETH")
            amount: Maximum amount as string or number
            window: Time window (e.g., "24h", "7d")

        Example:
            >>> agent.set_limit("USDC", "100", "24h")
            >>> agent.set_limit("ETH", 0.5, "1h")
        """
        config = self._load_config()

        # Parse window and convert amount
        window_seconds = parse_time_window(window)
        amount_decimal = Decimal(str(amount))

        # Create limit config
        limit_cfg = LimitConfig(
            asset=asset,
            amount=amount_decimal,
            window_seconds=window_seconds,
        )

        # Update config
        config.limits[asset] = limit_cfg
        self._config = config
        self._save_config()

    def allow_action(
        self,
        action_type: str,
        **constraints: Any
    ) -> None:
        """
        Add an allowed action rule with optional constraints.

        Args:
            action_type: Type of action (e.g., "swap", "transfer")
            **constraints: Key-value constraints that must match

        Example:
            >>> agent.allow_action("swap", protocol="UniswapV3")
            >>> agent.allow_action("transfer", token="USDC")
        """
        config = self._load_config()

        # Create allow rule
        rule = AllowRule(
            action_type=action_type,
            constraints=constraints,
        )

        # Append to rules
        config.allow_rules.append(rule)
        self._config = config
        self._save_config()

    def authorize(
        self,
        action_type: str,
        params: Dict[str, Any]
    ) -> bool:
        """
        Authorize an action based on configured rules and limits.

        This is the core authorization method. It:
        1. Checks if the action is in the allowlist
        2. Checks if the action would exceed spending limits
        3. Logs the decision
        4. Returns True if allowed, False if denied

        Authorization is deterministic and fail-safe (denies on error).

        Args:
            action_type: Type of action to authorize
            params: Parameters of the action

        Returns:
            True if authorized, False if denied

        Example:
            >>> allowed = agent.authorize("swap", {
            ...     "token": "USDC",
            ...     "amount": "10",
            ...     "protocol": "UniswapV3"
            ... })
        """
        try:
            config = self._load_config()
            now = datetime.now(timezone.utc)

            # Normalize params
            action_params = self._normalize_params(params)

            # Check 1: Is action allowed by rules?
            if not is_action_allowed_by_rules(
                action_type=action_type,
                params=params,
                rules=config.allow_rules
            ):
                self._log_decision(
                    action_type=action_type,
                    params=params,
                    allowed=False,
                    reason="Action not in allowlist"
                )
                return False

            # Check 2: If amount/asset present and limit exists, check limits
            if action_params.amount is not None:
                asset = action_params.asset or params.get('token')

                if asset and asset in config.limits:
                    limit_cfg = config.limits[asset]

                    if not is_within_limits(
                        asset=asset,
                        amount=action_params.amount,
                        limit_cfg=limit_cfg,
                        storage=self.storage,
                        agent_id=self.agent_id,
                        now=now
                    ):
                        self._log_decision(
                            action_type=action_type,
                            params=params,
                            allowed=False,
                            reason=f"Exceeds {asset} limit of {limit_cfg.amount} per {limit_cfg.window_seconds}s"
                        )
                        return False

            # All checks passed
            self._log_decision(
                action_type=action_type,
                params=params,
                allowed=True,
                reason=None
            )
            return True

        except Exception as e:
            # Fail-safe: deny on any error
            self._log_decision(
                action_type=action_type,
                params=params,
                allowed=False,
                reason=f"Error during authorization: {str(e)}"
            )
            return False

    def _normalize_params(self, params: Dict[str, Any]) -> ActionParams:
        """
        Normalize action parameters.

        Converts raw dict to ActionParams, handling amount conversion to Decimal.

        Args:
            params: Raw parameters dict

        Returns:
            Normalized ActionParams
        """
        try:
            return ActionParams.from_dict(params)
        except Exception:
            # If normalization fails, return minimal params
            return ActionParams(extra=params)

    def _log_decision(
        self,
        action_type: str,
        params: Dict[str, Any],
        allowed: bool,
        reason: Optional[str] = None
    ) -> None:
        """
        Log an authorization decision.

        Args:
            action_type: Type of action
            params: Action parameters
            allowed: Whether action was allowed
            reason: Optional reason for denial
        """
        log_entry = LogEntry.create(
            agent_id=self.agent_id,
            action_type=action_type,
            params=params,
            allowed=allowed,
            reason=reason,
        )

        self.storage.append_log(log_entry.model_dump())

    def get_logs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve audit logs for this agent.

        Args:
            limit: Optional maximum number of logs to return (most recent)

        Returns:
            List of log entry dictionaries

        Example:
            >>> logs = agent.get_logs(limit=10)
            >>> for log in logs:
            ...     print(f"{log['timestamp']}: {log['action_type']} - {log['allowed']}")
        """
        return self.storage.get_logs(agent_id=self.agent_id, limit=limit)
