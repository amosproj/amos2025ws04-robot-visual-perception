/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import {
  useRef,
  useState,
  useEffect,
  RefObject,
  forwardRef,
  useImperativeHandle,
  ReactNode,
} from 'react';
import VideoOverlay, { VideoOverlayHandle } from './video/VideoOverlay';
import { PlayerControls } from './video/PlayerControls';

export interface VideoPlayerProps {
  /** Reference to the video element */
  videoRef: RefObject<HTMLVideoElement>;
  /** Reference to the video container element (for fullscreen) */
  containerRef: RefObject<HTMLDivElement>;
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
  /** Optional metadata widget to display in fullscreen */
  metadataWidget?: ReactNode;
}

export interface VideoPlayerHandle {
  /** Update overlay with metadata */
  updateOverlay: (metadata: any) => void;
}

/**
 * Video player component that combines video element, overlay, and player controls
 */
const VideoPlayer = forwardRef<VideoPlayerHandle, VideoPlayerProps>(
  (
    {
      videoRef,
      containerRef,
      videoState,
      isPaused,
      onTogglePlay,
      onFullscreen,
      onOverlayFpsUpdate,
      metadataWidget,
    },
    ref
  ) => {
    const overlayRef = useRef<VideoOverlayHandle>(null);
    const [showControls, setShowControls] = useState(false);
    const [isFullscreen, setIsFullscreen] = useState(false);

    // Expose methods via ref
    useImperativeHandle(ref, () => ({
      updateOverlay: (metadata: any) =>
        overlayRef.current?.updateMetadata(metadata),
    }));

    // Listen for fullscreen changes to update state and trigger overlay resize
    useEffect(() => {
      const handleFullscreenChange = () => {
        const doc = document as any;
        const isNowFullscreen = !!(
          doc.fullscreenElement ||
          doc.webkitFullscreenElement ||
          doc.msFullscreenElement
        );
        setIsFullscreen(isNowFullscreen);
      };

      document.addEventListener('fullscreenchange', handleFullscreenChange);
      document.addEventListener(
        'webkitfullscreenchange',
        handleFullscreenChange
      );
      document.addEventListener('msfullscreenchange', handleFullscreenChange);

      return () => {
        document.removeEventListener(
          'fullscreenchange',
          handleFullscreenChange
        );
        document.removeEventListener(
          'webkitfullscreenchange',
          handleFullscreenChange
        );
        document.removeEventListener(
          'msfullscreenchange',
          handleFullscreenChange
        );
      };
    }, []);

    return (
      <div
        ref={containerRef}
        className={`relative flex justify-center ${
          isFullscreen ? 'w-full h-full items-center bg-black mb-0' : 'mb-8'
        }`}
        onMouseEnter={() => setShowControls(true)}
        onMouseLeave={() => setShowControls(false)}
      >
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`block bg-black ${
            isFullscreen
              ? 'w-full h-full object-contain'
              : 'max-w-full w-[640px] h-auto rounded-xl shadow-[0_4px_20px_rgba(0,0,0,0.15)]'
          }`}
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

        {/* Render metadata widget inside container for fullscreen support */}
        {metadataWidget}
      </div>
    );
  }
);

VideoPlayer.displayName = 'VideoPlayer';

export default VideoPlayer;
