"""
Local storage implementation for Agent Guardrails SDK.

Provides a protocol-based interface and JSON file storage implementation.
All data is stored locally with no external dependencies.
"""

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from .types import AgentConfig


class StorageDriver(Protocol):
    """
    Protocol defining the storage interface for agent configurations and logs.

    Implementations must provide thread-safe operations for saving and retrieving
    agent configurations and audit logs.
    """

    def save_agent(self, config: AgentConfig) -> None:
        """
        Save or update an agent configuration.

        Args:
            config: Agent configuration to save
        """
        ...

    def load_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """
        Load an agent configuration by ID.

        Args:
            agent_id: Unique identifier for the agent

        Returns:
            Agent configuration if found, None otherwise
        """
        ...

    def append_log(self, log_entry: Dict[str, Any]) -> None:
        """
        Append a log entry to the audit log.

        Args:
            log_entry: Log entry dictionary to append
        """
        ...

    def get_logs(
        self,
        agent_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit logs.

        Args:
            agent_id: Optional filter by agent ID
            limit: Optional maximum number of logs to return

        Returns:
            List of log entry dictionaries
        """
        ...


class JsonFileStorage:
    """
    Thread-safe JSON file storage implementation.

    Stores all agent configurations and logs in a single JSON file
    at ~/.agent_guardrails/state.json by default.

    File structure:
    {
        "agents": {
            "agent-id-1": {...},
            "agent-id-2": {...}
        },
        "logs": [
            {...},
            {...}
        ]
    }
    """

    def __init__(self, path: Optional[str] = None):
        """
        Initialize JSON file storage.

        Args:
            path: Optional custom path for the storage file.
                  Defaults to ~/.agent_guardrails/state.json
        """
        if path is None:
            home = Path.home()
            self.path = home / '.agent_guardrails' / 'state.json'
        else:
            self.path = Path(path)

        self._lock = threading.Lock()
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Create the storage file and parent directory if they don't exist."""
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._write_data({'agents': {}, 'logs': []})

    def _read_data(self) -> Dict[str, Any]:
        """
        Read and parse the storage file.

        Returns:
            Parsed JSON data
        """
        with open(self.path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _write_data(self, data: Dict[str, Any]) -> None:
        """
        Write data to the storage file.

        Args:
            data: Data to write
        """
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def save_agent(self, config: AgentConfig) -> None:
        """
        Save or update an agent configuration.

        Thread-safe operation that updates the agents dictionary.

        Args:
            config: Agent configuration to save
        """
        with self._lock:
            data = self._read_data()
            # Convert Pydantic model to dict with proper serialization
            data['agents'][config.agent_id] = json.loads(
                config.model_dump_json()
            )
            self._write_data(data)

    def load_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """
        Load an agent configuration by ID.

        Thread-safe read operation.

        Args:
            agent_id: Unique identifier for the agent

        Returns:
            Agent configuration if found, None otherwise
        """
        with self._lock:
            data = self._read_data()
            agent_data = data['agents'].get(agent_id)

            if agent_data is None:
                return None

            return AgentConfig.model_validate(agent_data)

    def append_log(self, log_entry: Dict[str, Any]) -> None:
        """
        Append a log entry to the audit log.

        Thread-safe append operation.

        Args:
            log_entry: Log entry dictionary to append
        """
        with self._lock:
            data = self._read_data()
            data['logs'].append(log_entry)
            self._write_data(data)

    def get_logs(
        self,
        agent_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit logs with optional filtering.

        Thread-safe read operation.

        Args:
            agent_id: Optional filter by agent ID
            limit: Optional maximum number of logs to return

        Returns:
            List of log entry dictionaries (most recent first if limited)
        """
        with self._lock:
            data = self._read_data()
            logs = data['logs']

            # Filter by agent_id if specified
            if agent_id is not None:
                logs = [log for log in logs if log.get('agent_id') == agent_id]

            # Apply limit if specified (return most recent)
            if limit is not None and limit > 0:
                logs = logs[-limit:]

            return logs
