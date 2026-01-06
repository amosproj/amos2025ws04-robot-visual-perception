/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import {
  LANGUAGE_OPTIONS,
  SUPPORTED_LANGUAGES,
  translations,
  type Language,
  type TranslationKey,
  type TranslationParams,
  type TranslationValue,
} from './translations';

const STORAGE_KEY = 'rvp.language';
const SUPPORTED_LANGUAGE_SET = new Set(SUPPORTED_LANGUAGES);

interface I18nContextValue {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: TranslationKey, params?: TranslationParams) => string;
  languageOptions: typeof LANGUAGE_OPTIONS;
}

const I18nContext = createContext<I18nContextValue | null>(null);

const normalizeLanguage = (value?: string | null): Language | null => {
  if (!value) return null;
  const code = value.toLowerCase().split('-')[0];
  return SUPPORTED_LANGUAGE_SET.has(code as Language)
    ? (code as Language)
    : null;
};

const resolveStoredLanguage = (): Language | null => {
  if (typeof window === 'undefined') return null;
  return normalizeLanguage(window.localStorage.getItem(STORAGE_KEY));
};

const resolveBrowserLanguage = (): Language => {
  if (typeof navigator === 'undefined') return 'en';
  return normalizeLanguage(navigator.language) ?? 'en';
};

const formatTranslation = (
  entry: TranslationValue,
  params?: TranslationParams
) => {
  return typeof entry === 'function' ? entry(params ?? {}) : entry;
};

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [language, setLanguage] = useState<Language>(() => {
    return resolveStoredLanguage() ?? resolveBrowserLanguage();
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(STORAGE_KEY, language);
  }, [language]);

  useEffect(() => {
    if (typeof document === 'undefined') return;
    document.documentElement.lang = language;
  }, [language]);

  const t = useCallback(
    (key: TranslationKey, params?: TranslationParams) => {
      const dictionary = translations[language] ?? translations.en;
      const fallback = translations.en[key];
      const entry = dictionary[key] ?? fallback ?? key;
      return formatTranslation(entry, params);
    },
    [language]
  );

  const value = useMemo<I18nContextValue>(
    () => ({
      language,
      setLanguage,
      t,
      languageOptions: LANGUAGE_OPTIONS,
    }),
    [language, t]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
};

export const useI18n = () => {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within I18nProvider');
  }
  return context;
};
