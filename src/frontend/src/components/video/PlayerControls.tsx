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
      className={`absolute inset-0 pointer-events-none flex flex-col justify-end p-4 transition-opacity duration-300 ${
        showControls ? 'opacity-100' : 'opacity-0'
      }`}
    >
      <div className="flex justify-between items-end w-full">
        {/* Left side - Play/Pause */}
        <button
          onClick={onTogglePlay}
          className="pointer-events-auto p-4 bg-black/40 hover:bg-black/60 rounded-xl backdrop-blur-md text-white transition-colors"
          title={isPlaying ? 'Pause' : 'Play'}
        >
          {!isPlaying ? (
            <Play size={36} fill="white" />
          ) : (
            <Pause size={36} fill="white" />
          )}
        </button>

        {/* Right side - Fullscreen */}
        <button
          onClick={onFullscreen}
          className="pointer-events-auto p-2 bg-black/40 hover:bg-black/60 rounded-lg backdrop-blur-md text-white transition-colors"
          title="Fullscreen"
        >
          <Maximize size={24} />
        </button>
      </div>
    </div>
  );
};
