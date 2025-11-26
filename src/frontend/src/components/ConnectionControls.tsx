/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */



export interface ConnectionControlsProps {
  videoState: string;
  analyzerConnected: boolean;
  onConnectVideo: () => void;
  onDisconnectVideo: () => void;
  onConnectAnalyzer: () => void;
  onDisconnectAnalyzer: () => void;
  onClearOverlay: () => void;
}

export default function ConnectionControls({
  videoState,
  analyzerConnected,
  onConnectVideo,
  onDisconnectVideo,
  onConnectAnalyzer,
  onDisconnectAnalyzer,
  onClearOverlay,
}: ConnectionControlsProps) {
  return (
    <div className="controls">
      <button
        onClick={videoState === 'connected' ? onDisconnectVideo : onConnectVideo}
        className={`btn ${videoState === 'connected' ? 'btn-danger' : 'btn-primary'}`}
        disabled={videoState === 'connecting'}
      >
        {videoState === 'connecting'
          ? 'Connecting...'
          : videoState === 'connected'
            ? 'Disconnect Video'
            : 'Connect Video'}
      </button>

      <button
        onClick={analyzerConnected ? onDisconnectAnalyzer : onConnectAnalyzer}
        className={`btn ${analyzerConnected ? 'btn-danger' : 'btn-primary'}`}
      >
        {analyzerConnected ? 'Disconnect Analyzer' : 'Connect Analyzer'}
      </button>

      <button onClick={onClearOverlay} className="btn btn-secondary">
        Clear Overlay
      </button>
    </div>
  );
}
