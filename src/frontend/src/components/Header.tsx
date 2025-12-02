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

// Helper function to get status value classes
const getStatusValueClass = (isConnected: boolean) => {
  if (isConnected) {
    return 'bg-gradient-to-br from-[#00d4aa] to-[#00b894] text-white shadow-[0_0_8px_rgba(0,212,170,0.3)]';
  }
  return 'bg-[#404040] text-[#e0e0e0] border border-[#555]';
};

const getVideoStateClass = (state: string) => {
  if (state === 'connected') {
    return 'bg-gradient-to-br from-[#00d4aa] to-[#00b894] text-white shadow-[0_0_8px_rgba(0,212,170,0.3)]';
  }
  if (state === 'connecting') {
    return 'bg-gradient-to-br from-[#fdcb6e] to-[#e17055] text-white shadow-[0_0_8px_rgba(253,203,110,0.3)] animate-pulse';
  }
  if (state === 'error') {
    return 'bg-gradient-to-br from-[#fd79a8] to-[#e84393] text-white shadow-[0_0_8px_rgba(253,121,168,0.3)]';
  }
  return 'bg-[#404040] text-[#e0e0e0] border border-[#555]';
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
      <h1 className="my-0 mb-5 text-[#00d4ff] text-[2.5rem] font-light shadow-[0_0_10px_rgba(0,212,255,0.3)]">
        Robot Visual Perception
      </h1>
      <div className="flex justify-center gap-8 flex-wrap bg-[#2a2a2a] border border-[#404040] p-4 rounded-lg shadow-[0_4px_20px_rgba(0,0,0,0.4)]">
        <div className="flex items-center gap-2 text-sm">
          <span className="font-semibold text-[#b0b0b0]">Video:</span>
          <span
            className={`font-medium px-3 py-1 rounded ${getVideoStateClass(videoState)}`}
          >
            {videoState}
          </span>
          {latencyMs && (
            <span className="text-[#00d4ff] text-xs font-semibold shadow-[0_0_4px_rgba(0,212,255,0.5)]">
              ({latencyMs}ms)
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 text-sm">
          <span className="font-semibold text-[#b0b0b0]">Analyzer:</span>
          <span
            className={`font-medium px-3 py-1 rounded ${getStatusValueClass(analyzerConnected)}`}
          >
            {analyzerConnected ? 'Connected' : 'Disconnected'}
          </span>
          {analyzerFps && analyzerFps > 0 && (
            <span className="text-[#00d4ff] text-xs font-semibold shadow-[0_0_4px_rgba(0,212,255,0.5)]">
              ({analyzerFps} FPS)
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 text-sm">
          <span className="font-semibold text-[#b0b0b0]">Overlay:</span>
          <span className="font-medium px-3 py-1 rounded bg-[#404040] text-[#e0e0e0] border border-[#555]">
            {overlayFps} FPS
          </span>
        </div>

        <div className="flex items-center gap-2 text-sm">
          <span className="font-semibold text-[#b0b0b0]">Objects:</span>
          <span className="font-medium px-3 py-1 rounded bg-[#404040] text-[#e0e0e0] border border-[#555]">
            {objectCount}
          </span>
        </div>
      </div>
    </div>
  );
}
