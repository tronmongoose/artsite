"""
Tests for policy logic.
"""

from decimal import Decimal
from datetime import datetime, timedelta, timezone

import pytest

from agent_guardrails.policies import (
    parse_time_window,
    is_action_allowed_by_rules,
    is_within_limits,
)
from agent_guardrails.types import AllowRule, LimitConfig
from agent_guardrails.storage import JsonFileStorage
import tempfile
from pathlib import Path


class TestParseTimeWindow:
    """Tests for parse_time_window function."""

    def test_parse_hours(self):
        """Test parsing hour-based windows."""
        assert parse_time_window("1h") == 3600
        assert parse_time_window("24h") == 86400
        assert parse_time_window("48h") == 172800

    def test_parse_days(self):
        """Test parsing day-based windows."""
        assert parse_time_window("1d") == 86400
        assert parse_time_window("7d") == 604800
        assert parse_time_window("30d") == 2592000

    def test_case_insensitive(self):
        """Test that parsing is case-insensitive."""
        assert parse_time_window("24H") == 86400
        assert parse_time_window("7D") == 604800

    def test_invalid_format(self):
        """Test that invalid formats raise ValueError."""
        with pytest.raises(ValueError, match="Invalid time window format"):
            parse_time_window("24hours")

        with pytest.raises(ValueError, match="Invalid time window format"):
            parse_time_window("abc")

        with pytest.raises(ValueError, match="Invalid time window format"):
            parse_time_window("24")


class TestIsActionAllowedByRules:
    """Tests for is_action_allowed_by_rules function."""

    def test_no_rules_denies(self):
        """Test that no rules results in denial."""
        result = is_action_allowed_by_rules(
            action_type="swap",
            params={"token": "USDC"},
            rules=[]
        )
        assert result is False

    def test_no_matching_action_type_denies(self):
        """Test that mismatched action type denies."""
        rules = [
            AllowRule(action_type="transfer", constraints={})
        ]
        result = is_action_allowed_by_rules(
            action_type="swap",
            params={},
            rules=rules
        )
        assert result is False

    def test_action_type_match_no_constraints_allows(self):
        """Test that matching action type with no constraints allows."""
        rules = [
            AllowRule(action_type="swap", constraints={})
        ]
        result = is_action_allowed_by_rules(
            action_type="swap",
            params={"token": "USDC", "amount": "10"},
            rules=rules
        )
        assert result is True

    def test_action_type_and_constraints_match_allows(self):
        """Test that matching action type and constraints allows."""
        rules = [
            AllowRule(
                action_type="swap",
                constraints={"protocol": "UniswapV3"}
            )
        ]
        result = is_action_allowed_by_rules(
            action_type="swap",
            params={"protocol": "UniswapV3", "token": "USDC"},
            rules=rules
        )
        assert result is True

    def test_constraint_mismatch_denies(self):
        """Test that mismatched constraints deny."""
        rules = [
            AllowRule(
                action_type="swap",
                constraints={"protocol": "UniswapV3"}
            )
        ]
        result = is_action_allowed_by_rules(
            action_type="swap",
            params={"protocol": "SushiSwap", "token": "USDC"},
            rules=rules
        )
        assert result is False

    def test_multiple_constraints_all_must_match(self):
        """Test that all constraints must match."""
        rules = [
            AllowRule(
                action_type="swap",
                constraints={
                    "protocol": "UniswapV3",
                    "chain": "ethereum"
                }
            )
        ]

        # Both match
        assert is_action_allowed_by_rules(
            action_type="swap",
            params={"protocol": "UniswapV3", "chain": "ethereum"},
            rules=rules
        ) is True

        # Only one matches
        assert is_action_allowed_by_rules(
            action_type="swap",
            params={"protocol": "UniswapV3", "chain": "polygon"},
            rules=rules
        ) is False

    def test_multiple_rules_any_can_match(self):
        """Test that any rule can provide authorization."""
        rules = [
            AllowRule(
                action_type="swap",
                constraints={"protocol": "UniswapV3"}
            ),
            AllowRule(
                action_type="swap",
                constraints={"protocol": "SushiSwap"}
            )
        ]

        # Matches first rule
        assert is_action_allowed_by_rules(
            action_type="swap",
            params={"protocol": "UniswapV3"},
            rules=rules
        ) is True

        # Matches second rule
        assert is_action_allowed_by_rules(
            action_type="swap",
            params={"protocol": "SushiSwap"},
            rules=rules
        ) is True

        # Matches neither
        assert is_action_allowed_by_rules(
            action_type="swap",
            params={"protocol": "PancakeSwap"},
            rules=rules
        ) is False


class TestIsWithinLimits:
    """Tests for is_within_limits function."""

    @pytest.fixture
    def temp_storage(self):
        """Create a temporary storage instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_state.json"
            yield JsonFileStorage(str(storage_path))

    def test_no_prior_spending_allows(self, temp_storage):
        """Test that with no prior spending, action is allowed."""
        limit_cfg = LimitConfig(
            asset="USDC",
            amount=Decimal("100"),
            window_seconds=86400
        )

        result = is_within_limits(
            asset="USDC",
            amount=Decimal("50"),
            limit_cfg=limit_cfg,
            storage=temp_storage,
            agent_id="agent-1",
            now=datetime.now(timezone.utc)
        )
        assert result is True

    def test_under_limit_allows(self, temp_storage):
        """Test that spending under limit is allowed."""
        agent_id = "agent-1"
        now = datetime.now(timezone.utc)

        # Add a log entry for previous spending
        temp_storage.append_log({
            "timestamp": now.isoformat().replace('+00:00', 'Z'),
            "agent_id": agent_id,
            "action_type": "swap",
            "params": {"asset": "USDC", "amount": "30"},
            "allowed": True,
            "reason": None
        })

        limit_cfg = LimitConfig(
            asset="USDC",
            amount=Decimal("100"),
            window_seconds=86400
        )

        # 30 + 50 = 80, which is under 100
        result = is_within_limits(
            asset="USDC",
            amount=Decimal("50"),
            limit_cfg=limit_cfg,
            storage=temp_storage,
            agent_id=agent_id,
            now=now
        )
        assert result is True

    def test_at_limit_allows(self, temp_storage):
        """Test that spending exactly at limit is allowed."""
        agent_id = "agent-1"
        now = datetime.now(timezone.utc)

        temp_storage.append_log({
            "timestamp": now.isoformat().replace('+00:00', 'Z'),
            "agent_id": agent_id,
            "action_type": "swap",
            "params": {"asset": "USDC", "amount": "50"},
            "allowed": True,
            "reason": None
        })

        limit_cfg = LimitConfig(
            asset="USDC",
            amount=Decimal("100"),
            window_seconds=86400
        )

        # 50 + 50 = 100, which equals the limit (should allow)
        result = is_within_limits(
            asset="USDC",
            amount=Decimal("50"),
            limit_cfg=limit_cfg,
            storage=temp_storage,
            agent_id=agent_id,
            now=now
        )
        assert result is True

    def test_over_limit_denies(self, temp_storage):
        """Test that spending over limit is denied."""
        agent_id = "agent-1"
        now = datetime.now(timezone.utc)

        temp_storage.append_log({
            "timestamp": now.isoformat().replace('+00:00', 'Z'),
            "agent_id": agent_id,
            "action_type": "swap",
            "params": {"asset": "USDC", "amount": "60"},
            "allowed": True,
            "reason": None
        })

        limit_cfg = LimitConfig(
            asset="USDC",
            amount=Decimal("100"),
            window_seconds=86400
        )

        # 60 + 50 = 110, which exceeds 100
        result = is_within_limits(
            asset="USDC",
            amount=Decimal("50"),
            limit_cfg=limit_cfg,
            storage=temp_storage,
            agent_id=agent_id,
            now=now
        )
        assert result is False

    def test_rolling_window_excludes_old_entries(self, temp_storage):
        """Test that old entries outside the window are excluded."""
        agent_id = "agent-1"
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(hours=25)  # Outside 24h window

        # Add old entry (should be excluded)
        temp_storage.append_log({
            "timestamp": old_time.isoformat().replace('+00:00', 'Z'),
            "agent_id": agent_id,
            "action_type": "swap",
            "params": {"asset": "USDC", "amount": "60"},
            "allowed": True,
            "reason": None
        })

        # Add recent entry (should be included)
        temp_storage.append_log({
            "timestamp": now.isoformat().replace('+00:00', 'Z'),
            "agent_id": agent_id,
            "action_type": "swap",
            "params": {"asset": "USDC", "amount": "20"},
            "allowed": True,
            "reason": None
        })

        limit_cfg = LimitConfig(
            asset="USDC",
            amount=Decimal("100"),
            window_seconds=86400  # 24 hours
        )

        # Only 20 should count, so 20 + 50 = 70 < 100
        result = is_within_limits(
            asset="USDC",
            amount=Decimal("50"),
            limit_cfg=limit_cfg,
            storage=temp_storage,
            agent_id=agent_id,
            now=now
        )
        assert result is True

    def test_denied_actions_dont_count(self, temp_storage):
        """Test that denied actions don't count against the limit."""
        agent_id = "agent-1"
        now = datetime.now(timezone.utc)

        # Add denied entry (should not count)
        temp_storage.append_log({
            "timestamp": now.isoformat().replace('+00:00', 'Z'),
            "agent_id": agent_id,
            "action_type": "swap",
            "params": {"asset": "USDC", "amount": "60"},
            "allowed": False,
            "reason": "Not allowed"
        })

        limit_cfg = LimitConfig(
            asset="USDC",
            amount=Decimal("100"),
            window_seconds=86400
        )

        # 0 + 50 = 50 < 100 (denied entry doesn't count)
        result = is_within_limits(
            asset="USDC",
            amount=Decimal("50"),
            limit_cfg=limit_cfg,
            storage=temp_storage,
            agent_id=agent_id,
            now=now
        )
        assert result is True

    def test_different_asset_doesnt_count(self, temp_storage):
        """Test that different assets don't affect each other's limits."""
        agent_id = "agent-1"
        now = datetime.now(timezone.utc)

        # Add entry for ETH (should not affect USDC limit)
        temp_storage.append_log({
            "timestamp": now.isoformat().replace('+00:00', 'Z'),
            "agent_id": agent_id,
            "action_type": "swap",
            "params": {"asset": "ETH", "amount": "60"},
            "allowed": True,
            "reason": None
        })

        limit_cfg = LimitConfig(
            asset="USDC",
            amount=Decimal("100"),
            window_seconds=86400
        )

        # 0 + 50 = 50 < 100 (ETH doesn't count against USDC)
        result = is_within_limits(
            asset="USDC",
            amount=Decimal("50"),
            limit_cfg=limit_cfg,
            storage=temp_storage,
            agent_id=agent_id,
            now=now
        )
        assert result is True

    def test_token_alias_support(self, temp_storage):
        """Test that 'token' field is also recognized as 'asset'."""
        agent_id = "agent-1"
        now = datetime.now(timezone.utc)

        # Add entry using 'token' instead of 'asset'
        temp_storage.append_log({
            "timestamp": now.isoformat().replace('+00:00', 'Z'),
            "agent_id": agent_id,
            "action_type": "swap",
            "params": {"token": "USDC", "amount": "30"},
            "allowed": True,
            "reason": None
        })

        limit_cfg = LimitConfig(
            asset="USDC",
            amount=Decimal("100"),
            window_seconds=86400
        )

        # 30 + 50 = 80 < 100
        result = is_within_limits(
            asset="USDC",
            amount=Decimal("50"),
            limit_cfg=limit_cfg,
            storage=temp_storage,
            agent_id=agent_id,
            now=now
        )
        assert result is True
