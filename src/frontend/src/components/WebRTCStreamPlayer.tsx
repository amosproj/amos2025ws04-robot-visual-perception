/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useRef, useState } from 'react';
import { useWebRTCPlayer } from '../hooks/useWebRTCPlayer';
import { useAnalyzerWebSocket } from '../hooks/useAnalyzerWebSocket';
import VideoOverlay, { VideoOverlayHandle } from './VideoOverlay';
import { PlayerControls } from './PlayerControls';
import MetadataWidget, { StreamMetadata } from './MetadataWidget';

// Return Tailwind class for the status indicator dot
const getStatusDotClass = (state: string) => {
  if (state === 'connected') return 'bg-status-connected';
  if (state === 'connecting') return 'bg-status-connecting';
  if (state === 'error') return 'bg-status-error';
  return 'bg-status-idle';
};

export interface WebRTCStreamPlayerProps {
  signalingEndpoint?: string;
  analyzerEndpoint?: string;
  className?: string;
  style?: React.CSSProperties;
  muted?: boolean;
  autoPlay?: boolean;
  /** Enable VideoOverlay with bounding boxes */
  enableOverlay?: boolean;
  /** Enable metadata widget to display stream and detection info */
  enableMetadataWidget?: boolean;
  /** Compact mode for metadata widget (less details) */
  metadataCompact?: boolean;
}

/**
 * A React component that shows a remote WebRTC video stream with
 * bounding box overlays and metadata from the analyzer service.
 *
 * Props:
 * - `signalingEndpoint` : backend URL for WebRTC signaling (offer/answer)
 * - `analyzerEndpoint`  : WebSocket URL for analyzer metadata
 * - `autoPlay`          : when true, attempts to start playback automatically
 * - `muted`             : start the video muted (useful to avoid autoplay blocks)
 * - `enableOverlay`     : enable drawing bounding-box overlays from metadata
 * - `enableMetadataWidget` : show comprehensive stats widget
 * - `metadataCompact`   : use compact mode for metadata widget
 */
export default function WebRTCStreamPlayer({
  signalingEndpoint,
  analyzerEndpoint = 'ws://localhost:8001/ws',
  className,
  style,
  muted = true,
  autoPlay = false,
  enableOverlay = true,
  enableMetadataWidget = true,
  metadataCompact = false,
}: WebRTCStreamPlayerProps) {
  // WebRTC connection for video stream
  const {
    videoRef,
    connectionState,
    errorReason,
    isPaused,
    latencyMs,
    stats,
    togglePlayPause,
    disconnect: disconnectVideo,
    enterFullscreen,
  } = useWebRTCPlayer({ signalingEndpoint, autoPlay });

  // WebSocket connection for analyzer metadata
  const {
    isConnected: analyzerConnected,
    latestMetadata,
    fps: analyzerFps,
    videoInfo,
    disconnect: disconnectAnalyzer,
  } = useAnalyzerWebSocket({
    endpoint: analyzerEndpoint,
    autoConnect: true,
  });

  const overlayRef = useRef<VideoOverlayHandle | null>(null);
  const videoContainerRef = useRef<HTMLDivElement | null>(null);
  const [showControls, setShowControls] = useState(true);
  const [videoReady, setVideoReady] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showMetadata, setShowMetadata] = useState(true);
  const [renderFps, setRenderFps] = useState<number>(0);

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

  // Update overlay when new metadata arrives from analyzer
  useEffect(() => {
    if (latestMetadata && overlayRef.current) {
      overlayRef.current.updateMetadata(latestMetadata);
    }
  }, [latestMetadata]);

  // Callback for when overlay processes a frame (for FPS tracking)
  const handleFrameProcessed = (overlayFps: number) => {
    setRenderFps(overlayFps);
  };

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
    document.addEventListener(
      'webkitfullscreenchange',
      handleFullscreenChange
    );
    document.addEventListener('msfullscreenchange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
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

  // Disconnect both video and analyzer on manual disconnect
  const handleDisconnect = () => {
    disconnectVideo();
    disconnectAnalyzer();
  };

  // Compose a single status text for display
  const statusText = (() => {
    if (connectionState === 'connected') return 'Connected';
    if (connectionState === 'connecting') return 'Connecting…';
    if (connectionState === 'error') return `Error: ${errorReason}`;
    return 'Idle';
  })();

  // Build comprehensive stream metadata for widget
  const streamMetadata: StreamMetadata = {
    connectionState,
    latencyMs,
    // Prefer backend video info, fallback to client stats
    videoResolution: videoInfo
      ? { width: videoInfo.width, height: videoInfo.height }
      : stats?.videoResolution,
    renderFps,
    videoFps: videoInfo?.source_fps ?? stats?.videoFps,
    // Client-side network quality
    packetLoss: stats?.packetLoss,
    jitter: stats?.jitter,
    bitrate: stats?.bitrate,
    // Client-side video quality
    framesDropped: stats?.framesDropped,
    framesReceived: stats?.framesReceived,
    framesDecoded: stats?.framesDecoded,
  };

  return (
    <div className={`flex flex-col gap-4 ${className || ''}`} style={style}>
      {/* Status Bar */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-4">
          <span className="text-sm opacity-80 flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${getStatusDotClass(connectionState)}`}
            />
            Video: {statusText}
          </span>
          <span className="text-sm opacity-80 flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${analyzerConnected ? 'bg-status-connected' : 'bg-status-idle'}`}
            />
            Analyzer: {analyzerConnected ? 'Connected' : 'Disconnected'}
          </span>
          {latestMetadata && (
            <span className="text-sm opacity-80">
              Objects: {latestMetadata.detections.length}
            </span>
          )}
        </div>
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
            onClick={handleDisconnect}
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

      {/* Video and Metadata Container */}
      <div className="flex gap-4 items-start">
        {/* Video Container - fixed width to prevent shifting */}
        <div
          ref={videoContainerRef}
          className="relative group rounded-lg overflow-hidden bg-black aspect-video"
          style={{ width: isFullscreen ? '100%' : 'calc(100% - 21rem)' }}
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
              onFrameProcessed={handleFrameProcessed}
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
                streamMetadata={streamMetadata}
                detectionMetadata={latestMetadata}
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
              streamMetadata={streamMetadata}
              detectionMetadata={latestMetadata}
              compact={metadataCompact}
            />
          </div>
        )}
      </div>
    </div>
  );
}
