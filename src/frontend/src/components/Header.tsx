/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useI18n } from '../i18n';
import ThemeToggle from './ThemeToggle';

export interface HeaderProps {
  /** Whether to show in minimal/game mode */
  minimal?: boolean;
}

export default function Header({ minimal = false }: HeaderProps) {
  const { t, language, setLanguage, languageOptions } = useI18n();

  if (minimal) {
    return (
      <header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 py-2 pointer-events-none">
        {/* Language selector - top left */}
        <div className="pointer-events-auto">
          <select
            id="language-select"
            value={language}
            onChange={(event) =>
              setLanguage(event.target.value as typeof language)
            }
            className="bg-[#2d3436] text-white border border-theme-border px-3 py-1.5 rounded text-sm cursor-pointer shadow-lg"
          >
            {languageOptions.map((option) => (
              <option key={option.value} value={option.value} className="bg-[#2d3436] text-white">
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Title - center */}
        <h1 className="my-0 text-theme-accent text-xl md:text-2xl font-light">
          {t('appTitle')}
        </h1>

        {/* Theme toggle - top right */}
        <div className="pointer-events-auto">
          <ThemeToggle />
        </div>
      </header>
    );
  }

  // Original header for non-game mode (kept for backwards compatibility)
  return (
    <div className="text-center mb-8">
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
}
