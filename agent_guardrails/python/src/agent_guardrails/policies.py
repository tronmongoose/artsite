"""
Pure policy logic for Agent Guardrails SDK.

This module contains deterministic, side-effect-free functions for:
- Parsing time windows
- Checking action allowlists
- Enforcing spending limits

All authorization decisions are deterministic and explicit.
"""

import re
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any

from .types import AllowRule, LimitConfig
from .storage import StorageDriver


def parse_time_window(window: str) -> int:
    """
    Parse a time window string into seconds.

    Supported formats:
    - "24h" -> 86400 seconds
    - "1h"  -> 3600 seconds
    - "7d"  -> 604800 seconds

    Args:
        window: Time window string (e.g., "24h", "7d")

    Returns:
        Number of seconds

    Raises:
        ValueError: If the window format is invalid
    """
    pattern = r'^(\d+)([hd])$'
    match = re.match(pattern, window.lower())

    if not match:
        raise ValueError(
            f"Invalid time window format: '{window}'. "
            "Expected format: <number><h|d> (e.g., '24h', '7d')"
        )

    amount = int(match.group(1))
    unit = match.group(2)

    if unit == 'h':
        return amount * 3600
    elif unit == 'd':
        return amount * 86400
    else:
        raise ValueError(f"Unknown time unit: {unit}")


def is_action_allowed_by_rules(
    action_type: str,
    params: Dict[str, Any],
    rules: List[AllowRule]
) -> bool:
    """
    Check if an action is allowed based on allowlist rules.

    Matching logic:
    1. At least one rule must exist for the action_type
    2. Rule matches if:
       - action_type matches AND
       - all constraint key-value pairs match exactly (string equality)

    Args:
        action_type: Type of action (e.g., "swap", "transfer")
        params: Parameters of the action
        rules: List of allow rules to check against

    Returns:
        True if the action is allowed, False otherwise
    """
    # Filter rules for this action type
    relevant_rules = [r for r in rules if r.action_type == action_type]

    # If no rules exist for this action type, deny
    if not relevant_rules:
        return False

    # Check if any rule matches
    for rule in relevant_rules:
        if _rule_matches(rule, params):
            return True

    return False


def _rule_matches(rule: AllowRule, params: Dict[str, Any]) -> bool:
    """
    Check if a single rule matches the given parameters.

    All constraints in the rule must match params exactly.

    Args:
        rule: Allow rule with constraints
        params: Parameters to check

    Returns:
        True if all constraints match, False otherwise
    """
    # If rule has no constraints, it matches anything of this action_type
    if not rule.constraints:
        return True

    # All constraints must match
    for key, expected_value in rule.constraints.items():
        actual_value = params.get(key)

        # Convert both to strings for comparison to handle different types
        if str(actual_value) != str(expected_value):
            return False

    return True


def is_within_limits(
    asset: str,
    amount: Decimal,
    limit_cfg: LimitConfig,
    storage: StorageDriver,
    agent_id: str,
    now: datetime
) -> bool:
    """
    Check if an action would exceed spending limits.

    Calculates the sum of allowed amounts for the asset within the rolling
    time window and checks if adding the new amount would exceed the limit.

    Args:
        asset: Asset symbol (must match limit_cfg.asset)
        amount: Amount to authorize
        limit_cfg: Limit configuration
        storage: Storage driver for querying logs
        agent_id: Agent identifier
        now: Current timestamp for window calculation

    Returns:
        True if within limits, False if would exceed
    """
    # Sanity check: asset must match
    if asset != limit_cfg.asset:
        return False

    # Ensure now is timezone-aware (UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # Calculate window start time
    window_start = now - timedelta(seconds=limit_cfg.window_seconds)

    # Get all logs for this agent
    all_logs = storage.get_logs(agent_id=agent_id)

    # Sum amounts for this asset within the window that were ALLOWED
    total_spent = Decimal('0')

    for log in all_logs:
        # Skip if not allowed (denied actions don't count against limit)
        if not log.get('allowed', False):
            continue

        # Parse timestamp
        try:
            log_time = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
        except (ValueError, KeyError):
            # Skip logs with invalid timestamps
            continue

        # Skip if outside window
        if log_time < window_start:
            continue

        # Check if this log is for the same asset
        log_params = log.get('params', {})
        log_asset = log_params.get('asset') or log_params.get('token')

        if log_asset == asset:
            # Extract amount from log
            log_amount_str = log_params.get('amount')
            if log_amount_str is not None:
                try:
                    log_amount = Decimal(str(log_amount_str))
                    total_spent += log_amount
                except (ValueError, ArithmeticError):
                    # Skip logs with invalid amounts
                    continue

    # Check if adding this amount would exceed the limit
    return (total_spent + amount) <= limit_cfg.amount
