/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Status indicator colors
        status: {
          connected: '#0f0',
          connecting: '#ff0',
          error: '#f00',
          idle: '#666',
        },
        // Brand colors
        brand: {
          purple: {
            from: '#667eea',
            to: '#764ba2',
          },
          gray: '#666',
        },
        // Theme-aware semantic colors using CSS variables
        theme: {
          'bg-primary': 'var(--color-bg-primary)',
          'bg-secondary': 'var(--color-bg-secondary)',
          'bg-tertiary': 'var(--color-bg-tertiary)',
          'bg-hover': 'var(--color-bg-hover)',
          'bg-disabled': 'var(--color-bg-disabled)',
          'text-primary': 'var(--color-text-primary)',
          'text-secondary': 'var(--color-text-secondary)',
          'text-muted': 'var(--color-text-muted)',
          border: 'var(--color-border)',
          'border-subtle': 'var(--color-border-subtle)',
          accent: 'var(--color-accent)',
          'accent-hover': 'var(--color-accent-hover)',
          success: 'var(--color-success)',
          'success-secondary': 'var(--color-success-secondary)',
          warning: 'var(--color-warning)',
          'warning-secondary': 'var(--color-warning-secondary)',
          error: 'var(--color-error)',
          'error-secondary': 'var(--color-error-secondary)',
          primary: 'var(--color-primary)',
          'primary-secondary': 'var(--color-primary-secondary)',
        },
      },
      boxShadow: {
        card: 'var(--shadow-card)',
        'accent-glow': 'var(--shadow-accent-glow)',
        'success-glow': 'var(--shadow-success-glow)',
        'warning-glow': 'var(--shadow-warning-glow)',
        'error-glow': 'var(--shadow-error-glow)',
      },
    },
  },
  plugins: [],
};
