/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

/** @type {import('tailwindcss').Config} */
export default {
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
      },
    },
  },
  plugins: [],
};
