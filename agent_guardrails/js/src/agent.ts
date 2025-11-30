/**
 * Agent class for Agent Guardrails SDK (TypeScript).
 */

import { v4 as uuidv4 } from 'uuid';
import { AgentConfig, AllowRule, LimitConfig, LogEntry, ActionParams } from './types';
import { StorageDriver, JsonFileStorage } from './storage';
import { parseTimeWindow, isActionAllowedByRules, isWithinLimits } from './policies';

export class Agent {
  private agentId: string;
  private storage: StorageDriver;
  private config: AgentConfig | null = null;

  private constructor(agentId: string, storage: StorageDriver) {
    this.agentId = agentId;
    this.storage = storage;
  }

  static register(options: {
    wallet: string;
    name?: string;
    metadata?: Record<string, any>;
    storage?: StorageDriver;
  }): Agent {
    const agentId = uuidv4();
    const storage = options.storage || new JsonFileStorage();

    const config: AgentConfig = {
      agent_id: agentId,
      wallet: options.wallet,
      name: options.name,
      metadata: options.metadata || {},
      limits: {},
      allow_rules: [],
    };

    storage.saveAgent(config);

    const agent = new Agent(agentId, storage);
    agent.config = config;
    return agent;
  }

  private loadConfig(): AgentConfig {
    if (!this.config) {
      this.config = this.storage.loadAgent(this.agentId);
    }

    if (!this.config) {
      throw new Error(`Agent ${this.agentId} not found in storage`);
    }

    return this.config;
  }

  private saveConfig(): void {
    if (this.config) {
      this.storage.saveAgent(this.config);
    }
  }

  setLimit(asset: string, amount: string | number, window: string): void {
    const config = this.loadConfig();

    const windowSeconds = parseTimeWindow(window);
    const amountStr = String(amount);

    const limitCfg: LimitConfig = {
      asset,
      amount: amountStr,
      window_seconds: windowSeconds,
    };

    config.limits[asset] = limitCfg;
    this.config = config;
    this.saveConfig();
  }

  allowAction(actionType: string, constraints?: Record<string, any>): void {
    const config = this.loadConfig();

    const rule: AllowRule = {
      action_type: actionType,
      constraints: constraints || {},
    };

    config.allow_rules.push(rule);
    this.config = config;
    this.saveConfig();
  }

  authorize(actionType: string, params: Record<string, any>): boolean {
    try {
      const config = this.loadConfig();
      const now = new Date();

      // Check 1: Is action allowed by rules?
      if (!isActionAllowedByRules(actionType, params, config.allow_rules)) {
        this.logDecision(actionType, params, false, 'Action not in allowlist');
        return false;
      }

      // Check 2: If amount/asset present and limit exists, check limits
      const amount = params.amount;
      const asset = params.asset || params.token;

      if (amount && asset && config.limits[asset]) {
        const limitCfg = config.limits[asset];

        if (!isWithinLimits(asset, String(amount), limitCfg, this.storage, this.agentId, now)) {
          this.logDecision(
            actionType,
            params,
            false,
            `Exceeds ${asset} limit of ${limitCfg.amount} per ${limitCfg.window_seconds}s`
          );
          return false;
        }
      }

      // All checks passed
      this.logDecision(actionType, params, true);
      return true;
    } catch (error) {
      // Fail-safe: deny on any error
      const errorMessage = error instanceof Error ? error.message : String(error);
      this.logDecision(actionType, params, false, `Error during authorization: ${errorMessage}`);
      return false;
    }
  }

  private logDecision(
    actionType: string,
    params: Record<string, any>,
    allowed: boolean,
    reason?: string
  ): void {
    const logEntry: LogEntry = {
      timestamp: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
      agent_id: this.agentId,
      action_type: actionType,
      params,
      allowed,
      reason,
    };

    this.storage.appendLog(logEntry);
  }

  getLogs(limit?: number): LogEntry[] {
    return this.storage.getLogs(this.agentId, limit);
  }

  getAgentId(): string {
    return this.agentId;
  }
}
