/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { describe, it, expect, vi } from 'vitest';
import {
  clamp,
  getDetectionColor,
  computeDisplayedVideoRect,
  calculateBoundingBoxPixels,
  formatDetectionLabel,
  calculateLabelPosition,
  findBestMetadataMatch,
  calculateTimeOffset,
  normalizeTimestamp,
  isHeldFrameValid,
  sanitizeTimestamp,
  hasLayoutChanged,
  DETECTION_COLORS,
  METADATA_TOLERANCE_MS,
  HOLD_LAST_MS,
} from '../src/lib/overlayUtils';

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

describe('getDetectionColor', () => {
  it('returns first color for index 0', () => {
    expect(getDetectionColor(0)).toBe(DETECTION_COLORS[0]);
  });

  it('cycles through colors', () => {
    for (let i = 0; i < DETECTION_COLORS.length; i++) {
      expect(getDetectionColor(i)).toBe(DETECTION_COLORS[i]);
    }
  });

  it('wraps around after all colors are used', () => {
    expect(getDetectionColor(DETECTION_COLORS.length)).toBe(
      DETECTION_COLORS[0]
    );
    expect(getDetectionColor(DETECTION_COLORS.length + 1)).toBe(
      DETECTION_COLORS[1]
    );
  });

  it('handles large indices', () => {
    const largeIndex = 1000;
    const expectedIndex = largeIndex % DETECTION_COLORS.length;
    expect(getDetectionColor(largeIndex)).toBe(DETECTION_COLORS[expectedIndex]);
  });
});

describe('computeDisplayedVideoRect', () => {
  describe('contain (default)', () => {
    it('scales down to fit width when video is wider', () => {
      const result = computeDisplayedVideoRect(1920, 1080, 800, 600, 'contain');
      // 1920/1080 = 1.78, 800/600 = 1.33, so width is limiting
      // scale = 800/1920 = 0.417, height = 1080 * 0.417 = 450
      expect(result.width).toBe(800);
      expect(result.height).toBe(450);
      expect(result.offsetX).toBe(0);
      expect(result.offsetY).toBe(75); // (600-450)/2
    });

    it('scales down to fit height when video is taller', () => {
      const result = computeDisplayedVideoRect(800, 600, 1920, 1080, 'contain');
      // Container is wider, so height is limiting
      // scale = 1080/600 = 1.8, width = 800 * 1.8 = 1440
      expect(result.height).toBe(1080);
      expect(result.width).toBe(1440);
      expect(result.offsetX).toBe(240); // (1920-1440)/2
      expect(result.offsetY).toBe(0);
    });

    it('handles square video in landscape container', () => {
      const result = computeDisplayedVideoRect(500, 500, 800, 400, 'contain');
      // scale = 400/500 = 0.8
      expect(result.width).toBe(400);
      expect(result.height).toBe(400);
      expect(result.offsetX).toBe(200); // (800-400)/2
      expect(result.offsetY).toBe(0);
    });
  });

  describe('cover', () => {
    it('scales up to cover container when video is smaller', () => {
      const result = computeDisplayedVideoRect(800, 600, 1920, 1080, 'cover');
      // widthRatio = 2.4, heightRatio = 1.8, use max = 2.4
      expect(result.width).toBe(1920);
      expect(result.height).toBe(1440);
      expect(result.offsetX).toBe(0);
      expect(result.offsetY).toBe(-180); // (1080-1440)/2
    });

    it('maintains aspect ratio while covering', () => {
      const result = computeDisplayedVideoRect(1920, 1080, 800, 600, 'cover');
      // widthRatio = 0.417, heightRatio = 0.556, use max = 0.556
      expect(result.height).toBe(600);
      expect(result.width).toBeCloseTo(1066.67, 1);
      expect(result.offsetX).toBeCloseTo(-133.33, 1);
      expect(result.offsetY).toBe(0);
    });
  });

  describe('fill', () => {
    it('stretches to fill container exactly', () => {
      const result = computeDisplayedVideoRect(800, 600, 1920, 1080, 'fill');
      expect(result.width).toBe(1920);
      expect(result.height).toBe(1080);
      expect(result.offsetX).toBe(0);
      expect(result.offsetY).toBe(0);
    });

    it('ignores aspect ratio', () => {
      const result = computeDisplayedVideoRect(500, 500, 800, 400, 'fill');
      expect(result.width).toBe(800);
      expect(result.height).toBe(400);
      expect(result.offsetX).toBe(0);
      expect(result.offsetY).toBe(0);
    });
  });

  describe('none', () => {
    it('uses intrinsic dimensions without scaling', () => {
      const result = computeDisplayedVideoRect(800, 600, 1920, 1080, 'none');
      expect(result.width).toBe(800);
      expect(result.height).toBe(600);
      expect(result.offsetX).toBe(560); // (1920-800)/2
      expect(result.offsetY).toBe(240); // (1080-600)/2
    });

    it('can overflow container if video is larger', () => {
      const result = computeDisplayedVideoRect(1920, 1080, 800, 600, 'none');
      expect(result.width).toBe(1920);
      expect(result.height).toBe(1080);
      expect(result.offsetX).toBe(-560); // (800-1920)/2
      expect(result.offsetY).toBe(-240); // (600-1080)/2
    });
  });

  describe('scale-down', () => {
    it('scales down like contain when video is larger', () => {
      const result = computeDisplayedVideoRect(
        1920,
        1080,
        800,
        600,
        'scale-down'
      );
      // Same as contain when scaling down
      expect(result.width).toBe(800);
      expect(result.height).toBe(450);
    });

    it('uses intrinsic size when video is smaller (no scaling up)', () => {
      const result = computeDisplayedVideoRect(
        400,
        300,
        800,
        600,
        'scale-down'
      );
      // scale would be 2, but min(1, 2) = 1
      expect(result.width).toBe(400);
      expect(result.height).toBe(300);
      expect(result.offsetX).toBe(200);
      expect(result.offsetY).toBe(150);
    });
  });

  describe('edge cases', () => {
    it('handles zero intrinsic dimensions', () => {
      const result = computeDisplayedVideoRect(0, 0, 800, 600, 'contain');
      expect(result.width).toBe(800);
      expect(result.height).toBe(600);
      expect(result.offsetX).toBe(0);
      expect(result.offsetY).toBe(0);
    });

    it('handles zero element dimensions', () => {
      const result = computeDisplayedVideoRect(800, 600, 0, 0, 'contain');
      expect(result.width).toBe(0);
      expect(result.height).toBe(0);
    });

    it('defaults to contain for unknown objectFit', () => {
      const result = computeDisplayedVideoRect(
        1920,
        1080,
        800,
        600,
        'unknown' as any
      );
      const resultDefault = computeDisplayedVideoRect(
        1920,
        1080,
        800,
        600,
        'contain'
      );
      expect(result).toEqual(resultDefault);
    });
  });
});

describe('calculateBoundingBoxPixels', () => {
  const canvasWidth = 1000;
  const canvasHeight = 800;

  it('calculates pixel coordinates from normalized box', () => {
    const box = { x: 0.1, y: 0.2, width: 0.3, height: 0.4 };
    const result = calculateBoundingBoxPixels(box, canvasWidth, canvasHeight);

    expect(result).not.toBeNull();
    expect(result!.x).toBe(100); // 0.1 * 1000
    expect(result!.y).toBe(160); // 0.2 * 800
    expect(result!.width).toBe(300); // 0.3 * 1000
    expect(result!.height).toBe(320); // 0.4 * 800
  });

  it('handles box at origin', () => {
    const box = { x: 0, y: 0, width: 0.5, height: 0.5 };
    const result = calculateBoundingBoxPixels(box, canvasWidth, canvasHeight);

    expect(result).not.toBeNull();
    expect(result!.x).toBe(0);
    expect(result!.y).toBe(0);
    expect(result!.width).toBe(500);
    expect(result!.height).toBe(400);
  });

  it('handles full-size box', () => {
    const box = { x: 0, y: 0, width: 1, height: 1 };
    const result = calculateBoundingBoxPixels(box, canvasWidth, canvasHeight);

    expect(result).not.toBeNull();
    expect(result!.x).toBe(0);
    expect(result!.y).toBe(0);
    expect(result!.width).toBe(1000);
    expect(result!.height).toBe(800);
  });

  it('clamps box that extends beyond canvas right edge', () => {
    const box = { x: 0.8, y: 0.1, width: 0.5, height: 0.2 };
    const result = calculateBoundingBoxPixels(box, canvasWidth, canvasHeight);

    expect(result).not.toBeNull();
    expect(result!.x).toBe(800); // 0.8 * 1000
    expect(result!.width).toBe(200); // clamped: 1000 - 800
  });

  it('clamps box that extends beyond canvas bottom edge', () => {
    const box = { x: 0.1, y: 0.9, width: 0.2, height: 0.5 };
    const result = calculateBoundingBoxPixels(box, canvasWidth, canvasHeight);

    expect(result).not.toBeNull();
    expect(result!.y).toBe(720); // 0.9 * 800
    expect(result!.height).toBe(80); // clamped: 800 - 720
  });

  it('clamps box with negative coordinates', () => {
    const box = { x: -0.1, y: -0.1, width: 0.3, height: 0.3 };
    const result = calculateBoundingBoxPixels(box, canvasWidth, canvasHeight);

    expect(result).not.toBeNull();
    expect(result!.x).toBe(0); // clamped from -100
    expect(result!.y).toBe(0); // clamped from -80
    expect(result!.width).toBe(200); // 300 - 100 (the part inside)
    expect(result!.height).toBe(160); // 240 - 80 (the part inside)
  });

  it('returns null for zero-width box', () => {
    const box = { x: 0.5, y: 0.5, width: 0, height: 0.2 };
    const result = calculateBoundingBoxPixels(box, canvasWidth, canvasHeight);
    expect(result).toBeNull();
  });

  it('returns null for zero-height box', () => {
    const box = { x: 0.5, y: 0.5, width: 0.2, height: 0 };
    const result = calculateBoundingBoxPixels(box, canvasWidth, canvasHeight);
    expect(result).toBeNull();
  });

  it('returns null for box completely outside canvas (left)', () => {
    const box = { x: -0.5, y: 0.5, width: 0.3, height: 0.2 };
    const result = calculateBoundingBoxPixels(box, canvasWidth, canvasHeight);
    expect(result).toBeNull();
  });

  it('returns null for box completely outside canvas (right)', () => {
    const box = { x: 1.5, y: 0.5, width: 0.3, height: 0.2 };
    const result = calculateBoundingBoxPixels(box, canvasWidth, canvasHeight);
    expect(result).toBeNull();
  });

  it('returns null for box completely outside canvas (top)', () => {
    const box = { x: 0.5, y: -0.5, width: 0.2, height: 0.3 };
    const result = calculateBoundingBoxPixels(box, canvasWidth, canvasHeight);
    expect(result).toBeNull();
  });

  it('returns null for box completely outside canvas (bottom)', () => {
    const box = { x: 0.5, y: 1.5, width: 0.2, height: 0.3 };
    const result = calculateBoundingBoxPixels(box, canvasWidth, canvasHeight);
    expect(result).toBeNull();
  });
});

describe('formatDetectionLabel', () => {
  it('formats label with string label and confidence', () => {
    const result = formatDetectionLabel('person', 0.95, undefined);
    expect(result).toBe('person 95%');
  });

  it('formats label with numeric label', () => {
    const result = formatDetectionLabel(0, 0.85, undefined);
    expect(result).toBe('0 85%');
  });

  it('includes distance when provided', () => {
    const result = formatDetectionLabel('car', 0.9, 2.5);
    expect(result).toBe('car 90% | 2.50m');
  });

  it('handles undefined confidence', () => {
    const result = formatDetectionLabel('dog', undefined, undefined);
    expect(result).toBe('dog ?%');
  });

  it('rounds confidence correctly', () => {
    expect(formatDetectionLabel('cat', 0.999, undefined)).toBe('cat 100%');
    expect(formatDetectionLabel('cat', 0.001, undefined)).toBe('cat 0%');
    expect(formatDetectionLabel('cat', 0.555, undefined)).toBe('cat 56%');
  });

  it('formats distance with 2 decimal places', () => {
    const result = formatDetectionLabel('chair', 0.8, 1.234);
    expect(result).toBe('chair 80% | 1.23m');
  });

  it('uses labelResolver when provided', () => {
    const resolver = (label: string | number) =>
      label === 0 ? 'person' : String(label);
    const result = formatDetectionLabel(0, 0.95, undefined, resolver);
    expect(result).toBe('person 95%');
  });

  it('handles zero distance', () => {
    const result = formatDetectionLabel('object', 0.5, 0);
    expect(result).toBe('object 50%'); // 0 is falsy, so no distance shown
  });

  it('handles very small distance', () => {
    const result = formatDetectionLabel('object', 0.5, 0.01);
    expect(result).toBe('object 50% | 0.01m');
  });
});

describe('calculateLabelPosition', () => {
  const canvasWidth = 1000;
  const canvasHeight = 800;
  const textHeight = 18;
  const padding = 6;

  it('positions label above box when there is room', () => {
    const result = calculateLabelPosition(
      100,
      100,
      200,
      textHeight,
      padding,
      100,
      canvasWidth,
      canvasHeight
    );
    expect(result.y).toBe(96); // bboxY - 4
    expect(result.x).toBe(100);
  });

  it('positions label below box when no room above', () => {
    const result = calculateLabelPosition(
      100,
      10,
      200,
      textHeight,
      padding,
      100,
      canvasWidth,
      canvasHeight
    );
    // 10 is not > 18 + 6 = 24, so label goes below
    expect(result.y).toBe(232); // bboxY + bboxHeight + textHeight + 4 = 10 + 200 + 18 + 4
    expect(result.x).toBe(100);
  });

  it('clamps label X to keep within canvas', () => {
    const result = calculateLabelPosition(
      950,
      100,
      200,
      textHeight,
      padding,
      100,
      canvasWidth,
      canvasHeight
    );
    expect(result.x).toBe(900); // canvasWidth - labelWidth
  });

  it('handles label at left edge', () => {
    const result = calculateLabelPosition(
      0,
      100,
      200,
      textHeight,
      padding,
      100,
      canvasWidth,
      canvasHeight
    );
    expect(result.x).toBe(0);
  });

  it('limits label Y to canvas height', () => {
    const result = calculateLabelPosition(
      100,
      10,
      780,
      textHeight,
      padding,
      100,
      canvasWidth,
      canvasHeight
    );
    // Below position would be: 10 + 780 + 18 + 4 = 812, but clamped to 798
    expect(result.y).toBe(798); // canvasHeight - 2
  });

  it('handles box at exact threshold for above/below', () => {
    // Threshold is textHeight + padding = 24
    const result = calculateLabelPosition(
      100,
      24,
      200,
      textHeight,
      padding,
      100,
      canvasWidth,
      canvasHeight
    );
    // 24 is NOT > 24, so label goes below
    expect(result.y).toBe(246); // 24 + 200 + 18 + 4
  });

  it('handles box just above threshold', () => {
    const result = calculateLabelPosition(
      100,
      25,
      200,
      textHeight,
      padding,
      100,
      canvasWidth,
      canvasHeight
    );
    // 25 > 24, so label goes above
    expect(result.y).toBe(21); // 25 - 4
  });
});

describe('findBestMetadataMatch', () => {
  it('returns null for empty buffer', () => {
    const result = findBestMetadataMatch([], 1000, null);
    expect(result).toBeNull();
  });

  it('finds exact match', () => {
    const buffer = [
      { timestamp: 1000, frameId: 1 },
      { timestamp: 2000, frameId: 2 },
      { timestamp: 3000, frameId: 3 },
    ];
    const result = findBestMetadataMatch(buffer, 2000, 0);
    expect(result).not.toBeNull();
    expect(result!.index).toBe(1);
    expect(result!.delta).toBe(0);
  });

  it('finds closest match within tolerance', () => {
    const buffer = [
      { timestamp: 1000, frameId: 1 },
      { timestamp: 2000, frameId: 2 },
    ];
    const result = findBestMetadataMatch(buffer, 1950, 0);
    expect(result).not.toBeNull();
    expect(result!.index).toBe(1);
    expect(result!.delta).toBe(50);
  });

  it('returns null when no match within tolerance', () => {
    const buffer = [{ timestamp: 1000, frameId: 1 }];
    const result = findBestMetadataMatch(buffer, 2000, 0);
    expect(result).toBeNull();
  });

  it('uses first frame to calculate offset when timeOffset is null', () => {
    const buffer = [
      { timestamp: 5000, frameId: 1 },
      { timestamp: 5100, frameId: 2 },
    ];
    // mediaTimeMs = 150, first frame timestamp = 5000
    // offset = 5000 - 150 = 4850
    // adjusted timestamps: 5000-4850=150, 5100-4850=250
    // Looking for 150: closest is frame 1 at 150, delta = 0
    const result = findBestMetadataMatch(buffer, 150, null);
    expect(result).not.toBeNull();
    expect(result!.index).toBe(0);
    expect(result!.delta).toBe(0);
  });

  it('selects second frame when it is closer to media time', () => {
    const buffer = [
      { timestamp: 5000, frameId: 1 },
      { timestamp: 5100, frameId: 2 },
    ];
    // With timeOffset = 4900:
    // adjusted timestamps: 5000-4900=100, 5100-4900=200
    // Looking for 180: frame 1 delta = |100-180| = 80, frame 2 delta = |200-180| = 20
    // Closest is frame 2 at 200, delta = 20
    const result = findBestMetadataMatch(buffer, 180, 4900);
    expect(result).not.toBeNull();
    expect(result!.index).toBe(1);
    expect(result!.delta).toBe(20);
  });

  it('respects provided timeOffset', () => {
    const buffer = [
      { timestamp: 5000, frameId: 1 },
      { timestamp: 5100, frameId: 2 },
    ];
    // With offset 4900, adjusted = 5100 - 4900 = 200
    const result = findBestMetadataMatch(buffer, 200, 4900);
    expect(result).not.toBeNull();
    expect(result!.index).toBe(1);
    expect(result!.delta).toBe(0);
  });

  it('handles negative time offset', () => {
    const buffer = [{ timestamp: 100, frameId: 1 }];
    // offset = 100 - 5000 = -4900
    // adjusted = 100 - (-4900) = 5000
    const result = findBestMetadataMatch(buffer, 5000, -4900);
    expect(result).not.toBeNull();
    expect(result!.delta).toBe(0);
  });

  it('handles edge case just beyond tolerance boundary', () => {
    const buffer = [{ timestamp: 1000, frameId: 1 }];
    // Delta beyond METADATA_TOLERANCE_MS should be rejected
    const result = findBestMetadataMatch(
      buffer,
      1000 + METADATA_TOLERANCE_MS + 1,
      0
    );
    expect(result).toBeNull();
  });

  it('accepts match at tolerance boundary', () => {
    const buffer = [{ timestamp: 1000, frameId: 1 }];
    const result = findBestMetadataMatch(
      buffer,
      1000 + METADATA_TOLERANCE_MS,
      0
    );
    expect(result).not.toBeNull();
  });
});

describe('calculateTimeOffset', () => {
  it('calculates offset correctly', () => {
    expect(calculateTimeOffset(5000, 100)).toBe(4900);
    expect(calculateTimeOffset(100, 5000)).toBe(-4900);
    expect(calculateTimeOffset(1000, 1000)).toBe(0);
  });
});

describe('normalizeTimestamp', () => {
  it('normalizes timestamp by subtracting offset', () => {
    expect(normalizeTimestamp(5000, 4900)).toBe(100);
    expect(normalizeTimestamp(5000, 0)).toBe(5000);
    expect(normalizeTimestamp(100, -4900)).toBe(5000);
  });
});

describe('isHeldFrameValid', () => {
  it('returns true when within hold window', () => {
    expect(isHeldFrameValid(1000, 900)).toBe(true);
    expect(isHeldFrameValid(1000, 1000)).toBe(true);
    expect(isHeldFrameValid(1000 + HOLD_LAST_MS, 1000)).toBe(true);
  });

  it('returns false when outside hold window', () => {
    expect(isHeldFrameValid(1000 + HOLD_LAST_MS + 1, 1000)).toBe(false);
    expect(isHeldFrameValid(2000, 1000)).toBe(false);
  });

  it('returns false when current time is before last rendered', () => {
    expect(isHeldFrameValid(900, 1000)).toBe(false);
  });

  it('respects custom hold duration', () => {
    expect(isHeldFrameValid(1050, 1000, 50)).toBe(true);
    expect(isHeldFrameValid(1051, 1000, 50)).toBe(false);
  });

  it('uses default HOLD_LAST_MS', () => {
    expect(isHeldFrameValid(1000 + HOLD_LAST_MS, 1000)).toBe(true);
  });
});

describe('sanitizeTimestamp', () => {
  it('returns valid timestamp as-is', () => {
    expect(sanitizeTimestamp(12345)).toBe(12345);
    expect(sanitizeTimestamp(0)).toBe(0);
    expect(sanitizeTimestamp(-1000)).toBe(-1000);
  });

  it('returns fallback for undefined', () => {
    const fallback = 99999;
    expect(sanitizeTimestamp(undefined, fallback)).toBe(fallback);
  });

  it('returns fallback for null', () => {
    const fallback = 99999;
    expect(sanitizeTimestamp(null, fallback)).toBe(fallback);
  });

  it('returns fallback for NaN', () => {
    const fallback = 99999;
    expect(sanitizeTimestamp(NaN, fallback)).toBe(fallback);
  });

  it('uses Date.now() as default fallback', () => {
    const nowSpy = vi.spyOn(Date, 'now').mockReturnValue(123456);
    expect(sanitizeTimestamp(undefined)).toBe(123456);
    nowSpy.mockRestore();
  });
});

describe('hasLayoutChanged', () => {
  const base = { width: 100, height: 100, top: 50, left: 50, dpr: 1 };

  it('detects no change when layouts are identical', () => {
    const result = hasLayoutChanged(base, { ...base });
    expect(result.sizeChanged).toBe(false);
    expect(result.positionChanged).toBe(false);
  });

  it('detects size change when width changes beyond threshold', () => {
    const result = hasLayoutChanged({ ...base, width: 101 }, base);
    expect(result.sizeChanged).toBe(true);
    expect(result.positionChanged).toBe(false);
  });

  it('detects size change when height changes beyond threshold', () => {
    const result = hasLayoutChanged({ ...base, height: 101 }, base);
    expect(result.sizeChanged).toBe(true);
    expect(result.positionChanged).toBe(false);
  });

  it('detects size change when dpr changes', () => {
    const result = hasLayoutChanged({ ...base, dpr: 2 }, base);
    expect(result.sizeChanged).toBe(true);
    expect(result.positionChanged).toBe(false);
  });

  it('detects position change when top changes beyond threshold', () => {
    const result = hasLayoutChanged({ ...base, top: 51 }, base);
    expect(result.sizeChanged).toBe(false);
    expect(result.positionChanged).toBe(true);
  });

  it('detects position change when left changes beyond threshold', () => {
    const result = hasLayoutChanged({ ...base, left: 51 }, base);
    expect(result.sizeChanged).toBe(false);
    expect(result.positionChanged).toBe(true);
  });

  it('ignores changes below threshold', () => {
    const result = hasLayoutChanged(
      { ...base, width: 100.4, height: 100.4, top: 50.4, left: 50.4 },
      base
    );
    expect(result.sizeChanged).toBe(false);
    expect(result.positionChanged).toBe(false);
  });

  it('respects custom threshold', () => {
    const result = hasLayoutChanged({ ...base, width: 101 }, base, 2);
    expect(result.sizeChanged).toBe(false);

    const result2 = hasLayoutChanged({ ...base, width: 103 }, base, 2);
    expect(result2.sizeChanged).toBe(true);
  });

  it('detects both size and position change', () => {
    const result = hasLayoutChanged(
      { width: 200, height: 200, top: 100, left: 100, dpr: 2 },
      base
    );
    expect(result.sizeChanged).toBe(true);
    expect(result.positionChanged).toBe(true);
  });
});

describe('constants', () => {
  it('has expected number of detection colors', () => {
    expect(DETECTION_COLORS.length).toBe(8);
  });

  it('has valid hex color format', () => {
    const hexColorRegex = /^#[0-9a-f]{6}$/i;
    DETECTION_COLORS.forEach((color) => {
      expect(color).toMatch(hexColorRegex);
    });
  });

  it('has reasonable tolerance values', () => {
    expect(METADATA_TOLERANCE_MS).toBeGreaterThan(0);
    expect(METADATA_TOLERANCE_MS).toBeLessThan(1000);
    expect(HOLD_LAST_MS).toBeGreaterThan(0);
    expect(HOLD_LAST_MS).toBeLessThan(1000);
  });
});
