/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { ReactNode, useState } from 'react';
import { IconButton } from './IconButton';
import { TabbedWidgetPanel, Tab } from './TabbedWidgetPanel';
import { Video, VideoOff, Activity, Filter, Maximize } from '../video/Icons';
import { useI18n } from '../../i18n';

export interface GameOverlayProps {
  /** Main content (video player) */
  children: ReactNode;
  /** Video connection state */
  videoState: string;
  /** Whether analyzer is connected */
  analyzerConnected: boolean;
  /** Video connection handlers */
  onConnectVideo: () => void;
  onDisconnectVideo: () => void;
  /** Analyzer connection handlers */
  onConnectAnalyzer: () => void;
  onDisconnectAnalyzer: () => void;
  /** Fullscreen handler */
  onFullscreen: () => void;
  /** Object filter panel content */
  filterPanel: ReactNode;
  /** Stream info panel content */
  streamInfoPanel: ReactNode;
  /** Status panel content (Video, Latency, FPS, Objects) */
  statusPanel?: ReactNode;
  /** Detection info panel content */
  detectionPanel?: ReactNode;
}

export function GameOverlay({
  children,
  videoState,
  analyzerConnected,
  onConnectVideo,
  onDisconnectVideo,
  onConnectAnalyzer,
  onDisconnectAnalyzer,
  onFullscreen,
  filterPanel,
  streamInfoPanel,
  statusPanel,
  detectionPanel,
}: GameOverlayProps) {
  const { t } = useI18n();
  const [showPanel, setShowPanel] = useState(true);

  const isVideoConnected = videoState === 'connected';
  const isVideoConnecting = videoState === 'connecting';

  // Tabs for the widget panel
  const tabs: Tab[] = [
    {
      id: 'filter',
      label: t('objectFilterTitle'),
      content: filterPanel,
    },
    {
      id: 'streamInfo',
      label: t('streamInfoTitle'),
      content: streamInfoPanel,
    },
  ];

  // Add detection tab if provided
  if (detectionPanel) {
    tabs.push({
      id: 'detections',
      label: 'Detections',
      content: detectionPanel,
    });
  }

  return (
    <div className="relative w-full h-full min-h-screen bg-theme-bg-primary">
      {/* Main content area (video) */}
      <div className="w-full h-full">{children}</div>

      {/* Left side - Toggle button for tabbed panel */}
      <div className="fixed left-4 top-20 z-50">
        <IconButton
          icon={<Filter size={20} />}
          tooltip={showPanel ? 'Hide Panel' : 'Show Panel'}
          onClick={() => setShowPanel(!showPanel)}
          active={showPanel}
          variant={showPanel ? 'success' : 'default'}
          tooltipPosition="right"
        />
      </div>

      {/* Left side - Tabbed widget panel */}
      {showPanel && (
        <div className="fixed left-4 top-32 z-40 w-72">
          <TabbedWidgetPanel tabs={tabs} defaultTab="filter" />
        </div>
      )}

      {/* Bottom left toolbar - Vertical stack */}
      <div className="fixed left-4 bottom-4 z-50 flex flex-col gap-2">
        {/* Video connection button */}
        <IconButton
          icon={isVideoConnected ? <Video size={20} /> : <VideoOff size={20} />}
          tooltip={
            isVideoConnecting
              ? t('connectionConnecting')
              : isVideoConnected
                ? t('connectionDisconnectVideo')
                : t('connectionConnectVideo')
          }
          onClick={isVideoConnected ? onDisconnectVideo : onConnectVideo}
          disabled={isVideoConnecting}
          variant={
            isVideoConnecting
              ? 'warning'
              : isVideoConnected
                ? 'success'
                : 'default'
          }
          tooltipPosition="right"
        />

        {/* Analyzer connection button */}
        <IconButton
          icon={<Activity size={20} />}
          tooltip={
            analyzerConnected
              ? t('connectionDisconnectAnalyzer')
              : t('connectionConnectAnalyzer')
          }
          onClick={analyzerConnected ? onDisconnectAnalyzer : onConnectAnalyzer}
          variant={analyzerConnected ? 'success' : 'default'}
          tooltipPosition="right"
        />
      </div>

      {/* Right side - Status panel */}
      {statusPanel && (
        <div className="fixed right-4 top-20 z-40 w-56">
          <div className="bg-theme-bg-secondary/95 backdrop-blur-sm border border-theme-border-subtle rounded-lg shadow-xl p-3">
            {statusPanel}
          </div>
        </div>
      )}

      {/* Bottom right - Fullscreen button only */}
      <div className="fixed right-4 bottom-4 z-50">
        <IconButton
          icon={<Maximize size={20} />}
          tooltip="Fullscreen"
          onClick={onFullscreen}
          tooltipPosition="left"
        />
      </div>
    </div>
  );
}

export default GameOverlay;
