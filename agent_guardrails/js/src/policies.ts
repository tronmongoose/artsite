/**
 * Pure policy logic for Agent Guardrails SDK (TypeScript).
 */

import { AllowRule, LimitConfig, LogEntry } from './types';
import { StorageDriver } from './storage';

export function parseTimeWindow(window: string): number {
  const pattern = /^(\d+)([hd])$/i;
  const match = window.match(pattern);

  if (!match) {
    throw new Error(
      `Invalid time window format: '${window}'. Expected format: <number><h|d> (e.g., '24h', '7d')`
    );
  }

  const amount = parseInt(match[1], 10);
  const unit = match[2].toLowerCase();

  if (unit === 'h') {
    return amount * 3600;
  } else if (unit === 'd') {
    return amount * 86400;
  } else {
    throw new Error(`Unknown time unit: ${unit}`);
  }
}

export function isActionAllowedByRules(
  actionType: string,
  params: Record<string, any>,
  rules: AllowRule[]
): boolean {
  const relevantRules = rules.filter(r => r.action_type === actionType);

  if (relevantRules.length === 0) {
    return false;
  }

  for (const rule of relevantRules) {
    if (ruleMatches(rule, params)) {
      return true;
    }
  }

  return false;
}

function ruleMatches(rule: AllowRule, params: Record<string, any>): boolean {
  if (!rule.constraints || Object.keys(rule.constraints).length === 0) {
    return true;
  }

  for (const [key, expectedValue] of Object.entries(rule.constraints)) {
    const actualValue = params[key];
    if (String(actualValue) !== String(expectedValue)) {
      return false;
    }
  }

  return true;
}

export function isWithinLimits(
  asset: string,
  amount: string,
  limitCfg: LimitConfig,
  storage: StorageDriver,
  agentId: string,
  now: Date
): boolean {
  if (asset !== limitCfg.asset) {
    return false;
  }

  const windowStart = new Date(now.getTime() - limitCfg.window_seconds * 1000);
  const allLogs = storage.getLogs(agentId);

  let totalSpent = 0;

  for (const log of allLogs) {
    if (!log.allowed) {
      continue;
    }

    let logTime: Date;
    try {
      logTime = new Date(log.timestamp);
    } catch {
      continue;
    }

    if (logTime < windowStart) {
      continue;
    }

    const logParams = log.params || {};
    const logAsset = logParams.asset || logParams.token;

    if (logAsset === asset) {
      const logAmount = logParams.amount;
      if (logAmount !== undefined && logAmount !== null) {
        try {
          totalSpent += parseFloat(String(logAmount));
        } catch {
          continue;
        }
      }
    }
  }

  const requestAmount = parseFloat(amount);
  const limitAmount = parseFloat(limitCfg.amount);

  return (totalSpent + requestAmount) <= limitAmount;
}
