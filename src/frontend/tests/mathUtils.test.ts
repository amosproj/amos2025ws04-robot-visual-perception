/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { describe, it, expect, vi } from 'vitest';
import {
  clamp,
  roundToDecimals,
  exponentialBackoff,
  scaleForDPR,
} from '../src/lib/mathUtils';

describe('clamp', () => {
  it('returns value when within bounds', () => {
    expect(clamp(5, 0, 10)).toBe(5);
    expect(clamp(0, 0, 10)).toBe(0);
    expect(clamp(10, 0, 10)).toBe(10);
  });

  it('clamps to min when value is below', () => {
    expect(clamp(-5, 0, 10)).toBe(0);
    expect(clamp(-100, 0, 10)).toBe(0);
  });

  it('clamps to max when value is above', () => {
    expect(clamp(15, 0, 10)).toBe(10);
    expect(clamp(100, 0, 10)).toBe(10);
  });

  it('handles negative ranges', () => {
    expect(clamp(-5, -10, -1)).toBe(-5);
    expect(clamp(-15, -10, -1)).toBe(-10);
    expect(clamp(0, -10, -1)).toBe(-1);
  });

  it('handles floating point values', () => {
    expect(clamp(0.5, 0, 1)).toBe(0.5);
    expect(clamp(1.5, 0, 1)).toBe(1);
    expect(clamp(-0.5, 0, 1)).toBe(0);
  });

  it('handles edge case where min equals max', () => {
    expect(clamp(5, 5, 5)).toBe(5);
    expect(clamp(0, 5, 5)).toBe(5);
    expect(clamp(10, 5, 5)).toBe(5);
  });
});

describe('roundToDecimals', () => {
  it('rounds to 0 decimal places', () => {
    expect(roundToDecimals(3.14159, 0)).toBe(3);
    expect(roundToDecimals(3.5, 0)).toBe(4);
    expect(roundToDecimals(3.49, 0)).toBe(3);
  });

  it('rounds to 1 decimal place', () => {
    expect(roundToDecimals(3.14159, 1)).toBe(3.1);
    expect(roundToDecimals(3.15, 1)).toBe(3.2);
    expect(roundToDecimals(3.14, 1)).toBe(3.1);
  });

  it('rounds to 2 decimal places', () => {
    expect(roundToDecimals(3.14159, 2)).toBe(3.14);
    expect(roundToDecimals(3.145, 2)).toBe(3.15);
    expect(roundToDecimals(3.144, 2)).toBe(3.14);
  });

  it('handles negative numbers', () => {
    expect(roundToDecimals(-3.14159, 2)).toBe(-3.14);
    expect(roundToDecimals(-3.145, 2)).toBe(-3.14); // Note: JS rounds toward zero
  });

  it('handles zero', () => {
    expect(roundToDecimals(0, 2)).toBe(0);
  });

  it('handles already rounded values', () => {
    expect(roundToDecimals(5, 2)).toBe(5);
    expect(roundToDecimals(5.5, 1)).toBe(5.5);
  });
});

describe('exponentialBackoff', () => {
  it('returns base delay for attempt 0', () => {
    expect(exponentialBackoff(0)).toBe(1000);
  });

  it('doubles delay for each attempt', () => {
    expect(exponentialBackoff(0)).toBe(1000);
    expect(exponentialBackoff(1)).toBe(2000);
    expect(exponentialBackoff(2)).toBe(4000);
    expect(exponentialBackoff(3)).toBe(8000);
  });

  it('caps at max delay', () => {
    expect(exponentialBackoff(10)).toBe(30000); // 2^10 * 1000 = 1024000, capped to 30000
    expect(exponentialBackoff(100)).toBe(30000);
  });

  it('respects custom base delay', () => {
    expect(exponentialBackoff(0, 500)).toBe(500);
    expect(exponentialBackoff(1, 500)).toBe(1000);
    expect(exponentialBackoff(2, 500)).toBe(2000);
  });

  it('respects custom max delay', () => {
    expect(exponentialBackoff(10, 1000, 5000)).toBe(5000);
    expect(exponentialBackoff(2, 1000, 3000)).toBe(3000);
  });

  it('handles edge case where base exceeds max', () => {
    expect(exponentialBackoff(0, 5000, 3000)).toBe(3000);
  });
});

describe('scaleForDPR', () => {
  it('scales value by DPR', () => {
    expect(scaleForDPR(100, 1)).toBe(100);
    expect(scaleForDPR(100, 2)).toBe(200);
    expect(scaleForDPR(100, 3)).toBe(300);
  });

  it('rounds to nearest integer', () => {
    expect(scaleForDPR(100, 1.5)).toBe(150);
    expect(scaleForDPR(100, 1.25)).toBe(125);
    expect(scaleForDPR(100, 1.24)).toBe(124);
  });

  it('enforces minimum value', () => {
    expect(scaleForDPR(0, 2)).toBe(1);
    expect(scaleForDPR(0.3, 2)).toBe(1);
  });

  it('respects custom minimum value', () => {
    expect(scaleForDPR(0, 2, 5)).toBe(5);
    expect(scaleForDPR(1, 2, 5)).toBe(5);
    expect(scaleForDPR(3, 2, 5)).toBe(6);
  });

  it('handles fractional DPR values', () => {
    expect(scaleForDPR(640, 1.5)).toBe(960);
    expect(scaleForDPR(480, 1.5)).toBe(720);
  });

  it('handles small values', () => {
    expect(scaleForDPR(1, 1)).toBe(1);
    expect(scaleForDPR(1, 2)).toBe(2);
  });
});
