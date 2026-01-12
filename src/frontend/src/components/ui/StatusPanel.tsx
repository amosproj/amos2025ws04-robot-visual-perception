/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useI18n } from '../../i18n';
import type { TranslationKey } from '../../i18n/translations';

export interface StatusPanelProps {
  videoState: string;
  latencyMs?: number;
  analyzerFps: number;
  overlayFps: number;
  objectCount: number;
}

const getVideoStateBadgeClass = (state: string) => {
  if (state === 'connected') {
    return 'bg-gradient-to-br from-theme-success to-theme-success-secondary text-white text-xs px-2 py-0.5 rounded';
  }
  if (state === 'connecting') {
    return 'bg-gradient-to-br from-theme-warning to-theme-warning-secondary text-white text-xs px-2 py-0.5 rounded animate-pulse';
  }
  if (state === 'error') {
    return 'bg-gradient-to-br from-theme-error to-theme-error-secondary text-white text-xs px-2 py-0.5 rounded';
  }
  return 'bg-theme-bg-tertiary text-theme-text-muted text-xs px-2 py-0.5 rounded border border-theme-border';
};

const getFpsBadgeClass = (fps: number) => {
  if (fps > 0) {
    return 'bg-gradient-to-br from-theme-success to-theme-success-secondary text-white text-xs px-2 py-0.5 rounded';
  }
  return 'bg-theme-bg-tertiary text-theme-text-muted text-xs px-2 py-0.5 rounded border border-theme-border';
};

export function StatusPanel({
  videoState,
  latencyMs,
  analyzerFps,
  overlayFps,
  objectCount,
}: StatusPanelProps) {
  const { t } = useI18n();

  const videoStateLabels: Record<string, TranslationKey> = {
    connected: 'videoStateConnected',
    connecting: 'videoStateConnecting',
    error: 'videoStateError',
    idle: 'videoStateIdle',
  };
  const videoStateLabel = t(videoStateLabels[videoState] ?? 'videoStateIdle');

  return (
    <div className="space-y-2 text-sm">
      {/* Video Status */}
      <div className="flex items-center justify-between">
        <span className="text-theme-text-secondary">{t('videoLabel')}</span>
        <span className={getVideoStateBadgeClass(videoState)}>
          {videoStateLabel}
        </span>
      </div>

      {/* Latency */}
      {latencyMs !== undefined && latencyMs > 0 && (
        <div className="flex items-center justify-between">
          <span className="text-theme-text-secondary">Latency</span>
          <span className="text-theme-accent text-xs font-mono">
            {latencyMs}ms
          </span>
        </div>
      )}

      {/* Analyzer */}
      <div className="flex items-center justify-between">
        <span className="text-theme-text-secondary">{t('analyzerLabel')}</span>
        <span className={getFpsBadgeClass(analyzerFps)}>
          {analyzerFps > 0 ? `${analyzerFps} FPS` : '0 FPS'}
        </span>
      </div>

      {/* Overlay */}
      <div className="flex items-center justify-between">
        <span className="text-theme-text-secondary">{t('overlayLabel')}</span>
        <span className="text-theme-text-primary text-xs font-mono">
          {overlayFps} FPS
        </span>
      </div>

      {/* Objects */}
      <div className="flex items-center justify-between">
        <span className="text-theme-text-secondary">{t('objectsLabel')}</span>
        <span
          className={`text-xs px-2 py-0.5 rounded ${objectCount > 0 ? 'bg-theme-accent text-white' : 'bg-theme-bg-tertiary text-theme-text-muted border border-theme-border'}`}
        >
          {objectCount}
        </span>
      </div>
    </div>
  );
}

export default StatusPanel;
