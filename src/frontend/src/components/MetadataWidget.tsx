/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useState } from 'react';
import { MetadataFrame } from './video/VideoOverlay';
import DetectionInfo from './DetectionInfo';
import StreamInfo, { type StreamInfoProps } from './StreamInfo';
import { useI18n } from '../i18n';

export interface MetadataWidgetProps {
  /** Detection metadata from AI backend */
  detectionMetadata?: MetadataFrame | null;
  /** Stream-related metadata (resolution, network quality, etc.) */
  streamMetadata?: StreamInfoProps;
  /** Optional: Start with grouped view */
  defaultGrouped?: boolean;
  /** Whether the widget is currently open */
  isOpen: boolean;
  /** Callback to toggle widget visibility */
  onToggle: () => void;
}

/**
 * MetadataWidget orchestrates DetectionInfo and StreamInfo components
 *
 * Displays:
 * - Stream Info: Network quality, video quality metrics
 * - Detection Info: Object detections with grouping option
 * - Toggle button for showing/hiding the widget
 */
function MetadataWidget({
  detectionMetadata,
  streamMetadata,
  defaultGrouped = false,
  isOpen,
  onToggle,
}: MetadataWidgetProps) {
  const [showGrouped, setShowGrouped] = useState(defaultGrouped);
  const { t } = useI18n();

  const hasDetections =
    detectionMetadata && detectionMetadata.detections.length > 0;

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={onToggle}
        className="fixed right-5 top-[80px] z-50 bg-theme-bg-tertiary hover:bg-theme-bg-hover text-theme-accent rounded-lg p-2 transition-colors border border-theme-border shadow-lg"
        aria-label={t('metadataToggle')}
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
          {isOpen ? <path d="M9 18l6-6-6-6" /> : <path d="M15 18l-6-6 6-6" />}
        </svg>
      </button>

      {/* Widget content */}
      {isOpen && (
        <div className="fixed right-5 top-[120px] w-[320px] max-h-[calc(100vh-140px)] overflow-y-auto z-50 transition-all duration-300">
          <div className="space-y-4">
            {/* Stream Info Section */}
            {streamMetadata && <StreamInfo {...streamMetadata} />}

            {/* Detection Info Section */}
            {hasDetections && (
              <div>
                {/* Toggle button for grouped/detail view */}
                <div className="mb-3 flex justify-end">
                  <button
                    onClick={() => setShowGrouped(!showGrouped)}
                    className="text-xs px-3 py-1.5 bg-theme-bg-tertiary hover:bg-theme-bg-hover text-theme-accent rounded border border-theme-border transition-colors"
                  >
                    {showGrouped
                      ? t('metadataShowDetails')
                      : t('metadataGroupByType')}
                  </button>
                </div>

                <DetectionInfo
                  detections={detectionMetadata.detections}
                  showGrouped={showGrouped}
                />
              </div>
            )}

            {/* No detections message */}
            {!hasDetections && detectionMetadata && (
              <div className="bg-theme-bg-secondary border border-theme-border-subtle p-5 rounded-lg shadow-card">
                <p className="text-theme-text-muted text-sm italic text-center">
                  {t('metadataNoObjectsDetected')}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

export default MetadataWidget;
