/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useRef, useEffect, useState, useMemo } from 'react';
import { useWebRTCPlayer } from './hooks/useWebRTCPlayer';
import { useAnalyzerWebSocket } from './hooks/useAnalyzerWebSocket';

import Header from './components/Header';
import ConnectionControls from './components/ConnectionControls';
import VideoPlayer, { VideoPlayerHandle } from './components/VideoPlayer';
import MetadataWidget from './components/MetadataWidget';
import ObjectFilter from './components/ObjectFilter';

function App() {
  const videoPlayerRef = useRef<VideoPlayerHandle>(null);
  const videoContainerRef = useRef<HTMLDivElement>(null);

  const [overlayFps, setOverlayFps] = useState<number>(0);
  const [isMetadataWidgetOpen, setIsMetadataWidgetOpen] = useState(true);
  const [isObjectFilterOpen, setIsObjectFilterOpen] = useState(true);
  const [selectedClasses, setSelectedClasses] = useState<Set<number>>(
    new Set()
  );

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

  // Filter metadata based on selected classes
  const filteredMetadata = useMemo(() => {
    if (!latestMetadata) return null;

    // If no classes are selected, show nothing
    if (selectedClasses.size === 0) {
      return {
        ...latestMetadata,
        detections: [],
      };
    }

    // Otherwise, filter detections to only show selected classes
    return {
      ...latestMetadata,
      detections: latestMetadata.detections.filter((detection) => {
        const classId =
          typeof detection.label === 'string'
            ? parseInt(detection.label, 10)
            : detection.label;
        return !isNaN(classId) && selectedClasses.has(classId);
      }),
    };
  }, [latestMetadata, selectedClasses]);

  // Update overlay when new metadata arrives (but not when video is paused)
  useEffect(() => {
    if (filteredMetadata && videoPlayerRef.current && !isPaused) {
      videoPlayerRef.current.updateOverlay(filteredMetadata);
    }
  }, [filteredMetadata, isPaused]);

  // Auto-connect to services when component mounts
  useEffect(() => {
    connectVideo();
    connectAnalyzer(); // Manual connect to analyzer
  }, [connectVideo, connectAnalyzer]);

  const handleClearOverlay = () => {
    setSelectedClasses(new Set());
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
      <ObjectFilter
        detections={latestMetadata?.detections || []}
        selectedClasses={selectedClasses}
        onSelectionChange={setSelectedClasses}
        isOpen={isObjectFilterOpen}
        onToggle={() => setIsObjectFilterOpen(!isObjectFilterOpen)}
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
        metadataWidget={
          <MetadataWidget
            streamMetadata={stats}
            detectionMetadata={latestMetadata}
            defaultGrouped={false}
            isOpen={isMetadataWidgetOpen}
            onToggle={() => setIsMetadataWidgetOpen(!isMetadataWidgetOpen)}
          />
        }
      />
    </div>
  );
}

export default App;
