/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
*/

import { useI18n } from '../i18n';

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
  const { t } = useI18n();
  const btnBase =
    'px-5 py-2.5 border-none rounded-md text-sm font-medium cursor-pointer transition-all duration-200 min-w-[140px]';
  const btnPrimary =
    'bg-gradient-to-br from-[#74b9ff] to-[#0984e3] text-white border border-[#0984e3] shadow-[0_2px_8px_rgba(116,185,255,0.3)] hover:bg-gradient-to-br hover:from-[#0984e3] hover:to-[#0056b3] hover:shadow-[0_4px_12px_rgba(116,185,255,0.4)] hover:-translate-y-px';
  const btnDanger =
    'bg-gradient-to-br from-[#fd79a8] to-[#e84393] text-white border border-[#e84393] shadow-[0_2px_8px_rgba(253,121,168,0.3)] hover:bg-gradient-to-br hover:from-[#e84393] hover:to-[#c82333] hover:shadow-[0_4px_12px_rgba(253,121,168,0.4)] hover:-translate-y-px';
  const btnSecondary =
    'bg-gradient-to-br from-[#636e72] to-[#2d3436] text-white border border-[#636e72] shadow-[0_2px_8px_rgba(99,110,114,0.3)] hover:bg-gradient-to-br hover:from-[#2d3436] hover:to-[#1e2124] hover:shadow-[0_4px_12px_rgba(99,110,114,0.4)] hover:-translate-y-px';
  const btnDisabled = 'opacity-60 cursor-not-allowed';

  return (
    <div className="flex justify-center gap-4 mb-8 flex-wrap">
      <button
        onClick={
          videoState === 'connected' ? onDisconnectVideo : onConnectVideo
        }
        className={`${btnBase} ${videoState === 'connected' ? btnDanger : btnPrimary} ${videoState === 'connecting' ? btnDisabled : ''}`}
        disabled={videoState === 'connecting'}
      >
        {videoState === 'connecting'
          ? t('connectionConnecting')
          : videoState === 'connected'
            ? t('connectionDisconnectVideo')
            : t('connectionConnectVideo')}
      </button>

      <button
        onClick={analyzerConnected ? onDisconnectAnalyzer : onConnectAnalyzer}
        className={`${btnBase} ${analyzerConnected ? btnDanger : btnPrimary}`}
      >
        {analyzerConnected
          ? t('connectionDisconnectAnalyzer')
          : t('connectionConnectAnalyzer')}
      </button>

      <button onClick={onClearOverlay} className={`${btnBase} ${btnSecondary}`}>
        {t('connectionClearOverlay')}
      </button>
    </div>
  );
}
