/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useRef, useEffect, useState, useMemo } from 'react';
import { useWebRTCPlayer } from './hooks/useWebRTCPlayer';
import { useAnalyzerWebSocket } from './hooks/useAnalyzerWebSocket';
import { logger } from './lib/logger';

import Header from './components/Header';
import VideoPlayer, { VideoPlayerHandle } from './components/VideoPlayer';
import UnifiedInfoPanel from './components/UnifiedInfoPanel';

function App() {
  const log = useMemo(() => logger.child({ component: 'App' }), []);
  const videoPlayerRef = useRef<VideoPlayerHandle>(null);
  const videoContainerRef = useRef<HTMLDivElement>(null);

  const [overlayFps, setOverlayFps] = useState<number>(0);
  const [selectedClasses, setSelectedClasses] = useState<Set<number>>(
    new Set()
  );
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.3);
  const autoSelectedClassesRef = useRef<Set<number>>(new Set());

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
    onBeforeDisconnect: () => {
      // Clear selections before disconnect to remove bounding boxes smoothly
      setSelectedClasses(new Set());
    },
  });

  // Filter metadata based on selected classes
  const thresholdedDetections = useMemo(() => {
    if (!latestMetadata) return [];
    return latestMetadata.detections.filter((detection) => {
      if (detection.confidence === undefined) return true;
      return detection.confidence >= confidenceThreshold;
    });
  }, [latestMetadata, confidenceThreshold]);

  const filteredMetadata = useMemo(() => {
    if (!latestMetadata) return null;

    // If no classes are selected, show nothing
    if (selectedClasses.size === 0) {
      return {
        ...latestMetadata,
        detections: [],
      };
    }

    // Otherwise, filter detections to only show selected classes above threshold
    return {
      ...latestMetadata,
      detections: thresholdedDetections.filter((detection) => {
        const classId =
          typeof detection.label === 'string'
            ? parseInt(detection.label, 10)
            : detection.label;
        return !isNaN(classId) && selectedClasses.has(classId);
      }),
    };
  }, [latestMetadata, selectedClasses, thresholdedDetections]);

  // Update overlay when new metadata arrives (only while video is connected and not paused)
  useEffect(() => {
    if (!videoPlayerRef.current) return;

    if (videoState === 'connected' && filteredMetadata && !isPaused) {
      videoPlayerRef.current.updateOverlay(filteredMetadata);
    } else {
      videoPlayerRef.current.updateOverlay(null as any);
    }
  }, [filteredMetadata, isPaused, videoState]);

  // Clear overlay when video is paused
  useEffect(() => {
    if (isPaused && videoPlayerRef.current) {
      setSelectedClasses(new Set());
      autoSelectedClassesRef.current = new Set();
    }
  }, [isPaused]);

  // Clear overlay and selections when analyzer disconnects
  useEffect(() => {
    if (!analyzerConnected) {
      // On disconnect: clear overlay and selections
      if (videoPlayerRef.current) {
        setSelectedClasses(new Set());
      }
      setSelectedClasses(new Set());
      autoSelectedClassesRef.current = new Set(); // Reset for next connection
    }
  }, [analyzerConnected]);

  // Auto-select any newly detected classes (default "select all" behavior)
  useEffect(() => {
    if (
      analyzerConnected &&
      thresholdedDetections &&
      videoState === 'connected' &&
      thresholdedDetections.length > 0
    ) {
      const newClassIds: number[] = [];

      thresholdedDetections.forEach((detection) => {
        const classId =
          typeof detection.label === 'string'
            ? parseInt(detection.label, 10)
            : detection.label;

        if (!isNaN(classId) && !autoSelectedClassesRef.current.has(classId)) {
          autoSelectedClassesRef.current.add(classId);
          newClassIds.push(classId);
        }
      });

      if (newClassIds.length > 0) {
        setSelectedClasses((prev) => {
          const updated = new Set(prev);
          newClassIds.forEach((id) => updated.add(id));
          log.info('ui.filter.auto_select', { classes: Array.from(updated) });
          return updated;
        });
      }
    }
  }, [analyzerConnected, thresholdedDetections, videoState, log]);

  // Clear overlay when video disconnects, but keep user selections
  useEffect(() => {
    if (videoState !== 'connected') {
      if (videoPlayerRef.current) {
        videoPlayerRef.current.updateOverlay(null as any);
      }
      // Allow auto-select to run again on reconnect
      autoSelectedClassesRef.current = new Set();
    }
  }, [videoState]);

  // Auto-connect to services when component mounts
  useEffect(() => {
    connectVideo();
    connectAnalyzer(); // Manual connect to analyzer
  }, [connectVideo, connectAnalyzer]);

  const handleClearOverlay = () => {
    setSelectedClasses(new Set());
    log.info('ui.overlay.cleared');
  };

  const handleSelectionChange = (nextSelection: Set<number>) => {
    // Clone to avoid mutation surprises from child components
    const cloned = new Set(nextSelection);
    setSelectedClasses(cloned);
    log.info('ui.filter.selection_changed', {
      classes: Array.from(cloned).sort(),
    });
  };

  return (
    <div className="font-sans max-w-[1200px] mx-auto p-5 bg-theme-bg-primary text-theme-text-primary min-h-screen">
      <Header
        videoState={videoState}
        latencyMs={latencyMs}
        analyzerConnected={analyzerConnected}
        analyzerFps={analyzerFps || 0}
        overlayFps={overlayFps || 0}
        objectCount={filteredMetadata?.detections.length || 0}
      />
      <div className="grid gap-6 lg:grid-cols-[340px_minmax(0,1fr)] items-start">
        <UnifiedInfoPanel
          videoState={videoState}
          analyzerConnected={analyzerConnected}
          onConnectVideo={connectVideo}
          onDisconnectVideo={disconnectVideo}
          onConnectAnalyzer={connectAnalyzer}
          onDisconnectAnalyzer={disconnectAnalyzer}
          onClearOverlay={handleClearOverlay}
          detections={thresholdedDetections}
          selectedClasses={selectedClasses}
          onSelectionChange={handleSelectionChange}
          confidenceThreshold={confidenceThreshold}
          onConfidenceThresholdChange={setConfidenceThreshold}
          isVideoConnected={videoState === 'connected'}
          streamMetadata={stats}
          detectionMetadata={latestMetadata}
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
      </div>
    </div>
  );
}

export default App;
