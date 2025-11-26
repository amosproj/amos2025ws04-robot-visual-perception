/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */



export interface HeaderProps {
  videoState: string;
  latencyMs?: number;
  analyzerConnected: boolean;
  analyzerFps: number;
  overlayFps: number;
  objectCount: number;
}

export default function Header({
  videoState,
  latencyMs,
  analyzerConnected,
  analyzerFps,
  overlayFps,
  objectCount,
}: HeaderProps) {
  return (
    <div className="header">
      <h1>Robot Visual Perception</h1>
      <div className="status-bar">
        <div className={`status-item ${videoState}`}>
          <span className="status-label">Video:</span>
          <span className="status-value">{videoState}</span>
          {latencyMs && (
            <span className="status-detail">({latencyMs}ms)</span>
          )}
        </div>

        <div
          className={`status-item ${analyzerConnected ? 'connected' : 'disconnected'}`}
        >
          <span className="status-label">Analyzer:</span>
          <span className="status-value">
            {analyzerConnected ? 'Connected' : 'Disconnected'}
          </span>
          {analyzerFps && analyzerFps > 0 && (
            <span className="status-detail">({analyzerFps} FPS)</span>
          )}
        </div>

        <div className="status-item">
          <span className="status-label">Overlay:</span>
          <span className="status-value">{overlayFps} FPS</span>
        </div>

        <div className="status-item">
          <span className="status-label">Objects:</span>
          <span className="status-value">{objectCount}</span>
        </div>
      </div>
    </div>
  );
}
