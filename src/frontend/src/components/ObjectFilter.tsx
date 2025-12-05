/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useState, useMemo, useCallback, memo } from 'react';
import { getCocoLabel } from '../constants/cocoLabels';
import { BoundingBox } from './video/VideoOverlay';

export interface ObjectFilterProps {
  /** Current detections from the latest frame */
  detections: BoundingBox[];
  /** Currently selected class IDs */
  selectedClasses: Set<number>;
  /** Callback when selection changes */
  onSelectionChange: (selectedClasses: Set<number>) => void;
  /** Whether the widget is currently open */
  isOpen: boolean;
  /** Callback to toggle widget visibility */
  onToggle: () => void;
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
  }: {
    classInfo: DetectedClass;
    isSelected: boolean;
    onToggle: (classId: number) => void;
  }) => {
    return (
      <label
        className="flex items-center justify-between p-2 hover:bg-[#333] rounded cursor-pointer transition-colors"
        onClick={(e) => {
          e.preventDefault();
          onToggle(classInfo.classId);
        }}
      >
        <div className="flex items-center gap-2 flex-1">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => {}} // Handled by label onClick
            className="w-4 h-4 accent-[#00d4ff] cursor-pointer"
          />
          <span className="text-sm text-[#e0e0e0]">{classInfo.label}</span>
        </div>
        <span className="text-xs text-[#888] bg-[#404040] px-2 py-0.5 rounded">
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
  isOpen,
  onToggle,
}: ObjectFilterProps) {
  // Track all classes ever seen in the session with their first-seen timestamp
  const [seenClasses, setSeenClasses] = useState<Map<number, number>>(
    new Map()
  );

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

        // Track when this class was first seen and auto-select it
        setSeenClasses((prev) => {
          if (!prev.has(classId)) {
            const updated = new Map(prev);
            updated.set(classId, Date.now());

            // Auto-select newly detected classes (default: select all)
            onSelectionChange(new Set([...selectedClasses, classId]));

            return updated;
          }
          return prev;
        });
      }
    });

    return classMap;
  }, [detections, selectedClasses, onSelectionChange]);

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
  }, [onSelectionChange]);

  const hasDetections = detectedClasses.length > 0;
  const allSelected =
    hasDetections && selectedClasses.size === detectedClasses.length;
  const noneSelected = selectedClasses.size === 0;

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={onToggle}
        className="fixed left-5 top-[80px] z-50 bg-[#404040] hover:bg-[#505050] text-[#00d4ff] rounded-lg p-2 transition-colors border border-[#555] shadow-lg"
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
          <div className="bg-[#2a2a2a] border border-[#404040] p-4 rounded-lg shadow-[0_4px_20px_rgba(0,0,0,0.4)]">
            {/* Header */}
            <div className="mb-3">
              <h3 className="my-0 text-[#00d4ff] text-lg font-semibold">
                Object Filter
              </h3>
              <p className="text-[#888] text-xs mt-1">
                {noneSelected
                  ? 'No objects visible'
                  : `${selectedClasses.size} class${selectedClasses.size !== 1 ? 'es' : ''} selected`}
              </p>
            </div>

            {/* Action buttons */}
            {hasDetections && (
              <div className="flex gap-2 mb-3">
                <button
                  onClick={handleSelectAll}
                  disabled={allSelected}
                  className="flex-1 text-xs px-2 py-1.5 bg-[#404040] hover:bg-[#505050] disabled:bg-[#333] disabled:text-[#666] text-[#00d4ff] rounded border border-[#555] transition-colors"
                >
                  Select All
                </button>
                <button
                  onClick={handleClearAll}
                  disabled={noneSelected}
                  className="flex-1 text-xs px-2 py-1.5 bg-[#404040] hover:bg-[#505050] disabled:bg-[#333] disabled:text-[#666] text-[#00d4ff] rounded border border-[#555] transition-colors"
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
                  />
                ))}
              </div>
            ) : (
              <p className="text-[#888] text-sm italic text-center py-4">
                No objects detected yet
              </p>
            )}

            {/* Info text */}
            {hasDetections && (
              <div className="mt-3 pt-3 border-t border-[#404040]">
                <p className="text-[#666] text-xs">
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
