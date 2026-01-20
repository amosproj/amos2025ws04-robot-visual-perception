/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useMemo, useCallback } from 'react';
import type { BoundingBox } from './video/VideoOverlay';
import { useI18n } from '../i18n';
import { getCocoLabel } from '../constants/cocoLabels';

export interface RadarViewProps {
  detections: BoundingBox[];
  maxRangeMeters?: number;
  maxLateralMeters?: number;
}

const clampValue = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

const getDistanceValue = (detection: BoundingBox) => {
  if (
    typeof detection.distance === 'number' &&
    Number.isFinite(detection.distance)
  ) {
    return detection.distance;
  }
  if (
    detection.position &&
    typeof detection.position.z === 'number' &&
    Number.isFinite(detection.position.z)
  ) {
    return detection.position.z;
  }
  return null;
};

const getRangeColor = (distance: number, maxRange: number) => {
  const ratio = distance / maxRange;
  if (ratio <= 0.33) return 'bg-theme-error';
  if (ratio <= 0.66) return 'bg-theme-warning';
  return 'bg-theme-success';
};

export default function RadarView({
  detections,
  maxRangeMeters = 8,
  maxLateralMeters = 4.5,
}: RadarViewProps) {
  const { t, language } = useI18n();
  const unknownLabel = useCallback(
    (value: string | number) => t('labelUnknown', { id: value }),
    [t]
  );
  const resolveLabel = useCallback(
    (detection: BoundingBox) => {
      if (detection.labelText && detection.labelText.trim().length > 0) {
        return detection.labelText;
      }
      return getCocoLabel(detection.label, language, { unknownLabel });
    },
    [language, unknownLabel]
  );

  const radarPoints = useMemo(() => {
    const range = Math.max(1, maxRangeMeters);
    const lateral = Math.max(0.5, maxLateralMeters);
    const marginPct = 6;

    return detections
      .map((detection) => {
        const distance = getDistanceValue(detection);
        if (distance == null || distance <= 0) return null;

        const rawX =
          typeof detection.position?.x === 'number' &&
          Number.isFinite(detection.position.x)
            ? detection.position.x
            : 0;
        const rawZ =
          typeof detection.position?.z === 'number' &&
          Number.isFinite(detection.position.z)
            ? detection.position.z
            : distance;

        const clampedX = clampValue(rawX, -lateral, lateral);
        const clampedZ = clampValue(rawZ, 0, range);
        const xPercent = 50 + (clampedX / lateral) * (50 - marginPct);
        const yPercent = marginPct + (clampedZ / range) * (100 - marginPct * 2);
        const isOutOfRange = rawZ > range || Math.abs(rawX) > lateral;

        return {
          id: detection.id,
          xPercent,
          yPercent,
          distance,
          label: resolveLabel(detection),
          colorClass: getRangeColor(distance, range),
          interpolated: detection.interpolated,
          outOfRange: isOutOfRange,
        };
      })
      .filter((point): point is NonNullable<typeof point> => Boolean(point));
  }, [detections, maxRangeMeters, maxLateralMeters, resolveLabel]);

  const ringSteps = useMemo(() => [0.25, 0.5, 0.75, 1], []);
  const objectCount = radarPoints.length;

  return (
    <div className="bg-theme-bg-secondary/95 backdrop-blur-sm border border-theme-border-subtle rounded-lg shadow-xl p-4 sm:p-5 md:p-6 w-[calc(100vw-2rem)] max-w-[34rem]">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="my-0 text-theme-accent text-base sm:text-lg md:text-xl font-semibold">
            {t('radarTitle')}
          </h3>
          <p className="my-1 text-xs text-theme-text-muted">
            {objectCount} {t('objectsLabel')}
          </p>
        </div>
        <span className="text-xs text-theme-text-muted font-mono">
          {maxRangeMeters.toFixed(1)}m
        </span>
      </div>

      <div
        className="relative mt-4 h-64 sm:h-72 md:h-80 lg:h-96 overflow-hidden rounded-b-[4rem] border border-theme-border-subtle bg-theme-bg-tertiary/70"
        style={{
          backgroundImage:
            'radial-gradient(circle at 50% 100%, rgba(116,185,255,0.18) 0%, rgba(45,52,54,0.05) 55%, rgba(45,52,54,0) 75%)',
        }}
      >
        {ringSteps.map((ratio) => (
          <div
            key={`ring-${ratio}`}
            className="absolute left-1/2 bottom-0 border border-theme-border-subtle rounded-full"
            style={{
              width: `${ratio * 100}%`,
              height: `${ratio * 100}%`,
              transform: 'translateX(-50%)',
            }}
          />
        ))}

        {ringSteps.map((ratio) => (
          <span
            key={`label-${ratio}`}
            className="absolute right-2 text-[10px] text-theme-text-muted font-mono"
            style={{ bottom: `${ratio * 100}%` }}
          >
            {(ratio * maxRangeMeters).toFixed(1)}m
          </span>
        ))}

        <div className="absolute bottom-0 left-0 right-0 h-px bg-theme-border-subtle/70" />
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-px h-full bg-theme-border-subtle/40" />

        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-10 h-4 rounded bg-theme-accent/70 border border-theme-border-subtle shadow-[0_0_10px_rgba(116,185,255,0.4)]" />

        {radarPoints.map((point) => (
          <div
            key={point.id}
            className={`absolute w-3 h-3 rounded-full border border-white/70 shadow-[0_0_8px_rgba(0,0,0,0.35)] ${point.colorClass} ${
              point.interpolated ? 'opacity-70' : ''
            } ${point.outOfRange ? 'ring-2 ring-white/40' : ''}`}
            style={{
              left: `${point.xPercent}%`,
              bottom: `${point.yPercent}%`,
              transform: 'translate(-50%, 50%)',
            }}
            title={`${point.label} - ${point.distance.toFixed(2)}m`}
          />
        ))}

        {objectCount === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-theme-text-muted">
            {t('metadataNoObjectsDetected')}
          </div>
        )}
      </div>
    </div>
  );
}
