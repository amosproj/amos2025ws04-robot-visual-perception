/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useRef, useState } from 'react';
import { useWebRTCPlayer } from '../hooks/useWebRTCPlayer';
import VideoOverlay, { VideoOverlayHandle } from './VideoOverlay';

// Shared colors used across the component
const COLORS = {
  dotConnected: '#0f0', // green
  dotConnecting: '#ff0', // yellow
  dotError: '#f00', // red
  dotIdle: '#666', // gray
  danger: '#dc2626', // red
  dangerHover: '#b91c1c', // red
  controlHover: 'rgba(255,255,255,0.2)', // white
};

// Return color for the status indicator dot
const getStatusColor = (state: string) => {
  if (state === 'connected') return COLORS.dotConnected;
  if (state === 'connecting') return COLORS.dotConnecting;
  if (state === 'error') return COLORS.dotError;
  return COLORS.dotIdle;
};

const Play = ({ size = 24, fill = 'white' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill}>
    <path d="M8 5v14l11-7z" />
  </svg>
);

const Pause = ({ size = 24, fill = 'white' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill}>
    <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
  </svg>
);

const Maximize = ({ size = 20 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
  >
    <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
  </svg>
);

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

  // Styles computed from shared colors
  const statusDotStyle: React.CSSProperties = {
    width: 8,
    height: 8,
    borderRadius: '50%',
    backgroundColor: getStatusColor(connectionState),
  };

  return (
    <div
      className={className}
      style={{ display: 'flex', flexDirection: 'column', gap: 16, ...style }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
        }}
      >
        <span
          style={{
            fontSize: 14,
            opacity: 0.8,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <span style={statusDotStyle} />
          {statusText}
        </span>
        <button
          onClick={disconnect}
          disabled={connectionState === 'idle'}
          style={{
            padding: '10px 24px',
            backgroundColor:
              connectionState === 'idle' ? COLORS.dotIdle : COLORS.danger,
            color: 'white',
            border: 'none',
            borderRadius: 6,
            fontSize: 15,
            fontWeight: 600,
            cursor: connectionState === 'idle' ? 'not-allowed' : 'pointer',
            opacity: connectionState === 'idle' ? 0.5 : 1,
            transition: 'all 0.2s',
          }}
          onMouseOver={(e) => {
            if (connectionState !== 'idle') {
              e.currentTarget.style.backgroundColor = COLORS.dangerHover;
            }
          }}
          onMouseOut={(e) => {
            if (connectionState !== 'idle') {
              e.currentTarget.style.backgroundColor = COLORS.danger;
            }
          }}
        >
          Disconnect
        </button>
      </div>

      <div
        style={{
          width: '100%',
          maxWidth: '100%',
          position: 'relative',
        }}
        onMouseEnter={() => setShowControls(true)}
        onMouseLeave={() => setShowControls(false)}
      >
        <video
          ref={videoRef}
          autoPlay={autoPlay}
          playsInline
          muted={muted}
          style={{
            width: '100%',
            maxWidth: '100%',
            aspectRatio: '16 / 9',
            background: '#000',
            borderRadius: 8,
            display: 'block',
          }}
        />

        {/* VideoOverlay - only render when video is ready and overlay is enabled */}
        {enableOverlay && videoReady && (
          <VideoOverlay
            ref={overlayRef}
            videoRef={videoRef}
          />
        )}

        {/* Controls overlay */}
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            padding: '12px',
            background:
              'linear-gradient(to top, rgba(0,0,0,0.7) 0%, transparent 100%)',
            opacity: showControls ? 1 : 0,
            transition: 'opacity 0.3s',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderRadius: '0 0 8px 8px',
          }}
        >
          {/* Left side - Play/Pause */}
          <button
            onClick={togglePlayPause}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'white',
              cursor: 'pointer',
              padding: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 4,
              transition: 'background 0.2s',
            }}
            onMouseOver={(e) =>
              (e.currentTarget.style.background = COLORS.controlHover)
            }
            onMouseOut={(e) =>
              (e.currentTarget.style.background = 'transparent')
            }
          >
            {connectionState !== 'connected' || isPaused ? (
              <Play size={24} fill="white" />
            ) : (
              <Pause size={24} fill="white" />
            )}
          </button>

          {/* Right side - Fullscreen */}
          <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
            <button
              onClick={enterFullscreen}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'white',
                cursor: 'pointer',
                padding: 8,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: 4,
                transition: 'background 0.2s',
              }}
              onMouseOver={(e) =>
                (e.currentTarget.style.background = COLORS.controlHover)
              }
              onMouseOut={(e) =>
                (e.currentTarget.style.background = 'transparent')
              }
            >
              <Maximize size={20} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
