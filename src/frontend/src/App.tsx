/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useRef, useEffect, useState } from 'react';
import { useWebRTCPlayer } from './hooks/useWebRTCPlayer';
import { useAnalyzerWebSocket } from './hooks/useAnalyzerWebSocket';
import VideoOverlay, { VideoOverlayHandle } from './components/VideoOverlay';
import './App.css';

function App() {
  const overlayRef = useRef<VideoOverlayHandle>(null);
  
  const [overlayFps, setOverlayFps] = useState<number>(0);

  // WebRTC connection to webcam service (for raw video)
  const { 
    videoRef,
    connectionState: videoState, 
    latencyMs,
    connect: connectVideo,
    disconnect: disconnectVideo
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
    disconnect: disconnectAnalyzer
  } = useAnalyzerWebSocket({
    endpoint: 'ws://localhost:8001/ws', // Analyzer service
    autoConnect: true,
  });

  // Update overlay when new metadata arrives
  useEffect(() => {
    if (latestMetadata && overlayRef.current) {
      overlayRef.current.updateMetadata(latestMetadata);
    }
  }, [latestMetadata]);

  // Auto-connect to video when component mounts
  useEffect(() => {
    connectVideo();
  }, [connectVideo]);

  const handleClearOverlay = () => {
    overlayRef.current?.clear();
  };

  return (
    <div className="app">
      <div className="header">
        <h1>Robot Visual Perception</h1>
        <div className="status-bar">
          <div className={`status-item ${videoState}`}>
            <span className="status-label">Video:</span>
            <span className="status-value">{videoState}</span>
            {latencyMs && <span className="status-detail">({latencyMs}ms)</span>}
          </div>
          
          <div className={`status-item ${analyzerConnected ? 'connected' : 'disconnected'}`}>
            <span className="status-label">Analyzer:</span>
            <span className="status-value">{analyzerConnected ? 'Connected' : 'Disconnected'}</span>
            {analyzerFps && analyzerFps > 0 && <span className="status-detail">({analyzerFps} FPS)</span>}
          </div>
          
          <div className="status-item">
            <span className="status-label">Overlay:</span>
            <span className="status-value">{overlayFps} FPS</span>
          </div>
          
          <div className="status-item">
            <span className="status-label">Objects:</span>
            <span className="status-value">{latestMetadata?.detections.length || 0}</span>
          </div>
        </div>
      </div>

      <div className="controls">
        <button 
          onClick={videoState === 'connected' ? disconnectVideo : connectVideo}
          className={`btn ${videoState === 'connected' ? 'btn-danger' : 'btn-primary'}`}
          disabled={videoState === 'connecting'}
        >
          {videoState === 'connecting' ? 'Connecting...' : 
           videoState === 'connected' ? 'Disconnect Video' : 'Connect Video'}
        </button>
        
        <button 
          onClick={analyzerConnected ? disconnectAnalyzer : connectAnalyzer}
          className={`btn ${analyzerConnected ? 'btn-danger' : 'btn-primary'}`}
        >
          {analyzerConnected ? 'Disconnect Analyzer' : 'Connect Analyzer'}
        </button>
        
        <button onClick={handleClearOverlay} className="btn btn-secondary">
          Clear Overlay
        </button>
      </div>

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
      </div>

      {latestMetadata && latestMetadata.detections.length > 0 && (
        <div className="detection-info">
          <h3>Latest Detections ({latestMetadata.detections.length})</h3>
          <div className="detection-list">
            {latestMetadata.detections.map((detection) => (
              <div key={detection.id} className="detection-item">
                <span className="detection-label">{detection.label}</span>
                <span className="detection-confidence">
                  {(detection.confidence * 100).toFixed(1)}%
                </span>
                {detection.distance && (
                  <span className="detection-distance">
                    {detection.distance.toFixed(2)}m
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}

export default App;