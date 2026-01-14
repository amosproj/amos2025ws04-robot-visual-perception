/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useEffect, useRef, useState } from 'react';
import { useTheme } from '../context/ThemeContext';

interface ThemeToggleProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export default function ThemeToggle({
  className = '',
  size = 'md',
}: ThemeToggleProps) {
  const { resolvedTheme, toggleTheme } = useTheme();
  const [showTooltip, setShowTooltip] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const tooltipText = `Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`;

  const handleMouseEnter = () => {
    timeoutRef.current = setTimeout(() => {
      setShowTooltip(true);
    }, 300);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setShowTooltip(false);
  };

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const sizeClass = {
    sm: 'p-2',
    md: 'p-2.5',
    lg: 'p-4 w-[4.5rem] h-[4.5rem]',
  }[size];

  const iconSize = {
    sm: 20,
    md: 24,
    lg: 40,
  }[size];

  return (
    <button
      onClick={toggleTheme}
      className={`relative flex items-center justify-center ${sizeClass} rounded-lg bg-theme-bg-tertiary hover:bg-theme-bg-hover text-theme-accent border border-theme-border transition-colors ${className}`}
      aria-label={tooltipText}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {resolvedTheme === 'dark' ? (
        // Sun icon for switching to light mode
        <svg
          width={iconSize}
          height={iconSize}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="5" />
          <line x1="12" y1="1" x2="12" y2="3" />
          <line x1="12" y1="21" x2="12" y2="23" />
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
          <line x1="1" y1="12" x2="3" y2="12" />
          <line x1="21" y1="12" x2="23" y2="12" />
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>
      ) : (
        // Moon icon for switching to dark mode
        <svg
          width={iconSize}
          height={iconSize}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      )}

      {showTooltip && (
        <div className="absolute z-[100] px-3 py-1.5 text-xs font-medium bg-[#2d3436] text-white border border-gray-600 rounded-md shadow-xl whitespace-nowrap pointer-events-none top-full left-1/2 -translate-x-1/2 mt-2">
          {tooltipText}
          <div className="absolute w-2 h-2 bg-[#2d3436] border-gray-600 transform rotate-45 -top-1 left-1/2 -translate-x-1/2 border-l border-t" />
        </div>
      )}
    </button>
  );
}
