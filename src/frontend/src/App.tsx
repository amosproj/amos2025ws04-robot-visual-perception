/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useRef, useEffect, useState } from 'react';
import { useWebRTCPlayer } from './hooks/useWebRTCPlayer';
import { useAnalyzerWebSocket } from './hooks/useAnalyzerWebSocket';
import VideoOverlay, { VideoOverlayHandle } from './components/video/VideoOverlay';
import './App.css';
import Header from './components/Header';
import ConnectionControls from './components/ConnectionControls';
import DetectionInfo from './components/DetectionInfo';
import { PlayerControls } from './components/video/PlayerControls';

function App() {
  const overlayRef = useRef<VideoOverlayHandle>(null);

  const [overlayFps, setOverlayFps] = useState<number>(0);

  // WebRTC connection to webcam service (for raw video)
  const {
    videoRef,
    connectionState: videoState,
    latencyMs,
    connect: connectVideo,
    disconnect: disconnectVideo,
  } = useWebRTCPlayer({
    signalingEndpoint: 'http://localhost:8000', // Webcam service
    autoPlay: true,
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

  // Update overlay when new metadata arrives
  useEffect(() => {
    if (latestMetadata && overlayRef.current) {
      overlayRef.current.updateMetadata(latestMetadata);
    }
  }, [latestMetadata]);

  // Auto-connect to services when component mounts
  useEffect(() => {
    connectVideo();
    connectAnalyzer(); // Manual connect to analyzer
  }, [connectVideo, connectAnalyzer]);

  const handleClearOverlay = () => {
    overlayRef.current?.clear();
  };

  return (
    <div className="app">
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
      <div className="video-container">
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
          onFrameProcessed={setOverlayFps}
        />
        <PlayerControls 
          isPlaying={videoState === 'connected'}
        />
      </div>

      {latestMetadata && latestMetadata.detections.length > 0 && (
        <DetectionInfo
          detections={latestMetadata.detections}
        />
      )}
    </div>
  );
}

export default App;
