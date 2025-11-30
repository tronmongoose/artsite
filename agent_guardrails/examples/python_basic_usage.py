"""
Basic usage example for Agent Guardrails SDK (Python).

This demonstrates:
- Registering an agent
- Setting spending limits
- Defining allowed actions
- Authorizing actions
- Viewing audit logs
"""

from agent_guardrails import Agent


def main():
    print("=== Agent Guardrails SDK - Basic Usage Example ===\n")

    # Register an agent with a wallet address
    print("1. Registering agent...")
    agent = Agent.register(wallet="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb", name="payments_bot")
    print(f"   Agent registered with ID: {agent.agent_id}\n")

    # Set spending limits
    print("2. Setting limits...")
    agent.set_limit("USDC", "25", "24h")  # Max 25 USDC per 24 hours
    agent.set_limit("ETH", "0.01", "1h")   # Max 0.01 ETH per hour
    print("   ✓ USDC limit: 25 per 24 hours")
    print("   ✓ ETH limit: 0.01 per 1 hour\n")

    # Define allowed actions
    print("3. Defining allowed actions...")
    agent.allow_action("swap", protocol="UniswapV3")
    agent.allow_action("transfer", token="USDC")
    print("   ✓ Allowed: swap on UniswapV3")
    print("   ✓ Allowed: transfer USDC\n")

    # Authorize an allowed action within limits
    print("4. Authorizing actions...")
    action1 = {
        "protocol": "UniswapV3",
        "token": "USDC",
        "amount": "10"
    }
    if agent.authorize("swap", action1):
        print(f"   ✓ Allowed: swap 10 USDC on UniswapV3")
    else:
        print(f"   ✗ Denied: swap 10 USDC on UniswapV3")

    # Try another action within limits
    action2 = {
        "protocol": "UniswapV3",
        "token": "USDC",
        "amount": "5"
    }
    if agent.authorize("swap", action2):
        print(f"   ✓ Allowed: swap 5 USDC on UniswapV3")
    else:
        print(f"   ✗ Denied: swap 5 USDC on UniswapV3")

    # Try an action that would exceed limits
    action3 = {
        "protocol": "UniswapV3",
        "token": "USDC",
        "amount": "15"
    }
    if agent.authorize("swap", action3):
        print(f"   ✓ Allowed: swap 15 USDC on UniswapV3")
    else:
        print(f"   ✗ Denied: swap 15 USDC on UniswapV3 (would exceed 24h limit)")

    # Try an action with wrong protocol
    action4 = {
        "protocol": "SushiSwap",  # Not in allowlist
        "token": "USDC",
        "amount": "5"
    }
    if agent.authorize("swap", action4):
        print(f"   ✓ Allowed: swap 5 USDC on SushiSwap")
    else:
        print(f"   ✗ Denied: swap 5 USDC on SushiSwap (protocol not allowed)")

    # Try a disallowed action type
    action5 = {
        "token": "ETH",
        "amount": "0.005"
    }
    if agent.authorize("stake", action5):
        print(f"   ✓ Allowed: stake 0.005 ETH")
    else:
        print(f"   ✗ Denied: stake 0.005 ETH (action type not allowed)")

    print()

    # View audit logs
    print("5. Viewing audit logs...")
    logs = agent.get_logs()
    print(f"   Total actions logged: {len(logs)}\n")

    for i, log in enumerate(logs, 1):
        status = "ALLOWED" if log["allowed"] else "DENIED"
        print(f"   [{i}] {log['timestamp']}")
        print(f"       Action: {log['action_type']}")
        print(f"       Status: {status}")
        if not log["allowed"] and log["reason"]:
            print(f"       Reason: {log['reason']}")
        print()

    print("=== Example Complete ===")
    print(f"\nAgent configuration and logs saved locally at:")
    print(f"~/.agent_guardrails/state.json")


if __name__ == "__main__":
    main()
