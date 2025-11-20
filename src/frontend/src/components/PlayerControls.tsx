/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import React from 'react';
import { Play, Pause, Maximize } from './Icons';

interface PlayerControlsProps {
  isPlaying: boolean;
  showControls: boolean;
  onTogglePlay: () => void;
  onFullscreen: () => void;
}

export const PlayerControls: React.FC<PlayerControlsProps> = ({
  isPlaying,
  showControls,
  onTogglePlay,
  onFullscreen,
}) => {
  return (
    <div
      className={`absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/70 to-transparent flex items-center justify-between transition-opacity duration-300 ${
        showControls ? 'opacity-100' : 'opacity-0'
      }`}
    >
      {/* Left side - Play/Pause */}
      <button
        onClick={onTogglePlay}
        className="bg-transparent border-none text-white cursor-pointer p-2 flex items-center justify-center rounded hover:bg-white/20 transition-colors"
      >
        {!isPlaying ? (
          <Play size={24} fill="white" />
        ) : (
          <Pause size={24} fill="white" />
        )}
      </button>

      {/* Right side - Fullscreen */}
      <div className="flex gap-1 items-center">
        <button
          onClick={onFullscreen}
          className="bg-transparent border-none text-white cursor-pointer p-2 flex items-center justify-center rounded hover:bg-white/20 transition-colors"
        >
          <Maximize size={20} />
        </button>
      </div>
    </div>
  );
};
