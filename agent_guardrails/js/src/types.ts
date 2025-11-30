/**
 * Type definitions for Agent Guardrails SDK (TypeScript).
 *
 * Mirrors the Python implementation using TypeScript interfaces and types.
 */

export interface LimitConfig {
  asset: string;
  amount: string; // Use string to avoid floating-point issues
  window_seconds: number;
}

export interface AllowRule {
  action_type: string;
  constraints: Record<string, any>;
}

export interface AgentConfig {
  agent_id: string;
  wallet: string;
  name?: string;
  metadata: Record<string, any>;
  limits: Record<string, LimitConfig>;
  allow_rules: AllowRule[];
}

export interface ActionParams {
  asset?: string;
  amount?: string;
  protocol?: string;
  chain_id?: number;
  to_address?: string;
  [key: string]: any; // Allow arbitrary additional fields
}

export interface LogEntry {
  timestamp: string;
  agent_id: string;
  action_type: string;
  params: Record<string, any>;
  allowed: boolean;
  reason?: string;
}

export interface StorageData {
  agents: Record<string, AgentConfig>;
  logs: LogEntry[];
}
