/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { ReactNode, useState, useRef, useEffect } from 'react';

export interface IconButtonProps {
  /** Icon to display */
  icon: ReactNode;
  /** Tooltip text shown on hover */
  tooltip: string;
  /** Click handler */
  onClick?: () => void;
  /** Whether the button is active/selected */
  active?: boolean;
  /** Whether the button is disabled */
  disabled?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Button variant */
  variant?: 'default' | 'success' | 'danger' | 'warning';
  /** Size of the button */
  size?: 'sm' | 'md' | 'lg';
  /** Tooltip position */
  tooltipPosition?: 'top' | 'right' | 'bottom' | 'left';
}

const variantStyles = {
  default:
    'bg-theme-bg-secondary hover:bg-theme-bg-hover text-theme-accent border-theme-border',
  success:
    'bg-gradient-to-br from-theme-success to-theme-success-secondary text-white border-theme-success shadow-success-glow',
  danger:
    'bg-gradient-to-br from-theme-error to-theme-error-secondary text-white border-theme-error shadow-error-glow',
  warning:
    'bg-gradient-to-br from-theme-warning to-theme-warning-secondary text-white border-theme-warning shadow-warning-glow animate-pulse',
};

const sizeStyles = {
  sm: 'w-11 h-11',
  md: 'w-14 h-14',
  lg: 'w-12 h-12 sm:w-14 sm:h-14 lg:w-[4.5rem] lg:h-[4.5rem]',
};

const tooltipPositionStyles = {
  top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
  right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
  left: 'right-full top-1/2 -translate-y-1/2 mr-2',
};

export function IconButton({
  icon,
  tooltip,
  onClick,
  active = false,
  disabled = false,
  className = '',
  variant = 'default',
  size = 'md',
  tooltipPosition = 'right',
}: IconButtonProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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

  const baseStyles = `
    relative flex items-center justify-center rounded-lg border
    transition-all duration-200 cursor-pointer
    ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:-translate-y-0.5'}
    ${active ? 'ring-2 ring-theme-accent ring-offset-2 ring-offset-theme-bg-primary' : ''}
  `;

  return (
    <button
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      aria-label={tooltip}
    >
      {icon}

      {/* Tooltip */}
      {showTooltip && (
        <div
          className={`
            absolute z-[100] px-3 py-1.5 text-xs font-medium
            bg-[#2d3436] text-white
            border border-gray-600 rounded-md shadow-xl
            whitespace-nowrap pointer-events-none
            ${tooltipPositionStyles[tooltipPosition]}
          `}
        >
          {tooltip}
          {/* Arrow */}
          <div
            className={`
              absolute w-2 h-2 bg-[#2d3436] border-gray-600
              transform rotate-45
              ${tooltipPosition === 'right' ? '-left-1 top-1/2 -translate-y-1/2 border-l border-b' : ''}
              ${tooltipPosition === 'left' ? '-right-1 top-1/2 -translate-y-1/2 border-r border-t' : ''}
              ${tooltipPosition === 'top' ? '-bottom-1 left-1/2 -translate-x-1/2 border-r border-b' : ''}
              ${tooltipPosition === 'bottom' ? '-top-1 left-1/2 -translate-x-1/2 border-l border-t' : ''}
            `}
          />
        </div>
      )}
    </button>
  );
}

export default IconButton;
