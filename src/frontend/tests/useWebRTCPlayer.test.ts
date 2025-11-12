/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { describe, it, expect } from 'vitest';
import { normalizeOfferUrl } from '../src/hooks/useWebRTCPlayer';
import type { ConnectionState } from '../src/hooks/useWebRTCPlayer';

describe('normalizeOfferUrl', () => {
  const fallback = 'http://localhost:8001/offer';

  it('returns fallback when input is undefined', () => {
    expect(normalizeOfferUrl()).toBe(fallback);
  });

  it('adds http scheme and /offer for host-only input', () => {
    expect(normalizeOfferUrl('example.com')).toBe('http://example.com/offer');
  });

  it('appends /offer to a base path', () => {
    expect(normalizeOfferUrl('https://example.com/base')).toBe('https://example.com/base/offer');
  });

  it('removes extra trailing slashes and appends /offer', () => {
    expect(normalizeOfferUrl('https://example.com/base///')).toBe('https://example.com/base/offer');
  });

  it('does not duplicate /offer when already present', () => {
    expect(normalizeOfferUrl('https://example.com/offer')).toBe('https://example.com/offer');
    expect(normalizeOfferUrl('https://example.com/offer/')).toBe('https://example.com/offer');
  });

  it('returns fallback for invalid urls', () => {
    expect(normalizeOfferUrl('http:////')).toBe(fallback);
    expect(normalizeOfferUrl('not a url at all')).toBe(fallback);
  });
});

// Compile-time type checks for ConnectionState
const _idle: ConnectionState = 'idle';
const _connecting: ConnectionState = 'connecting';
const _connected: ConnectionState = 'connected';
const _error: ConnectionState = 'error';

// @ts-expect-error: invalid ConnectionState should error at compile time
const _invalid: ConnectionState = 'paused';

