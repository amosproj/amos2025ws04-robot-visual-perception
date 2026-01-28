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

export interface ConnectionButtonGroupProps extends ConnectionControlsProps {
  variant?: 'page' | 'panel';
}

const buttonStyles = {
  basePage:
    'px-5 py-2.5 border-none rounded-md text-sm font-medium cursor-pointer transition-all duration-200 min-w-[140px]',
  basePanel:
    'px-3 py-2 border-none rounded-md text-xs font-medium cursor-pointer transition-all duration-200 w-full',
  primary:
    'bg-gradient-to-br from-[#74b9ff] to-[#0984e3] text-white border border-[#0984e3] shadow-[0_2px_8px_rgba(116,185,255,0.3)] hover:bg-gradient-to-br hover:from-[#0984e3] hover:to-[#0056b3] hover:shadow-[0_4px_12px_rgba(116,185,255,0.4)] hover:-translate-y-px',
  danger:
    'bg-gradient-to-br from-[#fd79a8] to-[#e84393] text-white border border-[#e84393] shadow-[0_2px_8px_rgba(253,121,168,0.3)] hover:bg-gradient-to-br hover:from-[#e84393] hover:to-[#c82333] hover:shadow-[0_4px_12px_rgba(253,121,168,0.4)] hover:-translate-y-px',
  secondary:
    'bg-gradient-to-br from-[#636e72] to-[#2d3436] text-white border border-[#636e72] shadow-[0_2px_8px_rgba(99,110,114,0.3)] hover:bg-gradient-to-br hover:from-[#2d3436] hover:to-[#1e2124] hover:shadow-[0_4px_12px_rgba(99,110,114,0.4)] hover:-translate-y-px',
  disabled: 'opacity-60 cursor-not-allowed',
};

export function ConnectionButtonGroup({
  videoState,
  analyzerConnected,
  onConnectVideo,
  onDisconnectVideo,
  onConnectAnalyzer,
  onDisconnectAnalyzer,
  onClearOverlay,
  variant = 'page',
}: ConnectionButtonGroupProps) {
  const { t } = useI18n();
  const btnBase =
    variant === 'panel' ? buttonStyles.basePanel : buttonStyles.basePage;
  const containerClass =
    variant === 'panel'
      ? 'grid gap-2'
      : 'flex justify-center gap-4 mb-8 flex-wrap';

  return (
    <div className={containerClass}>
      <button
        onClick={
          videoState === 'connected' ? onDisconnectVideo : onConnectVideo
        }
        className={`${btnBase} ${
          videoState === 'connected'
            ? buttonStyles.danger
            : buttonStyles.primary
        } ${videoState === 'connecting' ? buttonStyles.disabled : ''}`}
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
        className={`${btnBase} ${
          analyzerConnected ? buttonStyles.danger : buttonStyles.primary
        }`}
      >
        {analyzerConnected
          ? t('connectionDisconnectAnalyzer')
          : t('connectionConnectAnalyzer')}
      </button>

      <button
        onClick={onClearOverlay}
        className={`${btnBase} ${buttonStyles.secondary}`}
      >
        {t('connectionClearOverlay')}
      </button>
    </div>
  );
}

export default function ConnectionControls(props: ConnectionControlsProps) {
  return <ConnectionButtonGroup {...props} variant="page" />;
}
