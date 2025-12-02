/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useMemo, memo } from 'react';
import { getCocoLabel } from '../constants/cocoLabels';

export interface Detection {
  id: string;
  label: string;
  confidence: number;
  distance?: number;
}

export interface DetectionInfoProps {
  detections: Detection[];
  showGrouped?: boolean;
}

interface GroupedDetection {
  label: string;
  count: number;
  minConfidence: number;
  maxConfidence: number;
  minDistance?: number;
  maxDistance?: number;
}

function DetectionInfo({
  detections,
  showGrouped = false,
}: DetectionInfoProps) {
  if (!detections || detections.length === 0) {
    return null;
  }

  // Sort detections by distance (closest first)
  const sortedDetections = useMemo(() => {
    return [...detections].sort((a, b) => {
      // If both have distance, sort by distance
      if (a.distance !== undefined && b.distance !== undefined) {
        return a.distance - b.distance;
      }
      // If only one has distance, put it first
      if (a.distance !== undefined) return -1;
      if (b.distance !== undefined) return 1;
      // Otherwise maintain order
      return 0;
    });
  }, [detections]);

  // Group detections by label
  const groupedDetections = useMemo(() => {
    const groups = new Map<string, GroupedDetection>();

    sortedDetections.forEach((det) => {
      const labelName = getCocoLabel(det.label);
      const existing = groups.get(labelName);

      if (existing) {
        existing.count++;
        existing.minConfidence = Math.min(
          existing.minConfidence,
          det.confidence
        );
        existing.maxConfidence = Math.max(
          existing.maxConfidence,
          det.confidence
        );

        if (det.distance !== undefined) {
          existing.minDistance =
            existing.minDistance !== undefined
              ? Math.min(existing.minDistance, det.distance)
              : det.distance;
          existing.maxDistance =
            existing.maxDistance !== undefined
              ? Math.max(existing.maxDistance, det.distance)
              : det.distance;
        }
      } else {
        groups.set(labelName, {
          label: labelName,
          count: 1,
          minConfidence: det.confidence,
          maxConfidence: det.confidence,
          minDistance: det.distance,
          maxDistance: det.distance,
        });
      }
    });

    return Array.from(groups.values());
  }, [sortedDetections]);

  if (showGrouped) {
    return (
      <div className="bg-[#2a2a2a] border border-[#404040] p-5 rounded-lg shadow-[0_4px_20px_rgba(0,0,0,0.4)]">
        <h3 className="my-0 mb-4 text-[#00d4ff] text-xl">
          Detections ({detections.length} objects)
        </h3>
        <div className="max-h-96 overflow-y-auto space-y-2">
          {groupedDetections.map((group) => (
            <GroupedDetectionCard key={group.label} group={group} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#2a2a2a] border border-[#404040] p-5 rounded-lg shadow-[0_4px_20px_rgba(0,0,0,0.4)]">
      <h3 className="my-0 mb-4 text-[#00d4ff] text-xl">
        Latest Detections ({detections.length})
      </h3>
      <div className="max-h-96 overflow-y-auto">
        <div className="flex flex-wrap gap-2.5">
          {sortedDetections.map((detection) => (
            <DetectionCard key={detection.id} detection={detection} />
          ))}
        </div>
      </div>
    </div>
  );
}

// Memoized detection card component
const DetectionCard = memo(({ detection }: { detection: Detection }) => {
  const labelName = getCocoLabel(detection.label);

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-[#404040] rounded-md border-l-[3px] border-l-[#00d4ff] border border-[#555]">
      <span className="font-semibold text-[#e0e0e0]">{labelName}</span>
      <span className="bg-gradient-to-br from-[#74b9ff] to-[#0984e3] text-white px-2 py-0.5 rounded text-xs font-semibold shadow-[0_2px_4px_rgba(116,185,255,0.3)]">
        {(detection.confidence * 100).toFixed(1)}%
      </span>
      {detection.distance !== undefined && (
        <span className="bg-gradient-to-br from-[#00d4aa] to-[#00b894] text-white px-2 py-0.5 rounded text-xs font-semibold shadow-[0_2px_4px_rgba(0,212,170,0.3)]">
          {detection.distance.toFixed(2)}m
        </span>
      )}
    </div>
  );
});

DetectionCard.displayName = 'DetectionCard';

// Memoized grouped detection card component
const GroupedDetectionCard = memo(({ group }: { group: GroupedDetection }) => {
  return (
    <div className="flex items-center justify-between px-4 py-3 bg-[#404040] rounded-md border-l-[3px] border-l-[#00d4ff] border border-[#555]">
      <div className="flex items-center gap-3">
        <span className="font-semibold text-[#e0e0e0] text-lg">
          {group.count}× {group.label}
        </span>
        <span className="text-[#888] text-xs">
          {group.minConfidence === group.maxConfidence
            ? `${(group.minConfidence * 100).toFixed(1)}%`
            : `${(group.minConfidence * 100).toFixed(1)}%-${(group.maxConfidence * 100).toFixed(1)}%`}
        </span>
      </div>
      {group.minDistance !== undefined && (
        <span className="bg-gradient-to-br from-[#00d4aa] to-[#00b894] text-white px-3 py-1 rounded text-sm font-semibold shadow-[0_2px_4px_rgba(0,212,170,0.3)]">
          {group.minDistance === group.maxDistance
            ? `${group.minDistance.toFixed(2)}m`
            : `${group.minDistance.toFixed(2)}-${group.maxDistance!.toFixed(2)}m`}
        </span>
      )}
    </div>
  );
});

GroupedDetectionCard.displayName = 'GroupedDetectionCard';

export default memo(DetectionInfo);
