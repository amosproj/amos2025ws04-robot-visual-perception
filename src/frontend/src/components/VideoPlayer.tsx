/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useRef, useState, RefObject, forwardRef, useImperativeHandle } from 'react';
import VideoOverlay, { VideoOverlayHandle } from './video/VideoOverlay';
import { PlayerControls } from './video/PlayerControls';

export interface VideoPlayerProps {
  /** Reference to the video element */
  videoRef: RefObject<HTMLVideoElement>;
  /** Current video connection state */
  videoState: string;
  /** Whether video is paused */
  isPaused: boolean;
  /** Toggle play/pause function */
  onTogglePlay: () => void;
  /** Enter fullscreen function */
  onFullscreen: () => void;
  /** Callback for overlay FPS updates */
  onOverlayFpsUpdate: (fps: number) => void;
}

export interface VideoPlayerHandle {
  /** Clear the video overlay */
  clearOverlay: () => void;
  /** Update overlay with metadata */
  updateOverlay: (metadata: any) => void;
}

/**
 * Video player component that combines video element, overlay, and player controls
 */
const VideoPlayer = forwardRef<VideoPlayerHandle, VideoPlayerProps>(({ 
  videoRef, 
  videoState, 
  isPaused, 
  onTogglePlay, 
  onFullscreen, 
  onOverlayFpsUpdate 
}, ref) => {
  const overlayRef = useRef<VideoOverlayHandle>(null);
  const [showControls, setShowControls] = useState(false);

  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    clearOverlay: () => overlayRef.current?.clear(),
    updateOverlay: (metadata: any) => overlayRef.current?.updateMetadata(metadata),
  }));

  return (
    <div 
      className="video-container"
      onMouseEnter={() => setShowControls(true)}
      onMouseLeave={() => setShowControls(false)}
    >
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="video-stream"
      />

      <VideoOverlay
        ref={overlayRef}
        videoRef={videoRef}
        isPaused={isPaused}
        onFrameProcessed={onOverlayFpsUpdate}
      />
      
      <PlayerControls 
        isPlaying={videoState === 'connected' && !isPaused}
        showControls={showControls}
        onTogglePlay={onTogglePlay}
        onFullscreen={onFullscreen}
      />
    </div>
  );
});

VideoPlayer.displayName = 'VideoPlayer';

export default VideoPlayer;
