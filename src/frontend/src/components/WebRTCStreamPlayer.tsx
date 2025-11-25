/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useRef, useState } from 'react';
import { useWebRTCPlayer } from '../hooks/useWebRTCPlayer';
import VideoOverlay, { VideoOverlayHandle } from './VideoOverlay';
import { PlayerControls } from './PlayerControls';

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
}: WebRTCStreamPlayerProps) {
  const {
    videoRef,
    connectionState,
    errorReason,
    isPaused,
    latencyMs,
    togglePlayPause,
    disconnect,
    enterFullscreen,
  } = useWebRTCPlayer({ signalingEndpoint, autoPlay });

  const overlayRef = useRef<VideoOverlayHandle | null>(null);
  const [showControls, setShowControls] = useState(true);
  const [videoReady, setVideoReady] = useState(false);

  // Monitor video ready state for overlay
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleLoadedMetadata = () => {
      // Wait a bit to ensure video is fully ready before enabling overlay
      setTimeout(() => setVideoReady(true), 200);
    };

    video.addEventListener('loadedmetadata', handleLoadedMetadata);

    return () => {
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      setVideoReady(false);
    };
  }, [videoRef]);

  // TODO: Handle data channel for metadata stream from backend
  // When backend sends metadata, call: overlayRef.current?.updateMetadata(metadata)

  // Compose a single status text for display (keeps JSX simple)
  const statusText = (() => {
    if (connectionState === 'connected') {
      return latencyMs != null ? `Connected · ${latencyMs} ms` : 'Connected';
    }
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

      <div
        className="w-full max-w-full relative group rounded-lg overflow-hidden bg-black aspect-video"
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
          <VideoOverlay ref={overlayRef} videoRef={videoRef} />
        )}

        {/* Controls overlay */}
        <PlayerControls
          isPlaying={connectionState === 'connected' && !isPaused}
          showControls={showControls}
          onTogglePlay={togglePlayPause}
          onFullscreen={enterFullscreen}
        />
      </div>
    </div>
  );
}
