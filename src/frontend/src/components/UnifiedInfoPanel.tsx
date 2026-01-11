/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import DetectionInfo from './DetectionInfo';
import StreamInfo, { type StreamInfoProps } from './StreamInfo';
import { ObjectFilterSection } from './ObjectFilter';
import { ConnectionButtonGroup } from './ConnectionControls';
import type { BoundingBox, MetadataFrame } from './video/VideoOverlay';
import { useI18n } from '../i18n';

export interface UnifiedInfoPanelProps {
  videoState: string;
  analyzerConnected: boolean;
  onConnectVideo: () => void;
  onDisconnectVideo: () => void;
  onConnectAnalyzer: () => void;
  onDisconnectAnalyzer: () => void;
  onClearOverlay: () => void;
  detections: BoundingBox[];
  selectedClasses: Set<number>;
  onSelectionChange: (selectedClasses: Set<number>) => void;
  confidenceThreshold: number;
  onConfidenceThresholdChange: (threshold: number) => void;
  isVideoConnected: boolean;
  streamMetadata?: StreamInfoProps;
  detectionMetadata?: MetadataFrame | null;
  onClearAll?: () => void;
}

function UnifiedInfoPanel({
  videoState,
  analyzerConnected,
  onConnectVideo,
  onDisconnectVideo,
  onConnectAnalyzer,
  onDisconnectAnalyzer,
  onClearOverlay,
  detections,
  selectedClasses,
  onSelectionChange,
  confidenceThreshold,
  onConfidenceThresholdChange,
  isVideoConnected,
  streamMetadata,
  detectionMetadata,
  onClearAll,
}: UnifiedInfoPanelProps) {
  const { t } = useI18n();
  const detectionCount = detectionMetadata?.detections.length ?? 0;
  const hasDetections = detectionCount > 0;
  const showDetections = analyzerConnected || detectionMetadata != null;

  return (
    <div className="w-full max-w-[340px] lg:max-w-none">
      <div className="bg-theme-bg-secondary border border-theme-border-subtle p-4 rounded-lg shadow-card space-y-4">
        <div className="pb-3 border-b border-theme-border-subtle">
          <ConnectionButtonGroup
            videoState={videoState}
            analyzerConnected={analyzerConnected}
            onConnectVideo={onConnectVideo}
            onDisconnectVideo={onDisconnectVideo}
            onConnectAnalyzer={onConnectAnalyzer}
            onDisconnectAnalyzer={onDisconnectAnalyzer}
            onClearOverlay={onClearOverlay}
            variant="panel"
          />
        </div>

        <ObjectFilterSection
          detections={detections}
          selectedClasses={selectedClasses}
          onSelectionChange={onSelectionChange}
          confidenceThreshold={confidenceThreshold}
          onConfidenceThresholdChange={onConfidenceThresholdChange}
          isAnalyzerConnected={analyzerConnected}
          isVideoConnected={isVideoConnected}
          onClearAll={onClearAll}
          variant="section"
        />

        <div className="border-t border-theme-border-subtle pt-4">
          <StreamInfo {...(streamMetadata ?? {})} variant="section" />
        </div>

        {showDetections && (
          <div className="border-t border-theme-border-subtle pt-4">
            {hasDetections ? (
              <DetectionInfo
                detections={detectionMetadata?.detections ?? []}
                showGrouped={false}
                variant="section"
              />
            ) : (
              <div>
                <h3 className="my-0 mb-3 text-theme-accent text-lg font-semibold">
                  {t('detectionsTitleLatest', { count: detectionCount })}
                </h3>
                <p className="text-theme-text-muted text-sm italic text-center py-3">
                  {t('metadataNoObjectsDetected')}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default UnifiedInfoPanel;
