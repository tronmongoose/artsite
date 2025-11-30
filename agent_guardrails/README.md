# Agent Guardrails SDK

**Lightweight safety, permissions, and spend limits for autonomous AI agents.**

[![Python Tests](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/typescript-5.0%2B-blue)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

AI agents are starting to make decisions, move money, interact with DeFi, and execute transactions. The missing piece is **trust**.

Agent Guardrails SDK solves this by adding **identity**, **authorization**, **limits**, and **auditability** to autonomous agent execution—with:

- ✅ **Zero custody** - Never touches private keys
- ✅ **Zero network calls** - Runs entirely locally
- ✅ **Zero infrastructure** - No servers, no databases, no setup
- ✅ **100% deterministic** - Same inputs → same outputs, always
- ✅ **Framework-agnostic** - Works with any agent, wallet, or execution layer

Think of it like **Plaid/Okta for agent actions**.

---

## Why Use This?

Because you want to safely allow your agent to:

- Swap tokens
- Transfer stablecoins
- Manage a treasury
- Execute payments
- Call DeFi protocols

**without giving it a free hand.**

With Agent Guardrails SDK you can:

- ✅ Restrict which actions are allowed
- ✅ Cap spend per token or per time window
- ✅ Whitelist protocols/addresses
- ✅ Log every decision locally
- ✅ Enforce rules deterministically

---

## Installation

### Python

```bash
pip install agent-guardrails
```

### Node/TypeScript

```bash
npm install agent-guardrails
```

No external services. No config required.

---

## Quick Start

### Python

```python
from agent_guardrails import Agent

# Register an agent
agent = Agent.register(wallet="0x123", name="payments_bot")

# Set limits and controls
agent.set_limit("USDC", "25", "24h")  # Max 25 USDC per 24 hours
agent.allow_action("swap", protocol="UniswapV3")

# Authorize before executing
if agent.authorize("swap", {"token": "USDC", "amount": "10", "protocol": "UniswapV3"}):
    execute_swap()  # Your execution logic
else:
    print("Action denied by guardrails")
```

### TypeScript

```typescript
import { Agent } from 'agent-guardrails';

// Register an agent
const agent = Agent.register({ wallet: "0x123", name: "payments_bot" });

// Set limits and controls
agent.setLimit("USDC", "25", "24h");
agent.allowAction("swap", { protocol: "UniswapV3" });

// Authorize before executing
if (agent.authorize("swap", { token: "USDC", amount: "10", protocol: "UniswapV3" })) {
  executeSwap();  // Your execution logic
} else {
  console.log("Action denied by guardrails");
}
```

---

## Core API

### Registration

```python
agent = Agent.register(
    wallet="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    name="my_agent",  # optional
    metadata={"env": "production"}  # optional
)
```

### Setting Limits

```python
# Set spending limits with time windows
agent.set_limit("USDC", "100", "24h")  # 100 USDC per day
agent.set_limit("ETH", "0.5", "1h")     # 0.5 ETH per hour
agent.set_limit("DAI", "50", "7d")      # 50 DAI per week
```

**Supported time windows:** `1h`, `24h`, `7d`, etc.

### Allowing Actions

```python
# Allow actions with optional constraints
agent.allow_action("swap", protocol="UniswapV3")
agent.allow_action("transfer", token="USDC")
agent.allow_action("stake")  # No constraints
```

### Authorization

```python
# Authorize returns True/False
allowed = agent.authorize("swap", {
    "token": "USDC",
    "amount": "10",
    "protocol": "UniswapV3"
})

if allowed:
    # Execute the action
    ...
else:
    # Handle denial
    ...
```

### Audit Logs

```python
# Get logs for this agent
logs = agent.get_logs(limit=10)  # Most recent 10 logs

for log in logs:
    print(f"{log['timestamp']}: {log['action_type']} - {log['allowed']}")
    if not log['allowed']:
        print(f"  Reason: {log['reason']}")
```

---

## How It Works

```
┌──────────┐
│  Agent   │  Decides to swap 10 USDC
└────┬─────┘
     │
     v
┌──────────────────┐
│   Guardrails     │  Checks:
│   SDK           │  1. Is "swap" allowed?
│                 │  2. Protocol matches?
│                 │  3. Under 24h limit?
└────┬─────────────┘
     │
     ├─── TRUE  ──→  Execute swap
     │
     └─── FALSE ──→  Deny + Log reason
```

The SDK sits **between** your agent's decision and execution, providing a deterministic safety boundary.

---

## Key Principles

### 1. Deterministic

No randomness, no ML, no fuzzy matching. Same inputs always produce the same outputs.

### 2. Fail-Safe

Unknown actions → **deny**
Malformed requests → **deny**
Errors → **deny**

### 3. Zero Custody

The SDK **never**:
- Holds private keys
- Signs transactions
- Executes on-chain actions
- Has custody of funds

### 4. Local-First

All data stays on your machine:
- **Python:** `~/.agent_guardrails/state.json`
- **TypeScript:** `~/.agent_guardrails_js/state.json`

No telemetry. No remote logging. No external calls.

### 5. Framework-Agnostic

Works with:
- Any agent framework
- Any wallet (Safe, EOA, AA, etc.)
- Any execution layer
- Any blockchain

---

## Use Cases

### Autonomous Treasury Management

```python
agent = Agent.register(wallet="0x...", name="treasury_manager")
agent.set_limit("USDC", "10000", "24h")
agent.set_limit("ETH", "5", "24h")
agent.allow_action("swap", protocol="UniswapV3")
agent.allow_action("stake", protocol="Lido")
```

### Payment Bots

```python
agent = Agent.register(wallet="0x...", name="payment_bot")
agent.set_limit("USDC", "100", "24h")
agent.allow_action("transfer", token="USDC")
```

### DeFi Automation

```python
agent = Agent.register(wallet="0x...", name="defi_bot")
agent.set_limit("DAI", "5000", "7d")
agent.allow_action("deposit", protocol="Aave")
agent.allow_action("withdraw", protocol="Aave")
agent.allow_action("swap", protocol="UniswapV3")
```

---

## Architecture

### Authorization Flow

1. **Agent** calls `authorize(action_type, params)`
2. **Check allowlist:** Is this action_type + constraints allowed?
   - If **no** → Log deny + return `False`
3. **Check limits:** Would this exceed spending limits?
   - If **yes** → Log deny + return `False`
4. **Log allow** + return `True`

### Storage

- **Format:** JSON file
- **Schema:**
  ```json
  {
    "agents": {
      "agent-uuid": {
        "agent_id": "...",
        "wallet": "...",
        "limits": {...},
        "allow_rules": [...]
      }
    },
    "logs": [
      {
        "timestamp": "2025-11-30T12:00:00Z",
        "agent_id": "...",
        "action_type": "swap",
        "params": {...},
        "allowed": true,
        "reason": null
      }
    ]
  }
  ```

---

## Development

### Running Tests

**Python:**
```bash
cd python
pip install -e ".[dev]"
pytest -v
```

**TypeScript:**
```bash
cd js
npm install
npm test
```

### Running Examples

**Python:**
```bash
python examples/python_basic_usage.py
```

**TypeScript:**
```bash
ts-node examples/js_basic_usage.ts
```

---

## Philosophy

Agent Guardrails SDK is designed to be:

1. **As simple as adding middleware**
2. **Deterministic and explicit**
3. **Portable across chains and frameworks**
4. **The smallest abstraction that solves trust**

We believe AI agents should be able to act autonomously, but **only within boundaries you define**.

---

## Roadmap

- **v1.0** (Current): Python + Node SDK, local rules, audit logging
- **v1.5**: Declarative config (YAML), CLI tools, rule presets
- **v2.0**: Plugin system, remote log sync, advanced policies
- **v3.0**: Multi-agent governance, organization-level policies

---

## Contributing

We want feedback from real builders. If you:

- Find a bug → [Open an issue](https://github.com/yourusername/agent-guardrails/issues)
- Have a feature request → [Start a discussion](https://github.com/yourusername/agent-guardrails/discussions)
- Want to contribute → [Submit a PR](https://github.com/yourusername/agent-guardrails/pulls)

This SDK exists because the ecosystem needs a shared safety layer for agent actions.

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

Built for the next generation of autonomous systems.

Inspired by the need for trust boundaries in AI-driven financial operations.

---

## Support

- 📖 [Documentation](#) (Coming soon)
- 💬 [Discord](#) (Coming soon)
- 🐦 [Twitter](#) (Coming soon)

---

**Agent Guardrails SDK** - Because agents need boundaries, not babysitters.
