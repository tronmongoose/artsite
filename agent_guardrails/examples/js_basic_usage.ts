/**
 * Basic usage example for Agent Guardrails SDK (TypeScript).
 *
 * This demonstrates:
 * - Registering an agent
 * - Setting spending limits
 * - Defining allowed actions
 * - Authorizing actions
 * - Viewing audit logs
 */

import { Agent } from '../js/src';

function main() {
  console.log('=== Agent Guardrails SDK - Basic Usage Example (TypeScript) ===\n');

  // Register an agent with a wallet address
  console.log('1. Registering agent...');
  const agent = Agent.register({
    wallet: '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb',
    name: 'payments_bot',
  });
  console.log(`   Agent registered with ID: ${agent.getAgentId()}\n`);

  // Set spending limits
  console.log('2. Setting limits...');
  agent.setLimit('USDC', '25', '24h'); // Max 25 USDC per 24 hours
  agent.setLimit('ETH', '0.01', '1h'); // Max 0.01 ETH per hour
  console.log('   ✓ USDC limit: 25 per 24 hours');
  console.log('   ✓ ETH limit: 0.01 per 1 hour\n');

  // Define allowed actions
  console.log('3. Defining allowed actions...');
  agent.allowAction('swap', { protocol: 'UniswapV3' });
  agent.allowAction('transfer', { token: 'USDC' });
  console.log('   ✓ Allowed: swap on UniswapV3');
  console.log('   ✓ Allowed: transfer USDC\n');

  // Authorize an allowed action within limits
  console.log('4. Authorizing actions...');
  const action1 = {
    protocol: 'UniswapV3',
    token: 'USDC',
    amount: '10',
  };
  if (agent.authorize('swap', action1)) {
    console.log('   ✓ Allowed: swap 10 USDC on UniswapV3');
  } else {
    console.log('   ✗ Denied: swap 10 USDC on UniswapV3');
  }

  // Try another action within limits
  const action2 = {
    protocol: 'UniswapV3',
    token: 'USDC',
    amount: '5',
  };
  if (agent.authorize('swap', action2)) {
    console.log('   ✓ Allowed: swap 5 USDC on UniswapV3');
  } else {
    console.log('   ✗ Denied: swap 5 USDC on UniswapV3');
  }

  // Try an action that would exceed limits
  const action3 = {
    protocol: 'UniswapV3',
    token: 'USDC',
    amount: '15',
  };
  if (agent.authorize('swap', action3)) {
    console.log('   ✓ Allowed: swap 15 USDC on UniswapV3');
  } else {
    console.log('   ✗ Denied: swap 15 USDC on UniswapV3 (would exceed 24h limit)');
  }

  // Try an action with wrong protocol
  const action4 = {
    protocol: 'SushiSwap', // Not in allowlist
    token: 'USDC',
    amount: '5',
  };
  if (agent.authorize('swap', action4)) {
    console.log('   ✓ Allowed: swap 5 USDC on SushiSwap');
  } else {
    console.log('   ✗ Denied: swap 5 USDC on SushiSwap (protocol not allowed)');
  }

  // Try a disallowed action type
  const action5 = {
    token: 'ETH',
    amount: '0.005',
  };
  if (agent.authorize('stake', action5)) {
    console.log('   ✓ Allowed: stake 0.005 ETH');
  } else {
    console.log('   ✗ Denied: stake 0.005 ETH (action type not allowed)');
  }

  console.log();

  // View audit logs
  console.log('5. Viewing audit logs...');
  const logs = agent.getLogs();
  console.log(`   Total actions logged: ${logs.length}\n`);

  logs.forEach((log, i) => {
    const status = log.allowed ? 'ALLOWED' : 'DENIED';
    console.log(`   [${i + 1}] ${log.timestamp}`);
    console.log(`       Action: ${log.action_type}`);
    console.log(`       Status: ${status}`);
    if (!log.allowed && log.reason) {
      console.log(`       Reason: ${log.reason}`);
    }
    console.log();
  });

  console.log('=== Example Complete ===');
  console.log('\nAgent configuration and logs saved locally at:');
  console.log('~/.agent_guardrails_js/state.json');
}

main();
