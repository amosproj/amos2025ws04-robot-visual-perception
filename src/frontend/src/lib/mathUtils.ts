/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

/**
 * Clamp a value between min and max bounds
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Round a number to a specific number of decimal places
 */
export function roundToDecimals(value: number, decimals: number): number {
  const factor = Math.pow(10, decimals);
  return Math.round(value * factor) / factor;
}

/**
 * Calculate exponential backoff delay for reconnection attempts
 */
export function exponentialBackoff(
  attempt: number,
  baseMs: number = 1000,
  maxMs: number = 30000
): number {
  return Math.min(baseMs * Math.pow(2, attempt), maxMs);
}
