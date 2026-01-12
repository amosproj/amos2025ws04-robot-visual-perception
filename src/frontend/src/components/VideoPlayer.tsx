/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import {
  useRef,
  useState,
  useEffect,
  useCallback,
  RefObject,
  forwardRef,
  useImperativeHandle,
  ReactNode,
} from 'react';
import VideoOverlay, { VideoOverlayHandle } from './video/VideoOverlay';
import { PlayerControls } from './video/PlayerControls';
import { getCocoLabel } from '../constants/cocoLabels';
import { useI18n } from '../i18n';

export interface VideoPlayerProps {
  /** Reference to the video element */
  videoRef: RefObject<HTMLVideoElement>;
  /** Reference to the video container element (for fullscreen) */
  containerRef: RefObject<HTMLDivElement>;
  /** Current video connection state */
  videoState: string;
  /** Whether video is paused */
  isPaused: boolean;
  /** Toggle play/pause function */
  onTogglePlay: () => void;
  /** Enter fullscreen function */
  onFullscreen: () => void;
  /** Callback for overlay FPS updates */
  onOverlayFpsUpdate: (fps: number) => void;
  /** Optional metadata widget to display in fullscreen */
  metadataWidget?: ReactNode;
}

export interface VideoPlayerHandle {
  /** Update overlay with metadata */
  updateOverlay: (metadata: any) => void;
}

/**
 * Video player component that combines video element, overlay, and player controls
 */
const VideoPlayer = forwardRef<VideoPlayerHandle, VideoPlayerProps>(
  (
    {
      videoRef,
      containerRef,
      videoState,
      isPaused,
      onTogglePlay,
      onFullscreen,
      onOverlayFpsUpdate,
      metadataWidget,
    },
    ref
  ) => {
    const overlayRef = useRef<VideoOverlayHandle>(null);
    const displayCanvasRef = useRef<HTMLCanvasElement>(null);
    const [showControls, setShowControls] = useState(false);
    const [isFullscreen, setIsFullscreen] = useState(false);
  
    // frame synchronization state
    const metadataBufferRef = useRef<Map<number, any>>(new Map()); // frameId -> metadata
    const sequenceNumberRef = useRef<number>(0); // local frame counter
    const currentVideoFrameRef = useRef<{ imageData: ImageData | null; sequenceNumber: number }>({ imageData: null, sequenceNumber: -1 });
    const scheduleNextFrameRef = useRef<(() => void) | null>(null);
    const { language, t } = useI18n();
    const unknownLabel = useCallback(
      (value: string | number) => t('labelUnknown', { id: value }),
      [t]
    );
    const labelResolver = useCallback(
      (label: string | number) =>
        getCocoLabel(label, language, { unknownLabel }),
      [language, unknownLabel]
    );

    // Expose methods via ref
    useImperativeHandle(ref, () => ({
      updateOverlay: (metadata: any) => {
        const tsMs = Number(metadata?.timestamp);
        if (!Number.isFinite(tsMs)) {
          console.warn('[VideoPlayer] Dropping metadata without valid timestamp:', metadata);
          return;
        }

        const frameId = metadata.frameId;
        if (frameId === undefined) {
          console.warn('[VideoPlayer] Metadata without frameId:', metadata);
          return;
        }

        // Store metadata by backend frameId
        metadataBufferRef.current.set(frameId, metadata);

        // Keep only last 30 metadata entries
        if (metadataBufferRef.current.size > 30) {
          const sortedKeys = Array.from(metadataBufferRef.current.keys()).sort((a, b) => a - b);
          const toDelete = sortedKeys.slice(0, sortedKeys.length - 30);
          toDelete.forEach(k => metadataBufferRef.current.delete(k));
        }

        console.log('[VideoPlayer] Metadata received', { 
          frameId,
          bufferSize: metadataBufferRef.current.size,
          detectionsCount: metadata.detections?.length || 0
        });

        // Trigger next frame processing if we're waiting for metadata
        if (scheduleNextFrameRef.current) {
          scheduleNextFrameRef.current();
        }
      },
    }));

    // Listen for fullscreen changes to update state and trigger overlay resize
    useEffect(() => {
      const handleFullscreenChange = () => {
        const doc = document as any;
        const isNowFullscreen = !!(
          doc.fullscreenElement ||
          doc.webkitFullscreenElement ||
          doc.msFullscreenElement
        );
        setIsFullscreen(isNowFullscreen);
      };

      document.addEventListener('fullscreenchange', handleFullscreenChange);
      document.addEventListener(
        'webkitfullscreenchange',
        handleFullscreenChange
      );
      document.addEventListener('msfullscreenchange', handleFullscreenChange);

      return () => {
        document.removeEventListener(
          'fullscreenchange',
          handleFullscreenChange
        );
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

    // Frame-by-frame sync with metadata
    useEffect(() => {
      const video = videoRef.current;
      const canvas = displayCanvasRef.current;
      if (!video || !canvas) return;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      let rvfcHandle: number | undefined;

      const processVideoFrame = (_now: number, _frameMetadata: any) => {
        // Increment sequence number for each frame
        sequenceNumberRef.current++;
        const sequenceNumber = sequenceNumberRef.current;

        console.log('[VideoPlayer] Video frame received', { 
          sequenceNumber,
          slotFree: currentVideoFrameRef.current.imageData === null
        });

        // Step 1: Capture current video frame and store it with its sequence number (only if slot is free)
        if (currentVideoFrameRef.current.imageData === null && video.videoWidth && video.videoHeight) {
          // Create temporary canvas to capture current video frame
          const tempCanvas = document.createElement('canvas');
          tempCanvas.width = video.videoWidth;
          tempCanvas.height = video.videoHeight;
          const tempCtx = tempCanvas.getContext('2d');

          if (tempCtx) {
            // Draw current video frame to temp canvas
            tempCtx.drawImage(video, 0, 0, tempCanvas.width, tempCanvas.height);

            // Store the frame data with its sequence number
            const imageData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
            currentVideoFrameRef.current = {
              imageData,
              sequenceNumber
            };

            console.log('[VideoPlayer] Video frame captured', {
              sequenceNumber,
              videoSize: `${video.videoWidth}x${video.videoHeight}`,
              metadataBufferSize: metadataBufferRef.current.size
            });
          }
        }

        // Step 2: Check if we have matching metadata for the stored frame
        const storedFrame = currentVideoFrameRef.current;
        if (storedFrame.imageData && storedFrame.sequenceNumber >= 0) {
          // Find metadata with frameId matching or close to sequence number
          const availableFrameIds = Array.from(metadataBufferRef.current.keys()).sort((a, b) => a - b);
          const matchingFrameId = availableFrameIds.find(id => id >= storedFrame.sequenceNumber);

          if (matchingFrameId !== undefined) {
            const metadata = metadataBufferRef.current.get(matchingFrameId)!;

            // Step 3: Render the stored frame with matching metadata
            canvas.width = storedFrame.imageData.width;
            canvas.height = storedFrame.imageData.height;
            ctx.putImageData(storedFrame.imageData, 0, 0);

            // Update overlay with metadata AFTER drawing the frame
            overlayRef.current?.updateMetadata(metadata);

            console.log('[VideoPlayer] Frame rendered', {
              storedSequenceNumber: storedFrame.sequenceNumber,
              metadataFrameId: matchingFrameId,
              videoSize: `${canvas.width}x${canvas.height}`,
              detectionsCount: metadata.detections?.length || 0,
              backendTimestamp: metadata.timestamp
            });

            // Remove used metadata
            metadataBufferRef.current.delete(matchingFrameId);

            // Reset stored frame so we capture a new one next time
            currentVideoFrameRef.current = { imageData: null, sequenceNumber: -1 };

            // Continue with next frame
            scheduleRvfC();
          } else {
            // No matching metadata yet - DON'T schedule next callback, wait for metadata
            if (sequenceNumber % 30 === 0) { // Log every 30 frames only
              console.log('[VideoPlayer] Waiting for metadata', {
                storedSequenceNumber: storedFrame.sequenceNumber,
                currentSequenceNumber: sequenceNumber,
                availableMetadata: availableFrameIds,
                bufferSize: metadataBufferRef.current.size
              });
            }
            // Don't call scheduleRvfC() - we'll be triggered by metadata arrival
          }
        }
      };

      const scheduleRvfC = () => {
        if (typeof video.requestVideoFrameCallback !== 'function') {
          console.warn('[VideoPlayer] requestVideoFrameCallback not supported');
          return;
        }
        rvfcHandle = video.requestVideoFrameCallback((now: number, metadata: any) => {
          processVideoFrame(now, metadata);
          // Note: scheduleRvfC is now called from processVideoFrame only after successful render
        });
      };

      // Expose schedule function so metadata arrival can trigger it
      scheduleNextFrameRef.current = scheduleRvfC;

      // Update canvas size to match video and fullscreen state
      const updateCanvasSize = () => {
        if (!video.videoWidth || !video.videoHeight) return;

        const aspectRatio = video.videoWidth / video.videoHeight;
        const container = containerRef.current;

        if (isFullscreen && container) {
          // Fullscreen: fit canvas to container while maintaining aspect ratio
          const containerWidth = container.clientWidth;
          const containerHeight = container.clientHeight;
          const containerAspect = containerWidth / containerHeight;

          let displayWidth: number;
          let displayHeight: number;

          if (containerAspect > aspectRatio) {
            // Container is wider - fit to height
            displayHeight = containerHeight;
            displayWidth = displayHeight * aspectRatio;
          } else {
            // Container is taller - fit to width
            displayWidth = containerWidth;
            displayHeight = displayWidth / aspectRatio;
          }

          canvas.style.width = `${displayWidth}px`;
          canvas.style.height = `${displayHeight}px`;
        } else {
          // Normal mode: use max-width constraint
          const maxWidth = 640;
          let displayWidth = video.videoWidth;
          let displayHeight = video.videoHeight;

          if (displayWidth > maxWidth) {
            displayWidth = maxWidth;
            displayHeight = maxWidth / aspectRatio;
          }

          canvas.style.width = `${displayWidth}px`;
          canvas.style.height = `${displayHeight}px`;
        }

        // Set canvas internal resolution (always match video resolution)
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        console.log('[VideoPlayer] Canvas size updated', {
          videoResolution: `${video.videoWidth}x${video.videoHeight}`,
          displaySize: `${canvas.style.width}x${canvas.style.height}`,
          isFullscreen
        });
      };

      video.addEventListener('loadedmetadata', updateCanvasSize);
      video.addEventListener('play', scheduleRvfC);
      
      // Watch for container size changes (important for fullscreen)
      const container = containerRef.current;
      let resizeObserver: ResizeObserver | null = null;
      if (container) {
        resizeObserver = new ResizeObserver(() => {
          updateCanvasSize();
        });
        resizeObserver.observe(container);
      }
      
      // Update canvas size when fullscreen changes
      updateCanvasSize();
      scheduleRvfC();

      return () => {
        if (rvfcHandle !== undefined && typeof video.cancelVideoFrameCallback === 'function') {
          video.cancelVideoFrameCallback(rvfcHandle);
        }
        video.removeEventListener('loadedmetadata', updateCanvasSize);
        video.removeEventListener('play', scheduleRvfC);
        if (resizeObserver) {
          resizeObserver.disconnect();
        }
      };
    }, [videoRef, containerRef, isFullscreen]);


    return (
      <div
        ref={containerRef}
        className={`relative flex justify-center ${
          isFullscreen ? 'w-full h-full items-center bg-black mb-0' : 'mb-8'
        }`}
        onMouseEnter={() => setShowControls(true)}
        onMouseLeave={() => setShowControls(false)}
      >
        {/* Hidden video element for playback */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="hidden"
        />

        <canvas
          ref={displayCanvasRef}
          className={`block bg-black ${
            isFullscreen
              ? 'w-full h-full object-contain'
              : 'max-w-full w-[640px] h-auto rounded-xl shadow-[0_4px_20px_rgba(0,0,0,0.15)]'
          }`}
        />

        <VideoOverlay
          ref={overlayRef}
          videoRef={videoRef}
          displayCanvasRef={displayCanvasRef}
          isPaused={isPaused}
          onFrameProcessed={onOverlayFpsUpdate}
          labelResolver={labelResolver}
        />

        <PlayerControls
          isPlaying={videoState === 'connected' && !isPaused}
          showControls={showControls}
          onTogglePlay={onTogglePlay}
          onFullscreen={onFullscreen}
        />

        {/* Render metadata widget inside container for fullscreen support */}
        {metadataWidget}
      </div>
    );
  }
);

VideoPlayer.displayName = 'VideoPlayer';

export default VideoPlayer;
