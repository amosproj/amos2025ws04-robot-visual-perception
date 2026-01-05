/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import ThemeToggle from './ThemeToggle';

export interface HeaderProps {
  videoState: string;
  latencyMs?: number;
  analyzerConnected: boolean;
  analyzerFps: number;
  overlayFps: number;
  objectCount: number;
}

// Helper function to get status value classes
const getStatusValueClass = (isConnected: boolean) => {
  if (isConnected) {
    return 'bg-gradient-to-br from-theme-success to-theme-success-secondary text-white shadow-success-glow';
  }
  return 'bg-theme-bg-tertiary text-theme-text-primary border border-theme-border';
};

const getVideoStateClass = (state: string) => {
  if (state === 'connected') {
    return 'bg-gradient-to-br from-theme-success to-theme-success-secondary text-white shadow-success-glow';
  }
  if (state === 'connecting') {
    return 'bg-gradient-to-br from-theme-warning to-theme-warning-secondary text-white shadow-warning-glow animate-pulse';
  }
  if (state === 'error') {
    return 'bg-gradient-to-br from-theme-error to-theme-error-secondary text-white shadow-error-glow';
  }
  return 'bg-theme-bg-tertiary text-theme-text-primary border border-theme-border';
};

export default function Header({
  videoState,
  latencyMs,
  analyzerConnected,
  analyzerFps,
  overlayFps,
  objectCount,
}: HeaderProps) {
  return (
    <div className="text-center mb-8">
      <div className="flex justify-between items-center mb-5">
        <div className="w-10" /> {/* Spacer for centering */}
        <h1 className="my-0 text-theme-accent text-[2.5rem] font-light shadow-accent-glow">
          Robot Visual Perception
        </h1>
        <ThemeToggle />
      </div>
      <div className="flex justify-center gap-8 flex-wrap bg-theme-bg-secondary border border-theme-border-subtle p-4 rounded-lg shadow-card">
        <div className="flex items-center gap-2 text-sm">
          <span className="font-semibold text-theme-text-secondary">Video:</span>
          <span
            className={`font-medium px-3 py-1 rounded ${getVideoStateClass(videoState)}`}
          >
            {videoState}
          </span>
          {latencyMs && (
            <span className="text-theme-accent text-xs font-semibold shadow-accent-glow">
              ({latencyMs}ms)
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 text-sm">
          <span className="font-semibold text-theme-text-secondary">Analyzer:</span>
          <span
            className={`font-medium px-3 py-1 rounded ${getStatusValueClass(analyzerConnected)}`}
          >
            {analyzerConnected ? 'Connected' : 'Disconnected'}
          </span>
          {analyzerFps && analyzerFps > 0 && (
            <span className="text-theme-accent text-xs font-semibold shadow-accent-glow">
              ({analyzerFps} FPS)
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 text-sm">
          <span className="font-semibold text-theme-text-secondary">Overlay:</span>
          <span className="font-medium px-3 py-1 rounded bg-theme-bg-tertiary text-theme-text-primary border border-theme-border">
            {overlayFps} FPS
          </span>
        </div>

        <div className="flex items-center gap-2 text-sm">
          <span className="font-semibold text-theme-text-secondary">Objects:</span>
          <span className="font-medium px-3 py-1 rounded bg-theme-bg-tertiary text-theme-text-primary border border-theme-border">
            {objectCount}
          </span>
        </div>
      </div>
    </div>
  );
}
