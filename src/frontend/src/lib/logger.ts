/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

type LogFormat = 'json' | 'pretty';

const levelWeights: Record<LogLevel, number> = {
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
};

function parseLevel(raw?: string): LogLevel {
  const value = raw?.toLowerCase();
  if (value === 'debug' || value === 'info' || value === 'warn' || value === 'error') {
    return value;
  }
  return 'info';
}

function parseFormat(raw?: string): LogFormat {
  const value = raw?.toLowerCase();
  if (value === 'json' || value === 'pretty') {
    return value;
  }
  return 'pretty';
}

const envLevel = parseLevel((import.meta as any)?.env?.VITE_LOG_LEVEL);
const envFormat = parseFormat((import.meta as any)?.env?.VITE_LOG_FORMAT);

export interface LogContext {
  component?: string;
  [key: string]: unknown;
}

export interface LogEntry {
  level: LogLevel;
  event: string;
  message?: string;
  data?: Record<string, unknown>;
  context?: LogContext;
  timestamp: string;
}

type Transport = (entry: LogEntry) => void;

function consoleTransport(entry: LogEntry) {
  const payload = {
    ts: entry.timestamp,
    level: entry.level,
    event: entry.event,
    message: entry.message,
    ...entry.context,
    ...entry.data,
  };

  if (envFormat === 'json') {
    const fn = console[entry.level] ?? console.log;
    fn(JSON.stringify(payload));
    return;
  }

  const fn = console[entry.level] ?? console.log;
  const parts = [
    `[${payload.ts}]`,
    entry.level.toUpperCase(),
    entry.event,
    entry.message ?? '',
  ].filter(Boolean);

  fn(parts.join(' - '), entry.data ?? {}, entry.context ?? {});
}

export interface Logger {
  debug: (event: string, data?: Record<string, unknown>, message?: string) => void;
  info: (event: string, data?: Record<string, unknown>, message?: string) => void;
  warn: (event: string, data?: Record<string, unknown>, message?: string) => void;
  error: (event: string, data?: Record<string, unknown>, message?: string) => void;
  child: (context: LogContext) => Logger;
}

function createLogger(baseContext: LogContext = {}, transports: Transport[] = [consoleTransport]): Logger {
  const threshold = levelWeights[envLevel];

  const log = (level: LogLevel, event: string, data?: Record<string, unknown>, message?: string) => {
    if (levelWeights[level] < threshold) return;
    const entry: LogEntry = {
      level,
      event,
      message,
      data,
      context: baseContext,
      timestamp: new Date().toISOString(),
    };
    transports.forEach((t) => t(entry));
  };

  return {
    debug: (event, data, message) => log('debug', event, data, message),
    info: (event, data, message) => log('info', event, data, message),
    warn: (event, data, message) => log('warn', event, data, message),
    error: (event, data, message) => log('error', event, data, message),
    child: (context: LogContext) => createLogger({ ...baseContext, ...context }, transports),
  };
}

export const logger = createLogger({ app: 'robot-visual-perception' });
