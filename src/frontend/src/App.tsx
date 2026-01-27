/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useRef, useEffect, useState, useMemo, useLayoutEffect } from 'react';
import { useWebRTCPlayer } from './hooks/useWebRTCPlayer';
import { useAnalyzerWebSocket } from './hooks/useAnalyzerWebSocket';
import { useOrchestrator } from './hooks/useOrchestrator';
import { logger } from './lib/logger';
import { useI18n } from './i18n';
import { clamp } from './lib/mathUtils';
import { getClassId } from './lib/overlayUtils';

import Header from './components/Header';
import VideoPlayer, { VideoPlayerHandle } from './components/VideoPlayer';
import { GameOverlay } from './components/ui/GameOverlay';
import { ObjectFilterSection } from './components/ObjectFilter';
import StreamInfo from './components/StreamInfo';
import DetectionInfo from './components/DetectionInfo';

function App() {
  const log = useMemo(() => logger.child({ component: 'App' }), []);
  const { t } = useI18n();
  const videoPlayerRef = useRef<VideoPlayerHandle>(null);
  const videoContainerRef = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLDivElement | null>(null);

  const [overlayFps, setOverlayFps] = useState<number>(0);
  const [showGroupedDetections, setShowGroupedDetections] =
    useState<boolean>(false);
  const [selectedClasses, setSelectedClasses] = useState<Set<number>>(
    new Set()
  );
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.3);
  const autoSelectedClassesRef = useRef<Set<number>>(new Set());
  const [videoZoom, setVideoZoom] = useState(1);

  // Service discovery from orchestrator
  const orchestratorUrl = import.meta.env.VITE_ORCHESTRATOR_URL || 'http://localhost:8002';
  const {
    services,
    assignAnalyzer,
  } = useOrchestrator({
    orchestratorUrl,
  });

  // Selected streamer/analyzer
  const [selectedStreamerUrl, setSelectedStreamerUrl] = useState<string | null>(null);
  const [selectedAnalyzerUrl, setSelectedAnalyzerUrl] = useState<string | null>(null);

  // Auto-select first streamer on startup or when streamer list changes
  useEffect(() => {
    if (services.streamer.length > 0 && !selectedStreamerUrl) {
      const firstStreamer = services.streamer[0].url;
      setSelectedStreamerUrl(firstStreamer);
      log.info('app.streamer_selected', { streamer: firstStreamer });
    }
  }, [services.streamer, selectedStreamerUrl, log]);

  // Auto-request analyzer assignment when streamer is selected
  useEffect(() => {
    if (selectedStreamerUrl && !selectedAnalyzerUrl) {
      assignAnalyzer(selectedStreamerUrl).then((result) => {
        if (result?.analyzerUrl) {
          setSelectedAnalyzerUrl(result.analyzerUrl);
          log.info('app.analyzer_assigned', { analyzer: result.analyzerUrl });
        }
      });
    }
  }, [selectedStreamerUrl, selectedAnalyzerUrl, assignAnalyzer, log]);

  useLayoutEffect(() => {
    const header = headerRef.current;
    if (!header) return;

    const root = document.documentElement;
    const updateHeaderHeight = () => {
      const height = header.getBoundingClientRect().height;
      root.style.setProperty('--ui-header-height', `${Math.ceil(height)}px`);
    };

    updateHeaderHeight();

    const resizeObserver = new ResizeObserver(updateHeaderHeight);
    resizeObserver.observe(header);

    window.addEventListener('resize', updateHeaderHeight);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener('resize', updateHeaderHeight);
    };
  }, []);

  useEffect(() => {
    const handleWheel = (event: WheelEvent) => {
      if (!(event.ctrlKey || event.metaKey)) return;
      event.preventDefault();

      const direction = Math.sign(event.deltaY);
      if (!direction) return;

      const step = direction > 0 ? -0.1 : 0.1;
      setVideoZoom((prev) => clamp(prev + step, 1, 3));
    };

    window.addEventListener('wheel', handleWheel, { passive: false });
    return () => {
      window.removeEventListener('wheel', handleWheel);
    };
  }, []);

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
    signalingEndpoint: selectedStreamerUrl || 'http://localhost:8000',
    autoPlay: !!selectedStreamerUrl,
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
    endpoint: selectedAnalyzerUrl ? `ws://${selectedAnalyzerUrl.replace(/^https?:\/\//, '')}/ws` : '',
    autoConnect: !!selectedAnalyzerUrl,
    onBeforeDisconnect: () => {
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
        const classId = getClassId(detection.label);
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
        const classId = getClassId(detection.label);

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
    if (selectedStreamerUrl) {
      connectVideo();
    }
    if (selectedAnalyzerUrl) {
      connectAnalyzer();
    }
  }, [selectedStreamerUrl, selectedAnalyzerUrl, connectVideo, connectAnalyzer]);

  const [showPanel, setShowPanel] = useState(true);

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
    <div className="font-sans bg-theme-bg-primary text-theme-text-primary min-h-screen">
      <Header
        ref={headerRef}
        minimal
        videoState={videoState}
        analyzerConnected={analyzerConnected}
        onConnectVideo={connectVideo}
        onDisconnectVideo={disconnectVideo}
        onConnectAnalyzer={connectAnalyzer}
        onDisconnectAnalyzer={disconnectAnalyzer}
        showPanel={showPanel}
        onTogglePanel={() => setShowPanel(!showPanel)}
      />

      <GameOverlay
        showPanel={showPanel}
        filterPanel={
          <ObjectFilterSection
            detections={thresholdedDetections}
            selectedClasses={selectedClasses}
            onSelectionChange={handleSelectionChange}
            confidenceThreshold={confidenceThreshold}
            onConfidenceThresholdChange={setConfidenceThreshold}
            isAnalyzerConnected={analyzerConnected}
            isVideoConnected={videoState === 'connected'}
            onClearAll={handleClearOverlay}
            variant="section"
          />
        }
        streamInfoPanel={
          <StreamInfo
            {...(stats ?? {})}
            statusPanelProps={{
              videoState,
              latencyMs,
              analyzerFps: analyzerFps || 0,
              overlayFps,
              objectCount: filteredMetadata?.detections.length || 0,
            }}
            variant="section"
          />
        }
        detectionPanel={
          latestMetadata?.detections && latestMetadata.detections.length > 0 ? (
            <div className="space-y-3">
              <div className="flex justify-end">
                <button
                  onClick={() =>
                    setShowGroupedDetections(!showGroupedDetections)
                  }
                  className="text-xs px-3 py-1.5 bg-theme-bg-tertiary hover:bg-theme-bg-hover text-theme-accent rounded border border-theme-border transition-colors"
                >
                  {showGroupedDetections
                    ? t('metadataShowDetails')
                    : t('metadataGroupByType')}
                </button>
              </div>
              <DetectionInfo
                detections={latestMetadata.detections}
                showGrouped={showGroupedDetections}
                variant="section"
              />
            </div>
          ) : undefined
        }
      >
        {/* Main video player - fullscreen background */}
        <div className="fixed inset-0 pt-[var(--ui-header-height)] pb-[var(--ui-header-height)]">
          <VideoPlayer
            ref={videoPlayerRef}
            videoRef={videoRef}
            containerRef={videoContainerRef}
            videoState={videoState}
            isPaused={isPaused}
            zoomLevel={videoZoom}
            onTogglePlay={togglePlayPause}
            onFullscreen={enterFullscreen}
            onOverlayFpsUpdate={setOverlayFps}
          />
        </div>
      </GameOverlay>
    </div>
  );
}

export default App;
