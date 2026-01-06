/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useI18n } from '../i18n';
import type { TranslationKey } from '../i18n/translations';
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
      <div className="flex justify-between items-center mb-5">
        <div className="w-10" /> {/* Spacer for centering */}
        <h1 className="my-0 text-theme-accent text-[2.5rem] font-light shadow-accent-glow">
          {t('appTitle')}
        </h1>
        <ThemeToggle />
      </div>
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
            className="bg-theme-bg-tertiary border border-theme-border text-theme-text-primary px-2 py-1 rounded text-sm"
          >
            {languageOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="flex justify-center gap-8 flex-wrap bg-theme-bg-secondary border border-theme-border-subtle p-4 rounded-lg shadow-card">
        <div className="flex items-center gap-2 text-sm">
          <span className="font-semibold text-theme-text-secondary">
            {t('videoLabel')}:
          </span>
          <span
            className={`font-medium px-3 py-1 rounded ${getVideoStateClass(videoState)}`}
          >
            {videoStateLabel}
          </span>
          {latencyMs && (
            <span className="text-theme-accent text-xs font-semibold shadow-accent-glow">
              ({latencyMs}ms)
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 text-sm">
          <span className="font-semibold text-theme-text-secondary">
            {t('analyzerLabel')}:
          </span>
          <span
            className={`font-medium px-3 py-1 rounded ${getStatusValueClass(analyzerConnected)}`}
          >
            {analyzerConnected ? t('statusConnected') : t('statusDisconnected')}
          </span>
          {analyzerFps && analyzerFps > 0 && (
            <span className="text-theme-accent text-xs font-semibold shadow-accent-glow">
              ({analyzerFps} FPS)
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 text-sm">
          <span className="font-semibold text-theme-secondary">
            {t('overlayLabel')}:
          </span>
          <span className="font-medium px-3 py-1 rounded bg-theme-bg-tertiary text-theme-text-primary border border-theme-border">
            {overlayFps} FPS
          </span>
        </div>

        <div className="flex items-center gap-2 text-sm">
          <span className="font-semibold text-theme-text-secondary">
            {t('objectsLabel')}:
          </span>
          <span className="font-medium px-3 py-1 rounded bg-theme-bg-tertiary text-theme-text-primary border border-theme-border">
            {objectCount}
          </span>
        </div>
      </div>
    </div>
  );
}
