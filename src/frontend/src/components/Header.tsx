/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { forwardRef } from 'react';
import { useI18n } from '../i18n';
import ThemeToggle from './ThemeToggle';
import { IconButton } from './ui/IconButton';
import { Video, VideoOff, Activity, Filter } from './video/Icons';

export interface HeaderProps {
  /** Whether to show in minimal/game mode */
  minimal?: boolean;
  /** Video connection state */
  videoState?: string;
  /** Whether analyzer is connected */
  analyzerConnected?: boolean;
  /** Video connection handlers */
  onConnectVideo?: () => void;
  onDisconnectVideo?: () => void;
  /** Analyzer connection handlers */
  onConnectAnalyzer?: () => void;
  onDisconnectAnalyzer?: () => void;
  /** Panel state */
  showPanel?: boolean;
  onTogglePanel?: () => void;
}

const Header = forwardRef<HTMLDivElement, HeaderProps>((props, ref) => {
  const { minimal = false } = props;
  const { t, language, setLanguage, languageOptions } = useI18n();

  if (minimal) {
    const headerIconSize = 40;
    return (
      <header
        ref={ref}
        className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-10 py-4 pointer-events-none"
      >
        {/* Language selector - top left */}
        <div className="pointer-events-auto flex items-center gap-2">
          {props.onTogglePanel && (
            <IconButton
              size="lg"
              icon={<Filter size={headerIconSize} />}
              tooltip={props.showPanel ? 'Hide Panel' : 'Show Panel'}
              onClick={props.onTogglePanel}
              active={props.showPanel}
              variant={props.showPanel ? 'success' : 'default'}
              tooltipPosition="bottom"
            />
          )}
          <div className="relative">
            <select
              id="language-select"
              value={language}
              onChange={(event) =>
                setLanguage(event.target.value as typeof language)
              }
              className="bg-[#2d3436] text-white border border-theme-border appearance-none pl-3 pr-8 py-2 rounded text-xl cursor-pointer shadow-lg"
            >
              {languageOptions.map((option) => (
                <option
                  key={option.value}
                  value={option.value}
                  className="bg-[#2d3436] text-white"
                >
                  {option.label}
                </option>
              ))}
            </select>
            <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-white">
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M6 9l6 6 6-6" />
              </svg>
            </div>
          </div>
        </div>

        {/* Title - center */}
        <h1 className="my-0 text-theme-accent text-4xl md:text-5xl font-light">
          {t('appTitle')}
        </h1>

        {/* Controls - top right */}
        <div className="pointer-events-auto flex items-center gap-2">
          {/* Connection Controls (only if props provided) */}
          {props.onConnectVideo && (
            <>
              {/* Video connection button */}
              <IconButton
                size="lg"
                icon={
                  props.videoState === 'connected' ? (
                    <Video size={headerIconSize} />
                  ) : (
                    <VideoOff size={headerIconSize} />
                  )
                }
                tooltip={
                  props.videoState === 'connecting'
                    ? t('connectionConnecting')
                    : props.videoState === 'connected'
                      ? t('connectionDisconnectVideo')
                      : t('connectionConnectVideo')
                }
                onClick={
                  props.videoState === 'connected'
                    ? props.onDisconnectVideo
                    : props.onConnectVideo
                }
                disabled={props.videoState === 'connecting'}
                variant={
                  props.videoState === 'connecting'
                    ? 'warning'
                    : props.videoState === 'connected'
                      ? 'success'
                      : 'default'
                }
                tooltipPosition="bottom"
              />

              {/* Analyzer connection button */}
              <IconButton
                size="lg"
                icon={<Activity size={headerIconSize} />}
                tooltip={
                  props.analyzerConnected
                    ? t('connectionDisconnectAnalyzer')
                    : t('connectionConnectAnalyzer')
                }
                onClick={
                  props.analyzerConnected
                    ? props.onDisconnectAnalyzer
                    : props.onConnectAnalyzer
                }
                variant={props.analyzerConnected ? 'success' : 'default'}
                tooltipPosition="bottom"
              />

              <div className="w-px h-10 bg-theme-border mx-3" />
            </>
          )}

          <ThemeToggle size="lg" />
        </div>
      </header>
    );
  }

  // Original header for non-game mode (kept for backwards compatibility)
  return (
    <div ref={ref} className="text-center mb-8">
      <div className="flex justify-between items-center mb-5">
        <div className="w-10" />
        <h1 className="my-0 text-theme-accent text-[2.5rem] font-light shadow-accent-glow">
          {t('appTitle')}
        </h1>
        <ThemeToggle />
      </div>
      <div className="flex justify-center mb-4">
        <label
          htmlFor="language-select-full"
          className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-[#888]"
        >
          <span>{t('languageLabel')}</span>
          <select
            id="language-select-full"
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
    </div>
  );
});

Header.displayName = 'Header';

export default Header;
