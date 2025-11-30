/**
 * Agent Guardrails SDK (TypeScript)
 *
 * Lightweight safety, permissions, and spend limits for autonomous AI agents.
 */

export { Agent } from './agent';
export { AuthorizationError } from './errors';
export type {
  AgentConfig,
  LimitConfig,
  AllowRule,
  ActionParams,
  LogEntry,
  StorageData,
} from './types';
export { StorageDriver, JsonFileStorage } from './storage';
