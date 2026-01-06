/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useI18n } from '../i18n';
import type { TranslationKey } from '../i18n/translations';

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
  const { t, language, setLanguage, languageOptions } = useI18n();
  const videoStateLabels: Record<string, TranslationKey> = {
    connected: 'videoStateConnected',
    connecting: 'videoStateConnecting',
    error: 'videoStateError',
    idle: 'videoStateIdle',
  };
  const videoStateLabel = t(videoStateLabels[videoState] ?? 'videoStateIdle');

  return (
    <div className="text-center mb-8">
      <h1 className="my-0 mb-5 text-[#00d4ff] text-[2.5rem] font-light shadow-[0_0_10px_rgba(0,212,255,0.3)]">
        {t('appTitle')}
      </h1>
      <div className="flex justify-center mb-4">
        <label
          htmlFor="language-select"
          className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-[#888]"
        >
          <span>{t('languageLabel')}</span>
          <select
            id="language-select"
            value={language}
            onChange={(event) =>
              setLanguage(event.target.value as typeof language)
            }
            className="bg-[#2a2a2a] border border-[#404040] text-[#e0e0e0] px-2 py-1 rounded text-sm"
          >
            {languageOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="flex justify-center gap-8 flex-wrap bg-[#2a2a2a] border border-[#404040] p-4 rounded-lg shadow-[0_4px_20px_rgba(0,0,0,0.4)]">
        <div className="flex items-center gap-2 text-sm">
          <span className="font-semibold text-[#b0b0b0]">
            {t('videoLabel')}:
          </span>
          <span
            className={`font-medium px-3 py-1 rounded ${getVideoStateClass(videoState)}`}
          >
            {videoStateLabel}
          </span>
          {latencyMs && (
            <span className="text-[#00d4ff] text-xs font-semibold shadow-[0_0_4px_rgba(0,212,255,0.5)]">
              ({latencyMs}ms)
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 text-sm">
          <span className="font-semibold text-[#b0b0b0]">
            {t('analyzerLabel')}:
          </span>
          <span
            className={`font-medium px-3 py-1 rounded ${getStatusValueClass(analyzerConnected)}`}
          >
            {analyzerConnected ? t('statusConnected') : t('statusDisconnected')}
          </span>
          {analyzerFps && analyzerFps > 0 && (
            <span className="text-[#00d4ff] text-xs font-semibold shadow-[0_0_4px_rgba(0,212,255,0.5)]">
              ({analyzerFps} FPS)
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 text-sm">
          <span className="font-semibold text-[#b0b0b0]">
            {t('overlayLabel')}:
          </span>
          <span className="font-medium px-3 py-1 rounded bg-[#404040] text-[#e0e0e0] border border-[#555]">
            {overlayFps} FPS
          </span>
        </div>

        <div className="flex items-center gap-2 text-sm">
          <span className="font-semibold text-[#b0b0b0]">
            {t('objectsLabel')}:
          </span>
          <span className="font-medium px-3 py-1 rounded bg-[#404040] text-[#e0e0e0] border border-[#555]">
            {objectCount}
          </span>
        </div>
      </div>
    </div>
  );
}
