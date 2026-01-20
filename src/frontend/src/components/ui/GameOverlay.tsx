/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { ReactNode } from 'react';
import { TabbedWidgetPanel, Tab } from './TabbedWidgetPanel';
import { useI18n } from '../../i18n';

export interface GameOverlayProps {
  /** Main content (video player) */
  children: ReactNode;

  /** Panel state */
  showPanel?: boolean;

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
  showPanel = true,
  filterPanel,
  streamInfoPanel,
  statusPanel,
  detectionPanel,
}: GameOverlayProps) {
  const { t } = useI18n();

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

      {/* Left side - Tabbed widget panel */}
      {showPanel && (
        <div className="fixed left-2 right-2 top-[calc(var(--ui-header-height)+0.75rem)] z-40 sm:left-4 sm:right-auto sm:w-[28rem] md:w-[34rem] lg:w-[42rem]">
          <TabbedWidgetPanel tabs={tabs} defaultTab="filter" />
        </div>
      )}

      {/* Right side - Status panel */}
      {statusPanel && (
        <div className="fixed left-2 right-2 top-[calc(var(--ui-header-height)+0.75rem)] z-40 sm:left-auto sm:right-4 sm:w-72">
          <div className="bg-theme-bg-secondary/95 backdrop-blur-sm border border-theme-border-subtle rounded-lg shadow-xl p-4">
            {statusPanel}
          </div>
        </div>
      )}
    </div>
  );
}

export default GameOverlay;
