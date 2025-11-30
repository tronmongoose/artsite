/**
 * Local storage implementation for Agent Guardrails SDK (TypeScript).
 */

import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { AgentConfig, LogEntry, StorageData } from './types';

export interface StorageDriver {
  saveAgent(config: AgentConfig): void;
  loadAgent(agentId: string): AgentConfig | null;
  appendLog(logEntry: LogEntry): void;
  getLogs(agentId?: string, limit?: number): LogEntry[];
}

export class JsonFileStorage implements StorageDriver {
  private filePath: string;

  constructor(filePath?: string) {
    if (filePath) {
      this.filePath = filePath;
    } else {
      const homeDir = os.homedir();
      const storageDir = path.join(homeDir, '.agent_guardrails_js');
      this.filePath = path.join(storageDir, 'state.json');
    }

    this.ensureFileExists();
  }

  private ensureFileExists(): void {
    const dir = path.dirname(this.filePath);

    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    if (!fs.existsSync(this.filePath)) {
      this.writeData({ agents: {}, logs: [] });
    }
  }

  private readData(): StorageData {
    const content = fs.readFileSync(this.filePath, 'utf-8');
    return JSON.parse(content);
  }

  private writeData(data: StorageData): void {
    fs.writeFileSync(this.filePath, JSON.stringify(data, null, 2), 'utf-8');
  }

  saveAgent(config: AgentConfig): void {
    const data = this.readData();
    data.agents[config.agent_id] = config;
    this.writeData(data);
  }

  loadAgent(agentId: string): AgentConfig | null {
    const data = this.readData();
    return data.agents[agentId] || null;
  }

  appendLog(logEntry: LogEntry): void {
    const data = this.readData();
    data.logs.push(logEntry);
    this.writeData(data);
  }

  getLogs(agentId?: string, limit?: number): LogEntry[] {
    const data = this.readData();
    let logs = data.logs;

    if (agentId) {
      logs = logs.filter(log => log.agent_id === agentId);
    }

    if (limit && limit > 0) {
      logs = logs.slice(-limit);
    }

    return logs;
  }
}
