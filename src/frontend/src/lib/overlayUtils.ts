/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

/**
 * Overlay drawing utility functions
 * These are pure functions extracted from VideoOverlay for testability
 */

/**
 * Color palette for detection bounding boxes
 */
export const DETECTION_COLORS = [
  '#00d4ff',
  '#00ff88',
  '#ff6b9d',
  '#ffd93d',
  '#ff8c42',
  '#a8e6cf',
  '#b4a5ff',
  '#ffb347',
] as const;

/**
 * Color for interpolated detections
 */
export const INTERPOLATED_COLOR = '#808080';

/**
 * Tolerance window for metadata timestamp matching (in milliseconds)
 */
export const METADATA_TOLERANCE_MS = 120;

/**
 * How long to hold last overlay frame to reduce flicker (in milliseconds)
 */
export const HOLD_LAST_MS = 150;

/**
 * Clamp a value between min and max bounds
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Get the color for a detection based on its index
 */
export function getDetectionColor(
  label: string | number,
  interpolated: boolean = false
): string {
  // Use label (class ID) for consistent colors per class
  const index =
    typeof label === 'number' ? label : parseInt(String(label), 10) || 0;

  // Color scheme - use black for interpolated detections
  // For real detections, use color based on class ID for consistency
  if (interpolated) return INTERPOLATED_COLOR;
  else return DETECTION_COLORS[index % DETECTION_COLORS.length];
}

/**
 * Normalized bounding box coordinates (0-1 range)
 */
export interface NormalizedBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Pixel coordinates for rendering a bounding box
 */
export interface PixelBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Result of computing the displayed video rectangle
 */
export interface DisplayedVideoRect {
  width: number;
  height: number;
  offsetX: number;
  offsetY: number;
}

/**
 * Object-fit CSS values
 */
export type ObjectFit = 'contain' | 'cover' | 'fill' | 'none' | 'scale-down';

/**
 * Compute the displayed video rectangle based on object-fit CSS property
 *
 * @param intrinsicWidth - The natural width of the video
 * @param intrinsicHeight - The natural height of the video
 * @param elementWidth - The width of the video element container
 * @param elementHeight - The height of the video element container
 * @param objectFit - The CSS object-fit value
 * @returns The computed display dimensions and offsets
 */
export function computeDisplayedVideoRect(
  intrinsicWidth: number,
  intrinsicHeight: number,
  elementWidth: number,
  elementHeight: number,
  objectFit: ObjectFit = 'contain'
): DisplayedVideoRect {
  // Handle missing dimensions
  if (!intrinsicWidth || !intrinsicHeight) {
    return {
      width: elementWidth,
      height: elementHeight,
      offsetX: 0,
      offsetY: 0,
    };
  }

  const widthRatio = elementWidth / intrinsicWidth;
  const heightRatio = elementHeight / intrinsicHeight;
  let renderWidth = elementWidth;
  let renderHeight = elementHeight;

  switch (objectFit) {
    case 'cover': {
      const scale = Math.max(widthRatio, heightRatio);
      renderWidth = intrinsicWidth * scale;
      renderHeight = intrinsicHeight * scale;
      break;
    }
    case 'fill': {
      renderWidth = elementWidth;
      renderHeight = elementHeight;
      break;
    }
    case 'none': {
      renderWidth = intrinsicWidth;
      renderHeight = intrinsicHeight;
      break;
    }
    case 'scale-down': {
      const scale = Math.min(1, Math.min(widthRatio, heightRatio));
      renderWidth = intrinsicWidth * scale;
      renderHeight = intrinsicHeight * scale;
      break;
    }
    case 'contain':
    default: {
      const scale = Math.min(widthRatio, heightRatio);
      renderWidth = intrinsicWidth * scale;
      renderHeight = intrinsicHeight * scale;
    }
  }

  const offsetX = (elementWidth - renderWidth) / 2;
  const offsetY = (elementHeight - renderHeight) / 2;

  return { width: renderWidth, height: renderHeight, offsetX, offsetY };
}

/**
 * Calculate pixel coordinates for a bounding box, clamped to canvas bounds
 *
 * @param box - Normalized bounding box (0-1 range)
 * @param canvasWidth - Width of the canvas in pixels
 * @param canvasHeight - Height of the canvas in pixels
 * @returns Pixel coordinates for the bounding box, or null if box has zero area
 */
export function calculateBoundingBoxPixels(
  box: NormalizedBox,
  canvasWidth: number,
  canvasHeight: number
): PixelBox | null {
  const rawX = box.x * canvasWidth;
  const rawY = box.y * canvasHeight;
  const rawWidth = box.width * canvasWidth;
  const rawHeight = box.height * canvasHeight;

  const bboxX = clamp(rawX, 0, canvasWidth);
  const bboxY = clamp(rawY, 0, canvasHeight);
  const bboxMaxX = clamp(rawX + rawWidth, 0, canvasWidth);
  const bboxMaxY = clamp(rawY + rawHeight, 0, canvasHeight);
  const bboxWidth = Math.max(0, bboxMaxX - bboxX);
  const bboxHeight = Math.max(0, bboxMaxY - bboxY);

  // Return null if the box has no visible area
  if (bboxWidth === 0 || bboxHeight === 0) {
    return null;
  }

  return {
    x: bboxX,
    y: bboxY,
    width: bboxWidth,
    height: bboxHeight,
  };
}

/**
 * Format a detection label with confidence and optional distance
 *
 * @param label - The detection label (class name or ID)
 * @param confidence - Confidence score (0-1)
 * @param distance - Optional distance in meters
 * @param resolveLabel - Optional function to resolve label to display string
 * @returns Formatted label string
 */
export function formatDetectionLabel(
  label: string | number,
  confidence?: number,
  distance?: number,
  resolveLabel?: (
    value: string | number,
    providedLabelText?: string | undefined
  ) => string,
  labelText?: string
): string {
  const getActualLabel = () => {
    if (resolveLabel) return resolveLabel(label, labelText);
    if (labelText) return labelText;
    return String(label);
  };

  // Label + distance
  const resolvedLabelText = `${getActualLabel()} ${
    confidence !== undefined ? (confidence * 100).toFixed(0) : '?'
  }%`;
  const distanceText = distance ? ` | ${distance.toFixed(2)}m` : '';

  return resolvedLabelText + distanceText;
}

/**
 * Label position result
 */
export interface LabelPosition {
  x: number;
  y: number;
}

/**
 * Calculate the position for a label relative to its bounding box
 *
 * @param bboxX - X coordinate of the bounding box
 * @param bboxY - Y coordinate of the bounding box
 * @param bboxHeight - Height of the bounding box
 * @param textHeight - Height of the label text
 * @param padding - Padding around the label
 * @param labelWidth - Width of the label (including padding)
 * @param canvasWidth - Width of the canvas
 * @param canvasHeight - Height of the canvas
 * @returns The calculated label position
 */
export function calculateLabelPosition(
  bboxX: number,
  bboxY: number,
  bboxHeight: number,
  textHeight: number,
  padding: number,
  labelWidth: number,
  canvasWidth: number,
  canvasHeight: number
): LabelPosition {
  // Position label above the box if there's room, otherwise below
  const labelY =
    bboxY > textHeight + padding
      ? bboxY - 4
      : Math.min(canvasHeight - 2, bboxY + bboxHeight + textHeight + 4);

  // Clamp X position to keep label within canvas
  const labelX = clamp(bboxX, 0, canvasWidth - labelWidth);

  return { x: labelX, y: labelY };
}

/**
 * Metadata frame for timestamp matching
 */
export interface MetadataFrame {
  timestamp: number;
  frameId: number;
}

/**
 * Result of finding best metadata match
 */
export interface MetadataMatchResult {
  index: number;
  delta: number;
}

/**
 * Find the best matching metadata frame for a given media time
 *
 * @param buffer - Array of metadata frames with timestamps
 * @param mediaTimeMs - Current media playback time in milliseconds
 * @param timeOffset - Time offset between frame timestamps and media time (or null if not yet established)
 * @returns The best match result, or null if no match within tolerance
 */
export function findBestMetadataMatch(
  buffer: MetadataFrame[],
  mediaTimeMs: number,
  timeOffset: number | null
): MetadataMatchResult | null {
  if (!buffer.length) return null;

  // Calculate effective time offset
  const effectiveOffset = timeOffset ?? buffer[0].timestamp - mediaTimeMs;

  let bestIndex = -1;
  let bestDelta = Number.POSITIVE_INFINITY;

  buffer.forEach((frame, idx) => {
    const adjustedTimestamp = frame.timestamp - effectiveOffset;
    const delta = Math.abs(adjustedTimestamp - mediaTimeMs);
    if (delta < bestDelta) {
      bestDelta = delta;
      bestIndex = idx;
    }
  });

  // Only accept if within tolerance window
  if (bestIndex === -1 || bestDelta > METADATA_TOLERANCE_MS) {
    return null;
  }

  return { index: bestIndex, delta: bestDelta };
}

/**
 * Calculate the initial time offset for metadata synchronization
 *
 * @param firstFrameTimestamp - Timestamp of the first metadata frame
 * @param mediaTimeMs - Current media playback time in milliseconds
 * @returns The calculated time offset
 */
export function calculateTimeOffset(
  firstFrameTimestamp: number,
  mediaTimeMs: number
): number {
  return firstFrameTimestamp - mediaTimeMs;
}

/**
 * Normalize a metadata timestamp to be relative to media playback time
 *
 * @param frameTimestamp - The frame's timestamp
 * @param timeOffset - The calculated time offset
 * @returns The normalized timestamp
 */
export function normalizeTimestamp(
  frameTimestamp: number,
  timeOffset: number
): number {
  return frameTimestamp - timeOffset;
}

/**
 * Check if a held frame is still valid (within hold window)
 *
 * @param currentTimeMs - Current media time in milliseconds
 * @param lastRenderedTimeMs - Time when the frame was last rendered
 * @param holdMs - How long to hold the frame (default: HOLD_LAST_MS)
 * @returns True if the frame is still valid
 */
export function isHeldFrameValid(
  currentTimeMs: number,
  lastRenderedTimeMs: number,
  holdMs: number = HOLD_LAST_MS
): boolean {
  const age = currentTimeMs - lastRenderedTimeMs;
  return age >= 0 && age <= holdMs;
}

/**
 * Sanitize a metadata timestamp, returning current time if invalid
 *
 * @param timestamp - The timestamp to sanitize
 * @param fallback - Fallback value if timestamp is invalid (default: Date.now())
 * @returns A valid timestamp
 */
export function sanitizeTimestamp(
  timestamp: number | undefined | null,
  fallback: number = Date.now()
): number {
  if (typeof timestamp === 'number' && !Number.isNaN(timestamp)) {
    return timestamp;
  }
  return fallback;
}

/**
 * Check if canvas layout has changed significantly
 *
 * @param current - Current layout dimensions
 * @param previous - Previous layout dimensions
 * @param threshold - Change threshold in pixels (default: 0.5)
 * @returns Object indicating if size and/or position changed
 */
export function hasLayoutChanged(
  current: {
    width: number;
    height: number;
    top: number;
    left: number;
    dpr: number;
  },
  previous: {
    width: number;
    height: number;
    top: number;
    left: number;
    dpr: number;
  },
  threshold: number = 0.5
): { sizeChanged: boolean; positionChanged: boolean } {
  const sizeChanged =
    Math.abs(current.width - previous.width) > threshold ||
    Math.abs(current.height - previous.height) > threshold ||
    current.dpr !== previous.dpr;

  const positionChanged =
    Math.abs(current.top - previous.top) > threshold ||
    Math.abs(current.left - previous.left) > threshold;

  return { sizeChanged, positionChanged };
}
