/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useRef, useEffect, useState } from 'react';
import { useWebRTCPlayer } from './hooks/useWebRTCPlayer';
import { useAnalyzerWebSocket } from './hooks/useAnalyzerWebSocket';

import Header from './components/Header';
import ConnectionControls from './components/ConnectionControls';
import VideoPlayer, { VideoPlayerHandle } from './components/VideoPlayer';
import MetadataWidget from './components/MetadataWidget';

function App() {
  const videoPlayerRef = useRef<VideoPlayerHandle>(null);
  const videoContainerRef = useRef<HTMLDivElement>(null);

  const [overlayFps, setOverlayFps] = useState<number>(0);
  const [isMetadataWidgetOpen, setIsMetadataWidgetOpen] = useState(true);

  // WebRTC connection to webcam service (for raw video)
  const {
    videoRef,
    connectionState: videoState,
    latencyMs,
    isPaused,
    stats,
    connect: connectVideo,
    disconnect: disconnectVideo,
    togglePlayPause,
    enterFullscreen,
  } = useWebRTCPlayer({
    signalingEndpoint: 'http://localhost:8000', // Webcam service
    autoPlay: true,
    containerRef: videoContainerRef,
  });

  // WebSocket connection to analyzer service (for metadata)
  const {
    isConnected: analyzerConnected,
    latestMetadata,
    fps: analyzerFps,
    connect: connectAnalyzer,
    disconnect: disconnectAnalyzer,
  } = useAnalyzerWebSocket({
    endpoint: 'ws://localhost:8001/ws', // Analyzer service
    autoConnect: false, // Manual control for proper disconnect
  });

  // Update overlay when new metadata arrives (but not when video is paused)
  useEffect(() => {
    if (latestMetadata && videoPlayerRef.current && !isPaused) {
      videoPlayerRef.current.updateOverlay(latestMetadata);
    }
  }, [latestMetadata, isPaused]);

  // Clear overlay when video is paused
  useEffect(() => {
    if (isPaused && videoPlayerRef.current) {
      videoPlayerRef.current.clearOverlay();
    }
  }, [isPaused]);

  // Auto-connect to services when component mounts
  useEffect(() => {
    connectVideo();
    connectAnalyzer(); // Manual connect to analyzer
  }, [connectVideo, connectAnalyzer]);

  const handleClearOverlay = () => {
    videoPlayerRef.current?.clearOverlay();
  };

  return (
    <div className="font-sans max-w-[1200px] mx-auto p-5 bg-[#1a1a1a] text-[#e0e0e0] min-h-screen">
      <Header
        videoState={videoState}
        latencyMs={latencyMs}
        analyzerConnected={analyzerConnected}
        analyzerFps={analyzerFps || 0}
        overlayFps={overlayFps || 0}
        objectCount={latestMetadata?.detections.length || 0}
      />
      <ConnectionControls
        videoState={videoState}
        analyzerConnected={analyzerConnected}
        onConnectVideo={connectVideo}
        onDisconnectVideo={disconnectVideo}
        onConnectAnalyzer={connectAnalyzer}
        onDisconnectAnalyzer={disconnectAnalyzer}
        onClearOverlay={handleClearOverlay}
      />
      <VideoPlayer
        ref={videoPlayerRef}
        videoRef={videoRef}
        containerRef={videoContainerRef}
        videoState={videoState}
        isPaused={isPaused}
        onTogglePlay={togglePlayPause}
        onFullscreen={enterFullscreen}
        onOverlayFpsUpdate={setOverlayFps}
      />

      <MetadataWidget
        streamMetadata={stats}
        detectionMetadata={latestMetadata}
        defaultGrouped={false}
        isOpen={isMetadataWidgetOpen}
        onToggle={() => setIsMetadataWidgetOpen(!isMetadataWidgetOpen)}
      />
    </div>
  );
}

export default App;
