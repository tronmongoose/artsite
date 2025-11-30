"""
Tests for Agent class.
"""

import tempfile
from pathlib import Path
from decimal import Decimal

import pytest

from agent_guardrails import Agent, AuthorizationError
from agent_guardrails.storage import JsonFileStorage


class TestAgentRegistration:
    """Tests for agent registration."""

    @pytest.fixture
    def temp_storage(self):
        """Create a temporary storage instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_state.json"
            yield JsonFileStorage(str(storage_path))

    def test_register_minimal(self, temp_storage):
        """Test registering an agent with minimal parameters."""
        agent = Agent.register(
            wallet="0x123",
            storage=temp_storage
        )

        assert agent.agent_id is not None
        assert len(agent.agent_id) > 0

        # Verify it was saved
        config = temp_storage.load_agent(agent.agent_id)
        assert config is not None
        assert config.wallet == "0x123"
        assert config.name is None
        assert config.metadata == {}
        assert config.limits == {}
        assert config.allow_rules == []

    def test_register_with_name_and_metadata(self, temp_storage):
        """Test registering an agent with name and metadata."""
        agent = Agent.register(
            wallet="0xABC",
            name="test_bot",
            metadata={"env": "production", "version": "1.0"},
            storage=temp_storage
        )

        config = temp_storage.load_agent(agent.agent_id)
        assert config.name == "test_bot"
        assert config.metadata == {"env": "production", "version": "1.0"}


class TestAgentLimits:
    """Tests for setting limits."""

    @pytest.fixture
    def agent(self):
        """Create a test agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_state.json"
            storage = JsonFileStorage(str(storage_path))
            yield Agent.register(wallet="0x123", storage=storage)

    def test_set_limit_hours(self, agent):
        """Test setting a limit with hour window."""
        agent.set_limit("USDC", "100", "24h")

        config = agent._load_config()
        assert "USDC" in config.limits
        assert config.limits["USDC"].amount == Decimal("100")
        assert config.limits["USDC"].window_seconds == 86400

    def test_set_limit_days(self, agent):
        """Test setting a limit with day window."""
        agent.set_limit("ETH", 1.5, "7d")

        config = agent._load_config()
        assert "ETH" in config.limits
        assert config.limits["ETH"].amount == Decimal("1.5")
        assert config.limits["ETH"].window_seconds == 604800

    def test_set_multiple_limits(self, agent):
        """Test setting limits for multiple assets."""
        agent.set_limit("USDC", "100", "24h")
        agent.set_limit("ETH", "1", "1h")
        agent.set_limit("DAI", "50", "7d")

        config = agent._load_config()
        assert len(config.limits) == 3
        assert "USDC" in config.limits
        assert "ETH" in config.limits
        assert "DAI" in config.limits

    def test_update_existing_limit(self, agent):
        """Test updating an existing limit."""
        agent.set_limit("USDC", "100", "24h")
        agent.set_limit("USDC", "200", "48h")

        config = agent._load_config()
        assert config.limits["USDC"].amount == Decimal("200")
        assert config.limits["USDC"].window_seconds == 172800


class TestAgentAllowRules:
    """Tests for allow action rules."""

    @pytest.fixture
    def agent(self):
        """Create a test agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_state.json"
            storage = JsonFileStorage(str(storage_path))
            yield Agent.register(wallet="0x123", storage=storage)

    def test_allow_action_no_constraints(self, agent):
        """Test allowing an action without constraints."""
        agent.allow_action("swap")

        config = agent._load_config()
        assert len(config.allow_rules) == 1
        assert config.allow_rules[0].action_type == "swap"
        assert config.allow_rules[0].constraints == {}

    def test_allow_action_with_constraints(self, agent):
        """Test allowing an action with constraints."""
        agent.allow_action("swap", protocol="UniswapV3", chain="ethereum")

        config = agent._load_config()
        assert len(config.allow_rules) == 1
        assert config.allow_rules[0].action_type == "swap"
        assert config.allow_rules[0].constraints == {
            "protocol": "UniswapV3",
            "chain": "ethereum"
        }

    def test_allow_multiple_actions(self, agent):
        """Test allowing multiple action types."""
        agent.allow_action("swap", protocol="UniswapV3")
        agent.allow_action("transfer", token="USDC")
        agent.allow_action("stake")

        config = agent._load_config()
        assert len(config.allow_rules) == 3


class TestAgentAuthorization:
    """Tests for authorization logic."""

    @pytest.fixture
    def agent(self):
        """Create a test agent with predefined rules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_state.json"
            storage = JsonFileStorage(str(storage_path))
            agent = Agent.register(wallet="0x123", storage=storage)

            # Set up rules and limits
            agent.set_limit("USDC", "100", "24h")
            agent.allow_action("swap", protocol="UniswapV3")

            yield agent

    def test_authorize_allowed_action(self, agent):
        """Test authorizing an allowed action."""
        result = agent.authorize("swap", {
            "protocol": "UniswapV3",
            "token": "USDC",
            "amount": "10"
        })

        assert result is True

        # Check log
        logs = agent.get_logs()
        assert len(logs) == 1
        assert logs[0]["allowed"] is True
        assert logs[0]["action_type"] == "swap"

    def test_authorize_disallowed_action_type(self, agent):
        """Test that disallowed action types are denied."""
        result = agent.authorize("transfer", {
            "token": "USDC",
            "amount": "10"
        })

        assert result is False

        # Check log
        logs = agent.get_logs()
        assert len(logs) == 1
        assert logs[0]["allowed"] is False
        assert "allowlist" in logs[0]["reason"].lower()

    def test_authorize_wrong_constraints(self, agent):
        """Test that wrong constraints are denied."""
        result = agent.authorize("swap", {
            "protocol": "SushiSwap",  # Wrong protocol
            "token": "USDC",
            "amount": "10"
        })

        assert result is False

    def test_authorize_over_limit(self, agent):
        """Test that actions exceeding limits are denied."""
        # First action within limit
        result1 = agent.authorize("swap", {
            "protocol": "UniswapV3",
            "token": "USDC",
            "amount": "60"
        })
        assert result1 is True

        # Second action that would exceed limit
        result2 = agent.authorize("swap", {
            "protocol": "UniswapV3",
            "token": "USDC",
            "amount": "50"
        })
        assert result2 is False

        # Check that second log shows over limit
        logs = agent.get_logs()
        assert len(logs) == 2
        assert logs[1]["allowed"] is False
        assert "limit" in logs[1]["reason"].lower()

    def test_authorize_at_limit_boundary(self, agent):
        """Test authorization at exact limit boundary."""
        # Use exactly the limit
        result = agent.authorize("swap", {
            "protocol": "UniswapV3",
            "token": "USDC",
            "amount": "100"
        })
        assert result is True

        # Try to spend more (should fail)
        result2 = agent.authorize("swap", {
            "protocol": "UniswapV3",
            "token": "USDC",
            "amount": "0.01"
        })
        assert result2 is False

    def test_authorize_without_amount_no_limit_check(self, agent):
        """Test that actions without amounts skip limit checks."""
        # This should be allowed even though we have a USDC limit,
        # because there's no amount to check
        result = agent.authorize("swap", {
            "protocol": "UniswapV3",
            "token": "ETH"  # Different token, no limit
        })

        assert result is True

    def test_authorize_denied_dont_count_against_limit(self, agent):
        """Test that denied actions don't count against limits."""
        # Deny due to wrong protocol (doesn't count)
        agent.authorize("swap", {
            "protocol": "SushiSwap",
            "token": "USDC",
            "amount": "60"
        })

        # Now authorize with correct protocol - should work
        result = agent.authorize("swap", {
            "protocol": "UniswapV3",
            "token": "USDC",
            "amount": "60"
        })
        assert result is True


class TestAgentLogs:
    """Tests for log retrieval."""

    @pytest.fixture
    def agent(self):
        """Create a test agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_state.json"
            storage = JsonFileStorage(str(storage_path))
            agent = Agent.register(wallet="0x123", storage=storage)
            agent.allow_action("swap")
            yield agent

    def test_get_logs_empty(self, agent):
        """Test getting logs when none exist."""
        logs = agent.get_logs()
        assert logs == []

    def test_get_logs_after_authorizations(self, agent):
        """Test getting logs after some authorizations."""
        agent.authorize("swap", {"token": "USDC", "amount": "10"})
        agent.authorize("swap", {"token": "ETH", "amount": "1"})

        logs = agent.get_logs()
        assert len(logs) == 2
        assert logs[0]["action_type"] == "swap"
        assert logs[1]["action_type"] == "swap"

    def test_get_logs_with_limit(self, agent):
        """Test getting logs with a limit."""
        for i in range(5):
            agent.authorize("swap", {"token": "USDC", "amount": str(i)})

        logs = agent.get_logs(limit=3)
        assert len(logs) == 3

    def test_logs_contain_required_fields(self, agent):
        """Test that logs contain all required fields."""
        agent.authorize("swap", {"token": "USDC", "amount": "10"})

        logs = agent.get_logs()
        log = logs[0]

        assert "timestamp" in log
        assert "agent_id" in log
        assert "action_type" in log
        assert "params" in log
        assert "allowed" in log
        assert "reason" in log

        assert log["agent_id"] == agent.agent_id
        assert log["action_type"] == "swap"
        assert log["params"] == {"token": "USDC", "amount": "10"}


class TestAgentIntegration:
    """Integration tests for complete workflows."""

    def test_complete_workflow(self):
        """Test a complete workflow from registration to authorization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_state.json"
            storage = JsonFileStorage(str(storage_path))

            # Register agent
            agent = Agent.register(
                wallet="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
                name="trading_bot",
                metadata={"strategy": "arbitrage"},
                storage=storage
            )

            # Set limits
            agent.set_limit("USDC", "1000", "24h")
            agent.set_limit("ETH", "0.5", "1h")

            # Allow actions
            agent.allow_action("swap", protocol="UniswapV3")
            agent.allow_action("swap", protocol="SushiSwap")

            # Authorize some actions
            assert agent.authorize("swap", {
                "protocol": "UniswapV3",
                "token": "USDC",
                "amount": "100"
            }) is True

            assert agent.authorize("swap", {
                "protocol": "SushiSwap",
                "token": "USDC",
                "amount": "200"
            }) is True

            assert agent.authorize("swap", {
                "protocol": "PancakeSwap",  # Not allowed
                "token": "USDC",
                "amount": "50"
            }) is False

            # Check logs
            logs = agent.get_logs()
            assert len(logs) == 3
            assert logs[0]["allowed"] is True
            assert logs[1]["allowed"] is True
            assert logs[2]["allowed"] is False

    def test_multiple_agents_isolated(self):
        """Test that multiple agents are properly isolated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_state.json"
            storage = JsonFileStorage(str(storage_path))

            # Create two agents
            agent1 = Agent.register(wallet="0x111", storage=storage)
            agent2 = Agent.register(wallet="0x222", storage=storage)

            # Configure agent1
            agent1.set_limit("USDC", "100", "24h")
            agent1.allow_action("swap")

            # Configure agent2
            agent2.set_limit("USDC", "200", "24h")
            agent2.allow_action("transfer")

            # Agent1 authorizes a swap
            agent1.authorize("swap", {"token": "USDC", "amount": "50"})

            # Agent2's logs should be empty
            assert len(agent2.get_logs()) == 0

            # Agent1 should have one log
            assert len(agent1.get_logs()) == 1

            # Agent2 can't swap (not in allowlist)
            assert agent2.authorize("swap", {"token": "USDC", "amount": "10"}) is False

            # Agent1 can't transfer (not in allowlist)
            assert agent1.authorize("transfer", {"token": "USDC", "amount": "10"}) is False
