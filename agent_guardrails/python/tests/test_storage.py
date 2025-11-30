"""
Tests for storage module.
"""

import tempfile
from pathlib import Path
from decimal import Decimal

import pytest

from agent_guardrails.storage import JsonFileStorage
from agent_guardrails.types import AgentConfig, LimitConfig, AllowRule


class TestJsonFileStorage:
    """Tests for JsonFileStorage implementation."""

    @pytest.fixture
    def temp_storage(self):
        """Create a temporary storage instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_state.json"
            yield JsonFileStorage(str(storage_path))

    @pytest.fixture
    def sample_config(self):
        """Create a sample agent configuration."""
        return AgentConfig(
            agent_id="test-agent-123",
            wallet="0xABC123",
            name="test_agent",
            metadata={"env": "test"},
            limits={
                "USDC": LimitConfig(
                    asset="USDC",
                    amount=Decimal("100"),
                    window_seconds=86400
                )
            },
            allow_rules=[
                AllowRule(
                    action_type="swap",
                    constraints={"protocol": "UniswapV3"}
                )
            ]
        )

    def test_file_creation(self, temp_storage):
        """Test that storage file is created on initialization."""
        assert temp_storage.path.exists()
        assert temp_storage.path.is_file()

    def test_save_and_load_agent(self, temp_storage, sample_config):
        """Test saving and loading agent configuration."""
        # Save
        temp_storage.save_agent(sample_config)

        # Load
        loaded = temp_storage.load_agent(sample_config.agent_id)

        assert loaded is not None
        assert loaded.agent_id == sample_config.agent_id
        assert loaded.wallet == sample_config.wallet
        assert loaded.name == sample_config.name
        assert loaded.metadata == sample_config.metadata
        assert "USDC" in loaded.limits
        assert loaded.limits["USDC"].amount == Decimal("100")
        assert len(loaded.allow_rules) == 1
        assert loaded.allow_rules[0].action_type == "swap"

    def test_load_nonexistent_agent(self, temp_storage):
        """Test loading an agent that doesn't exist."""
        result = temp_storage.load_agent("nonexistent-id")
        assert result is None

    def test_update_agent(self, temp_storage, sample_config):
        """Test updating an existing agent configuration."""
        # Save initial
        temp_storage.save_agent(sample_config)

        # Modify and save again
        sample_config.name = "updated_name"
        sample_config.limits["ETH"] = LimitConfig(
            asset="ETH",
            amount=Decimal("1"),
            window_seconds=3600
        )
        temp_storage.save_agent(sample_config)

        # Load and verify
        loaded = temp_storage.load_agent(sample_config.agent_id)
        assert loaded.name == "updated_name"
        assert len(loaded.limits) == 2
        assert "ETH" in loaded.limits

    def test_append_log(self, temp_storage):
        """Test appending log entries."""
        log1 = {
            "timestamp": "2025-11-30T12:00:00Z",
            "agent_id": "agent-1",
            "action_type": "swap",
            "params": {"token": "USDC", "amount": "10"},
            "allowed": True,
            "reason": None
        }
        log2 = {
            "timestamp": "2025-11-30T12:01:00Z",
            "agent_id": "agent-1",
            "action_type": "transfer",
            "params": {"token": "USDC", "amount": "5"},
            "allowed": False,
            "reason": "Over limit"
        }

        temp_storage.append_log(log1)
        temp_storage.append_log(log2)

        logs = temp_storage.get_logs()
        assert len(logs) == 2
        assert logs[0] == log1
        assert logs[1] == log2

    def test_get_logs_filtered_by_agent(self, temp_storage):
        """Test filtering logs by agent ID."""
        temp_storage.append_log({
            "timestamp": "2025-11-30T12:00:00Z",
            "agent_id": "agent-1",
            "action_type": "swap",
            "params": {},
            "allowed": True,
            "reason": None
        })
        temp_storage.append_log({
            "timestamp": "2025-11-30T12:01:00Z",
            "agent_id": "agent-2",
            "action_type": "transfer",
            "params": {},
            "allowed": True,
            "reason": None
        })
        temp_storage.append_log({
            "timestamp": "2025-11-30T12:02:00Z",
            "agent_id": "agent-1",
            "action_type": "stake",
            "params": {},
            "allowed": False,
            "reason": "Not allowed"
        })

        agent1_logs = temp_storage.get_logs(agent_id="agent-1")
        assert len(agent1_logs) == 2
        assert all(log["agent_id"] == "agent-1" for log in agent1_logs)

        agent2_logs = temp_storage.get_logs(agent_id="agent-2")
        assert len(agent2_logs) == 1
        assert agent2_logs[0]["agent_id"] == "agent-2"

    def test_get_logs_with_limit(self, temp_storage):
        """Test retrieving logs with a limit."""
        for i in range(5):
            temp_storage.append_log({
                "timestamp": f"2025-11-30T12:0{i}:00Z",
                "agent_id": "agent-1",
                "action_type": "swap",
                "params": {},
                "allowed": True,
                "reason": None
            })

        logs = temp_storage.get_logs(limit=3)
        assert len(logs) == 3
        # Should get the most recent 3
        assert logs[0]["timestamp"] == "2025-11-30T12:02:00Z"
        assert logs[2]["timestamp"] == "2025-11-30T12:04:00Z"

    def test_multiple_agents(self, temp_storage):
        """Test storing multiple agents in the same file."""
        config1 = AgentConfig(
            agent_id="agent-1",
            wallet="0x111",
            name="agent_1",
            metadata={},
            limits={},
            allow_rules=[]
        )
        config2 = AgentConfig(
            agent_id="agent-2",
            wallet="0x222",
            name="agent_2",
            metadata={},
            limits={},
            allow_rules=[]
        )

        temp_storage.save_agent(config1)
        temp_storage.save_agent(config2)

        loaded1 = temp_storage.load_agent("agent-1")
        loaded2 = temp_storage.load_agent("agent-2")

        assert loaded1.wallet == "0x111"
        assert loaded2.wallet == "0x222"
