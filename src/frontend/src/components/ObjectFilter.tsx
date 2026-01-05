/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useState, useMemo, useCallback, memo, useEffect } from 'react';
import { getCocoLabel } from '../constants/cocoLabels';
import { BoundingBox } from './video/VideoOverlay';

export interface ObjectFilterProps {
  /** Current detections from the latest frame */
  detections: BoundingBox[];
  /** Currently selected class IDs */
  selectedClasses: Set<number>;
  /** Callback when selection changes */
  onSelectionChange: (selectedClasses: Set<number>) => void;
  /** Current confidence threshold (0-1) */
  confidenceThreshold: number;
  /** Callback when confidence threshold changes */
  onConfidenceThresholdChange: (threshold: number) => void;
  /** Whether the widget is currently open */
  isOpen: boolean;
  /** Callback to toggle widget visibility */
  onToggle: () => void;
  /** Whether the analyzer is currently connected */
  isAnalyzerConnected: boolean;
  /** Whether the video is currently connected */
  isVideoConnected: boolean;
  /** Callback when clear all is triggered */
  onClearAll?: () => void;
}

interface DetectedClass {
  /** COCO class ID */
  classId: number;
  /** Human-readable label */
  label: string;
  /** Number of detections in current frame */
  count: number;
  /** First seen timestamp (for stable ordering) */
  firstSeen: number;
}

/**
 * Individual checkbox item for a detected class
 * Memoized to prevent unnecessary re-renders
 */
const ClassCheckboxItem = memo(
  ({
    classInfo,
    isSelected,
    onToggle,
    disabled = false,
  }: {
    classInfo: DetectedClass;
    isSelected: boolean;
    onToggle: (classId: number) => void;
    disabled?: boolean;
  }) => {
    return (
      <label
        className={`flex items-center justify-between p-2 rounded transition-colors ${
          disabled
            ? 'opacity-50 cursor-not-allowed'
            : 'hover:bg-theme-bg-disabled cursor-pointer'
        }`}
        onClick={(e) => {
          e.preventDefault();
          if (!disabled) {
            onToggle(classInfo.classId);
          }
        }}
      >
        <div className="flex items-center gap-2 flex-1">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => {}} // Handled by label onClick
            disabled={disabled}
            className="w-4 h-4 accent-theme-accent cursor-pointer disabled:cursor-not-allowed"
          />
          <span className="text-sm text-theme-text-primary">{classInfo.label}</span>
        </div>
        <span className="text-xs text-theme-text-muted bg-theme-bg-tertiary px-2 py-0.5 rounded">
          {classInfo.count}
        </span>
      </label>
    );
  }
);

/**
 * ObjectFilter component for filtering detected objects by class
 *
 * Features:
 * - Multi-select checkbox list of detected object classes
 * - Stable ordering: new classes added at top, but not reordered after that
 * - Shows current count of each class in the frame
 * - Positioned on the left side (opposite of MetadataWidget)
 */
function ObjectFilter({
  detections,
  selectedClasses,
  onSelectionChange,
  confidenceThreshold,
  onConfidenceThresholdChange,
  isOpen,
  onToggle,
  isAnalyzerConnected,
  isVideoConnected,
  onClearAll,
}: ObjectFilterProps) {
  // Track all classes ever seen in the session with their first-seen timestamp
  const [seenClasses, setSeenClasses] = useState<Map<number, number>>(
    new Map()
  );

  // Clear seen classes when analyzer disconnects
  useEffect(() => {
    if (!isAnalyzerConnected) {
      setSeenClasses(new Map());
    }
  }, [isAnalyzerConnected]);

  // Compute current frame's class counts and update seen classes
  const currentClasses = useMemo(() => {
    const classMap = new Map<number, number>();

    detections.forEach((detection) => {
      const classId =
        typeof detection.label === 'string'
          ? parseInt(detection.label, 10)
          : detection.label;

      if (!isNaN(classId)) {
        classMap.set(classId, (classMap.get(classId) || 0) + 1);

        // Track when this class was first seen
        setSeenClasses((prev) => {
          if (!prev.has(classId)) {
            const updated = new Map(prev);
            updated.set(classId, Date.now());
            return updated;
          }
          return prev;
        });
      }
    });

    return classMap;
  }, [detections]);

  // Build stable list of detected classes (ordered by first-seen, newest at top)
  const detectedClasses = useMemo(() => {
    const classes: DetectedClass[] = [];

    seenClasses.forEach((firstSeen, classId) => {
      const count = currentClasses.get(classId) || 0;
      classes.push({
        classId,
        label: getCocoLabel(classId),
        count,
        firstSeen,
      });
    });

    // Sort by first-seen timestamp (newest first = highest timestamp first)
    return classes.sort((a, b) => b.firstSeen - a.firstSeen);
  }, [seenClasses, currentClasses]);

  const handleToggleClass = useCallback(
    (classId: number) => {
      const newSelection = new Set(selectedClasses);
      if (newSelection.has(classId)) {
        newSelection.delete(classId);
      } else {
        newSelection.add(classId);
      }
      onSelectionChange(newSelection);
    },
    [selectedClasses, onSelectionChange]
  );

  const handleSelectAll = useCallback(() => {
    const allClasses = new Set(detectedClasses.map((c) => c.classId));
    onSelectionChange(allClasses);
  }, [detectedClasses, onSelectionChange]);

  const handleClearAll = useCallback(() => {
    onSelectionChange(new Set());
    onClearAll?.();
  }, [onSelectionChange, onClearAll]);

  const handleConfidenceChange = useCallback(
    (value: number) => {
      const clamped = Math.min(1, Math.max(0, value));
      onConfidenceThresholdChange(clamped);
    },
    [onConfidenceThresholdChange]
  );

  const hasDetections = detectedClasses.length > 0;
  const allSelected =
    hasDetections && selectedClasses.size === detectedClasses.length;
  const noneSelected = selectedClasses.size === 0;

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={onToggle}
        className="fixed left-5 top-[80px] z-50 bg-theme-bg-tertiary hover:bg-theme-bg-hover text-theme-accent rounded-lg p-2 transition-colors border border-theme-border shadow-lg"
        aria-label="Toggle Object Filter"
      >
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          {isOpen ? <path d="M15 18l-6-6 6-6" /> : <path d="M9 18l6-6-6-6" />}
        </svg>
      </button>

      {/* Widget content */}
      {isOpen && (
        <div className="fixed left-5 top-[120px] w-[280px] max-h-[calc(100vh-140px)] overflow-y-auto z-50 transition-all duration-300">
          <div className="bg-theme-bg-secondary border border-theme-border-subtle p-4 rounded-lg shadow-card">
            {/* Header */}
            <div className="mb-3">
              <h3 className="my-0 text-theme-accent text-lg font-semibold">
                Object Filter
              </h3>
              <p className="text-theme-text-muted text-xs mt-1">
                {noneSelected
                  ? 'No objects visible'
                  : `${selectedClasses.size} class${selectedClasses.size !== 1 ? 'es' : ''} selected`}
              </p>
            </div>

            {/* Low confidence filter */}
            <div className="mb-4">
              <div className="flex items-center justify-between text-xs text-theme-text-primary mb-1">
                <span>Low-confidence filter</span>
                <span className="text-theme-accent font-mono">
                  {Math.round(confidenceThreshold * 100)}%+
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={confidenceThreshold}
                onChange={(e) =>
                  handleConfidenceChange(parseFloat(e.target.value))
                }
                disabled={!isVideoConnected}
                className="w-full accent-theme-accent cursor-pointer disabled:cursor-not-allowed"
              />
              <p className="text-theme-text-muted text-[11px] mt-1">
                Hide detections below this confidence to keep metadata in sync
                with trusted boxes.
              </p>
            </div>

            {/* Action buttons */}
            {hasDetections && (
              <div className="flex gap-2 mb-3">
                <button
                  onClick={handleSelectAll}
                  disabled={allSelected || !isVideoConnected}
                  className="flex-1 text-xs px-2 py-1.5 bg-theme-bg-tertiary hover:bg-theme-bg-hover disabled:bg-theme-bg-disabled disabled:text-theme-text-muted text-theme-accent rounded border border-theme-border transition-colors"
                >
                  Select All
                </button>
                <button
                  onClick={handleClearAll}
                  disabled={noneSelected || !isVideoConnected}
                  className="flex-1 text-xs px-2 py-1.5 bg-theme-bg-tertiary hover:bg-theme-bg-hover disabled:bg-theme-bg-disabled disabled:text-theme-text-muted text-theme-accent rounded border border-theme-border transition-colors"
                >
                  Clear All
                </button>
              </div>
            )}

            {/* Class list */}
            {hasDetections ? (
              <div className="space-y-1 max-h-[calc(100vh-300px)] overflow-y-auto">
                {detectedClasses.map((classInfo) => (
                  <ClassCheckboxItem
                    key={classInfo.classId}
                    classInfo={classInfo}
                    isSelected={selectedClasses.has(classInfo.classId)}
                    onToggle={handleToggleClass}
                    disabled={!isVideoConnected}
                  />
                ))}
              </div>
            ) : (
              <p className="text-theme-text-muted text-sm italic text-center py-4">
                No objects detected yet
              </p>
            )}

            {/* Info text */}
            {hasDetections && (
              <div className="mt-3 pt-3 border-t border-theme-border-subtle">
                <p className="text-theme-text-muted text-xs">
                  {noneSelected
                    ? 'Select classes to show bounding boxes'
                    : 'Only selected classes are visible'}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

export default ObjectFilter;
