/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useRef, useState } from 'react';
import { useWebRTCPlayer } from '../hooks/useWebRTCPlayer';
import VideoOverlay, { VideoOverlayHandle, MetadataFrame } from './VideoOverlay';
import { PlayerControls } from './PlayerControls';
import MetadataWidget from './MetadataWidget';

// Return Tailwind class for the status indicator dot
const getStatusDotClass = (state: string) => {
  if (state === 'connected') return 'bg-status-connected';
  if (state === 'connecting') return 'bg-status-connecting';
  if (state === 'error') return 'bg-status-error';
  return 'bg-status-idle';
};

export interface WebRTCStreamPlayerProps {
  signalingEndpoint?: string;
  className?: string;
  style?: React.CSSProperties;
  muted?: boolean;
  autoPlay?: boolean;
  /** Enable VideoOverlay with bounding boxes */
  enableOverlay?: boolean;
  /** Enable test mode for VideoOverlay (shows animated test box) */
  overlayTestMode?: boolean;
  /** Enable metadata widget to display stream and detection info */
  enableMetadataWidget?: boolean;
  /** Compact mode for metadata widget (less details) */
  metadataCompact?: boolean;
}

/**
 * A simple React component that shows a remote WebRTC video stream and
 * basic playback controls. It uses the `useWebRTCPlayer` hook to manage
 * the underlying RTCPeerConnection and expose control functions.
 *
 * Props:
 * - `signalingEndpoint` : optional backend URL used for signaling (offer/answer)
 * - `autoPlay`          : when true, attempts to start playback automatically
 * - `muted`             : start the video muted (useful to avoid autoplay blocks)
 * - `enableOverlay`     : enable drawing bounding-box overlays from metadata
 * - `overlayTestMode`   : when `enableOverlay` is true, show simulated boxes
 *
 * The component renders a small status indicator (Idle / Connecting / Error / Connected)
 * and a Disconnect button. It also exposes play/pause and fullscreen actions.
 */
export default function WebRTCStreamPlayer({
  signalingEndpoint,
  className,
  style,
  muted = true,
  autoPlay = false,
  enableOverlay = false,
  overlayTestMode = false,
  enableMetadataWidget = false,
  metadataCompact = false,
}: WebRTCStreamPlayerProps) {
  const {
    videoRef,
    connectionState,
    errorReason,
    isPaused,
    latencyMs,
    stats,
    togglePlayPause,
    disconnect,
    enterFullscreen,
  } = useWebRTCPlayer({ signalingEndpoint, autoPlay });

  const overlayRef = useRef<VideoOverlayHandle | null>(null);
  const videoContainerRef = useRef<HTMLDivElement | null>(null);
  const [showControls, setShowControls] = useState(true);
  const [videoReady, setVideoReady] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showMetadata, setShowMetadata] = useState(true);
  const [videoResolution, setVideoResolution] = useState<{
    width: number;
    height: number;
  }>();
  const [renderFps, setRenderFps] = useState<number>();
  const [videoFps, setVideoFps] = useState<number>();
  const [currentMetadata, setCurrentMetadata] = useState<MetadataFrame>();

  // Monitor video ready state for overlay and capture video resolution
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleLoadedMetadata = () => {
      // Capture video resolution
      setVideoResolution({
        width: video.videoWidth,
        height: video.videoHeight,
      });
      // Wait a bit to ensure video is fully ready before enabling overlay
      setTimeout(() => setVideoReady(true), 200);
    };

    video.addEventListener('loadedmetadata', handleLoadedMetadata);

    return () => {
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      setVideoReady(false);
      setVideoResolution(undefined);
    };
  }, [videoRef]);

  // TODO: Handle data channel for metadata stream from backend
  // When backend sends metadata via WebRTC data channel, do the following:
  // 1. Update the overlay: overlayRef.current?.updateMetadata(metadata)
  // 2. Update local state for widget: setCurrentMetadata(metadata)
  // Example implementation:
  // useEffect(() => {
  //   const pc = pcRef.current; // Get from useWebRTCPlayer hook
  //   if (!pc) return;
  //   const dataChannel = pc.createDataChannel('metadata');
  //   dataChannel.onmessage = (event) => {
  //     const metadata: MetadataFrame = JSON.parse(event.data);
  //     overlayRef.current?.updateMetadata(metadata);
  //     setCurrentMetadata(metadata);
  //   };
  // }, [connectionState]);

  // Callback for when overlay processes a frame (for FPS tracking)
  const handleFrameProcessed = (overlayFps: number) => {
    setRenderFps(overlayFps);
  };

  // Callback for when overlay metadata is updated (sync to widget)
  const handleMetadataUpdated = (metadata: MetadataFrame) => {
    setCurrentMetadata(metadata);
  };

  // Track video FPS (camera framerate)
  useEffect(() => {
    const video = videoRef.current;
    if (!video || connectionState !== 'connected') return;

    let lastFrameTime = 0;
    let frameCount = 0;
    let rafId: number;

    const measureFps = (now: number) => {
      if (lastFrameTime === 0) {
        lastFrameTime = now;
      }

      frameCount++;
      const elapsed = now - lastFrameTime;

      if (elapsed >= 1000) {
        // Update every second
        const fps = Math.round((frameCount * 1000) / elapsed);
        setVideoFps(fps);
        frameCount = 0;
        lastFrameTime = now;
      }

      // Use requestVideoFrameCallback if available, otherwise requestAnimationFrame
      if ('requestVideoFrameCallback' in video) {
        (video as any).requestVideoFrameCallback(measureFps);
      } else {
        rafId = requestAnimationFrame(measureFps);
      }
    };

    // Start measuring
    if ('requestVideoFrameCallback' in video) {
      (video as any).requestVideoFrameCallback(measureFps);
    } else {
      rafId = requestAnimationFrame(measureFps);
    }

    return () => {
      if (rafId) {
        cancelAnimationFrame(rafId);
      }
    };
  }, [videoRef, connectionState]);

  // Monitor fullscreen state changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      const doc = document as any;
      const isCurrentlyFullscreen = !!(
        doc.fullscreenElement ||
        doc.webkitFullscreenElement ||
        doc.msFullscreenElement
      );
      setIsFullscreen(isCurrentlyFullscreen);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('msfullscreenchange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
      document.removeEventListener('msfullscreenchange', handleFullscreenChange);
    };
  }, []);

  // Compose a single status text for display (keeps JSX simple)
  const statusText = (() => {
    if (connectionState === 'connected') return 'Connected';
    if (connectionState === 'connecting') return 'Connecting…';
    if (connectionState === 'error') return `Error: ${errorReason}`;
    return 'Idle';
  })();

  return (
    <div className={`flex flex-col gap-4 ${className || ''}`} style={style}>
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm opacity-80 flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${getStatusDotClass(connectionState)}`} />
          {statusText}
        </span>
        <div className="flex gap-3">
          {enableMetadataWidget && (
            <button
              onClick={() => setShowMetadata(!showMetadata)}
              className={`px-6 py-2.5 text-white rounded-md text-[15px] font-semibold transition-all duration-200 ${
                showMetadata
                  ? 'bg-blue-600 hover:bg-blue-700'
                  : 'bg-gray-600 hover:bg-gray-700'
              }`}
            >
              {showMetadata ? 'Hide Stats' : 'Show Stats'}
            </button>
          )}
          <button
            onClick={disconnect}
            disabled={connectionState === 'idle'}
            className={`px-6 py-2.5 text-white rounded-md text-[15px] font-semibold transition-all duration-200 ${
              connectionState === 'idle'
                ? 'bg-brand-gray cursor-not-allowed opacity-50'
                : 'bg-red-600 hover:bg-red-700 cursor-pointer'
            }`}
          >
            Disconnect
          </button>
        </div>
      </div>

      <div className="flex gap-4">
        <div
          ref={videoContainerRef}
          className="flex-1 relative group rounded-lg overflow-hidden bg-black aspect-video"
          onMouseEnter={() => setShowControls(true)}
          onMouseLeave={() => setShowControls(false)}
        >
        <video
          ref={videoRef}
          autoPlay={autoPlay}
          playsInline
          muted={muted}
          className="w-full h-full object-contain block"
        />

        {/* VideoOverlay - only render when video is ready and overlay is enabled */}
        {enableOverlay && videoReady && (
          <VideoOverlay
            ref={overlayRef}
            videoRef={videoRef}
            testMode={overlayTestMode}
            onFrameProcessed={handleFrameProcessed}
            onMetadataUpdated={handleMetadataUpdated}
          />
        )}

        {/* Controls overlay */}
        <PlayerControls
          isPlaying={connectionState === 'connected' && !isPaused}
          showControls={showControls}
          onTogglePlay={togglePlayPause}
          onFullscreen={enterFullscreen}
        />

        {/* Fullscreen Metadata Overlay - shown top-left in fullscreen mode */}
        {enableMetadataWidget && showMetadata && isFullscreen && (
          <div className="absolute top-4 left-4 z-50 max-h-[calc(100vh-2rem)] overflow-y-auto">
            <MetadataWidget
              streamMetadata={{
                latencyMs,
                connectionState,
                videoResolution,
                renderFps,
                videoFps,
                ...stats,
              }}
              detectionMetadata={currentMetadata}
              compact={metadataCompact}
              className="w-80"
            />
          </div>
        )}
        </div>

        {/* Metadata Widget - shown to the right of video in normal mode */}
        {enableMetadataWidget && showMetadata && !isFullscreen && (
          <div className="w-80 flex-shrink-0">
            <MetadataWidget
              streamMetadata={{
                latencyMs,
                connectionState,
                videoResolution,
                renderFps,
                videoFps,
                ...stats,
              }}
              detectionMetadata={currentMetadata}
              compact={metadataCompact}
            />
          </div>
        )}
      </div>
    </div>
  );
}
