/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from 'react';

export type Theme = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

interface ThemeContextValue {
  /** User-selected theme preference */
  theme: Theme;
  /** Actual applied theme (resolved from system if theme === 'system') */
  resolvedTheme: ResolvedTheme;
  /** Set theme preference */
  setTheme: (theme: Theme) => void;
  /** Toggle between light and dark */
  toggleTheme: () => void;
}

const STORAGE_KEY = 'theme-preference';

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function getSystemTheme(): ResolvedTheme {
  if (typeof window === 'undefined') return 'dark';
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light';
}

function getStoredTheme(): Theme | null {
  if (typeof window === 'undefined') return null;
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'light' || stored === 'dark' || stored === 'system') {
    return stored;
  }
  return null;
}

interface ThemeProviderProps {
  children: ReactNode;
  defaultTheme?: Theme;
}

export function ThemeProvider({
  children,
  defaultTheme = 'system',
}: ThemeProviderProps) {
  const [theme, setThemeState] = useState<Theme>(() => {
    return getStoredTheme() || defaultTheme;
  });
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() => {
    const initial = getStoredTheme() || defaultTheme;
    return initial === 'system' ? getSystemTheme() : initial;
  });

  // Apply theme class to document
  const applyTheme = useCallback((resolved: ResolvedTheme) => {
    const root = document.documentElement;

    // Temporarily disable transitions to prevent flash
    root.classList.add('theme-transition-disabled');

    if (resolved === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }

    // Re-enable transitions after a frame
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        root.classList.remove('theme-transition-disabled');
      });
    });
  }, []);

  // Resolve and apply theme whenever theme or system preference changes
  useEffect(() => {
    const resolved = theme === 'system' ? getSystemTheme() : theme;
    setResolvedTheme(resolved);
    applyTheme(resolved);
  }, [theme, applyTheme]);

  // Listen for system theme changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = () => {
      if (theme === 'system') {
        const resolved = getSystemTheme();
        setResolvedTheme(resolved);
        applyTheme(resolved);
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [theme, applyTheme]);

  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme);
    localStorage.setItem(STORAGE_KEY, newTheme);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(resolvedTheme === 'dark' ? 'light' : 'dark');
  }, [resolvedTheme, setTheme]);

  return (
    <ThemeContext.Provider
      value={{ theme, resolvedTheme, setTheme, toggleTheme }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
