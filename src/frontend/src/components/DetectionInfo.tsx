/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useMemo, memo, useRef, useCallback } from 'react';
import { getCocoLabel } from '../constants/cocoLabels';
import { useI18n } from '../i18n';

export interface Detection {
  id: string;
  label: string | number;
  labelText?: string;
  confidence: number;
  distance?: number;
  position: Position;
}

export interface Position {
  x: number;
  y: number;
  z: number;
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
  const { t, language } = useI18n();
  const resolveLabel = useCallback(
    (det: Detection) => {
      if (det.labelText && det.labelText.trim().length > 0) {
        return det.labelText;
      }

      return getCocoLabel(det.label, language, {
        unknownLabel: (id) => t('labelUnknown', { id }),
      });
    },
    [language, t]
  );
  // Track the order in which labels were first seen for stable sorting
  const firstSeenOrderRef = useRef<Map<string, number>>(new Map());
  const nextOrderRef = useRef<number>(0);

  // Update first-seen order for new labels
  useMemo(() => {
    const currentLabels = new Set(detections.map((d) => resolveLabel(d)));

    // Add new labels with next available order
    currentLabels.forEach((label) => {
      if (!firstSeenOrderRef.current.has(label)) {
        firstSeenOrderRef.current.set(label, nextOrderRef.current++);
      }
    });

    // Clean up labels that are no longer present
    const labelsToRemove: string[] = [];
    firstSeenOrderRef.current.forEach((_, label) => {
      if (!currentLabels.has(label)) {
        labelsToRemove.push(label);
      }
    });
    labelsToRemove.forEach((label) => {
      firstSeenOrderRef.current.delete(label);
    });
  }, [detections, resolveLabel]);

  if (!detections || detections.length === 0) {
    return null;
  }

  // Sort detections by first-seen order (stable sorting)
  const sortedDetections = useMemo(() => {
    return [...detections].sort((a, b) => {
      const labelA = resolveLabel(a);
      const labelB = resolveLabel(b);

      const orderA =
        firstSeenOrderRef.current.get(labelA) ?? Number.MAX_SAFE_INTEGER;
      const orderB =
        firstSeenOrderRef.current.get(labelB) ?? Number.MAX_SAFE_INTEGER;

      return orderA - orderB;
    });
  }, [detections, resolveLabel]);

  // Group detections by label
  const groupedDetections = useMemo(() => {
    const groups = new Map<string, GroupedDetection>();

    sortedDetections.forEach((det) => {
      const labelName = resolveLabel(det);
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
  }, [sortedDetections, resolveLabel]);

  if (showGrouped) {
    return (
      <div className="bg-theme-bg-secondary border border-theme-border-subtle p-5 rounded-lg shadow-card">
        <h3 className="my-0 mb-4 text-theme-accent text-xl">
          {t('detectionsTitleGrouped', { count: detections.length })}
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
    <div className="bg-theme-bg-secondary border border-theme-border-subtle p-5 rounded-lg shadow-card">
      <h3 className="my-0 mb-4 text-theme-accent text-xl">
        {t('detectionsTitleLatest', { count: detections.length })}
      </h3>
      <div className="max-h-96 overflow-y-auto">
        <div className="flex flex-wrap gap-2.5">
          {sortedDetections.map((detection) => (
            <DetectionCard
              key={detection.id}
              detection={detection}
              resolveLabel={resolveLabel}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// Memoized detection card component
const DetectionCard = memo(
  ({
    detection,
    resolveLabel,
  }: {
    detection: Detection;
    resolveLabel: (det: Detection) => string;
  }) => {
    const labelName = resolveLabel(detection);

    return (
      <div className="flex flex-col items-center gap-2 px-3 py-2 bg-theme-bg-tertiary w-full rounded-md border-l-[3px] border-l-theme-accent border border-theme-border">
        <span className="font-semibold text-theme-text-primary">
          {labelName}
        </span>
        <span className="bg-gradient-to-br from-theme-primary to-theme-primary-secondary text-white px-2 py-0.5 rounded text-xs font-semibold font-mono shadow-[0_2px_4px_rgba(116,185,255,0.3)]">
          {(detection.confidence * 100).toFixed(1)}%
        </span>
        {detection.distance !== undefined && (
          <span className="bg-gradient-to-br from-theme-success to-theme-success-secondary text-white px-2 py-0.5 rounded text-xs font-semibold font-mono shadow-success-glow">
            {detection.distance.toFixed(2)}m
          </span>
        )}
        <span className="bg-gradient-to-br from-orange-700 to-orange-800 text-white px-2 py-0.5 rounded text-xs font-semibold font-mono shadow-[0_2px_4px_rgba(116,185,255,0.3)]">
          x={detection.position.x.toFixed(1)}m,y=
          {detection.position.y.toFixed(1)}m,z=
          {detection.position.z.toFixed(1)}m
        </span>
      </div>
    );
  }
);

DetectionCard.displayName = 'DetectionCard';

// Memoized grouped detection card component
const GroupedDetectionCard = memo(({ group }: { group: GroupedDetection }) => {
  const { t } = useI18n();

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-theme-bg-tertiary rounded-md border-l-[3px] border-l-theme-accent border border-theme-border">
      <div className="flex items-center gap-3">
        <span className="font-semibold text-theme-text-primary text-lg">
          {t('detectionsGroupedItem', {
            count: group.count,
            label: group.label,
          })}
        </span>
        <span className="text-theme-text-muted text-xs">
          {group.minConfidence === group.maxConfidence
            ? `${(group.minConfidence * 100).toFixed(1)}%`
            : `${(group.minConfidence * 100).toFixed(1)}%-${(group.maxConfidence * 100).toFixed(1)}%`}
        </span>
      </div>
      {group.minDistance !== undefined && (
        <span className="bg-gradient-to-br from-theme-success to-theme-success-secondary text-white px-3 py-1 rounded text-sm font-semibold shadow-success-glow">
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
