/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useEffect, useRef, forwardRef, useImperativeHandle } from 'react';

/**
 * Metadata for a single detected object with bounding box
 */
export interface BoundingBox {
  /** Unique identifier for this detection */
  id: string;
  /** Object class/label (e.g., "person", "chair", "robot") */
  label: string;
  /** Confidence score (0-1) */
  confidence: number;
  /** Bounding box in normalized coordinates (0-1) */
  box: {
    x: number; // left edge (0 = left side of frame)
    y: number; // top edge (0 = top of frame)
    width: number; // box width (0-1)
    height: number; // box height (0-1)
  };
  /** Optional: Distance from camera in meters */
  distance?: number;
  /** Optional: 3D position (x, y, z) in meters */
  position?: {
    x: number;
    y: number;
    z: number;
  };
}

/**
 * Metadata stream message containing detection results
 */
export interface MetadataFrame {
  /** Timestamp in milliseconds */
  timestamp: number;
  /** Frame number */
  frameId: number;
  /** Array of detected objects with bounding boxes */
  detections: BoundingBox[];
}

interface VideoOverlayProps {
  /** Reference to the video element being overlayed */
  videoRef: React.RefObject<HTMLVideoElement>;
  /** Callback when metadata frame is processed (for debugging/stats) */
  onFrameProcessed?: (fps: number) => void;
  /** Optional: custom styling for the container */
  style?: React.CSSProperties;
}

export interface VideoOverlayHandle {
  /** Send metadata to be rendered (will be called by backend data stream) */
  updateMetadata: (metadata: MetadataFrame) => void;
  /** Clear all bounding boxes */
  clear: () => void;
}

/**
 * Video overlay component that draws bounding boxes
 * directly to a canvas element
 *
 * Usage:
 * - In test mode: automatically generates a moving test bounding box
 * - In production: call updateMetadata() with real backend data
 */
const VideoOverlay = forwardRef<VideoOverlayHandle, VideoOverlayProps>(
  ({ videoRef, onFrameProcessed, style }, ref) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const metadataRef = useRef<MetadataFrame | null>(null);
    const animationFrameRef = useRef<number>();
    const fpsCounterRef = useRef({ lastTime: 0, frames: 0, fps: 0 });
    const lastRenderedTimestamp = useRef<number>(0);

    // Expose methods to parent component
    useImperativeHandle(ref, () => ({
      updateMetadata: (metadata: MetadataFrame) => {
        metadataRef.current = metadata;
      },
      clear: () => {
        metadataRef.current = null;
        lastRenderedTimestamp.current = 0;
        const canvas = canvasRef.current;
        const ctx = canvas?.getContext('2d');
        if (ctx && canvas) {
          const dpr = window.devicePixelRatio || 1;
          ctx.clearRect(0, 0, canvas.width / dpr, canvas.height / dpr);
        }
      },
    }));

    // Main render loop - OPTIMIZED: only render when data changes
    useEffect(() => {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      if (!canvas || !video) return;

      const ctx = canvas.getContext('2d', {
        alpha: true,
        desynchronized: true, // reduce latency
      });
      if (!ctx) return;

      // Update canvas size to match video
      const updateCanvasSize = () => {
        const rect = video.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;

        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        canvas.style.width = `${rect.width}px`;
        canvas.style.height = `${rect.height}px`;

        ctx.scale(dpr, dpr);
      };

      updateCanvasSize();
      const resizeObserver = new ResizeObserver(updateCanvasSize);
      resizeObserver.observe(video);

      // Rendering function with timestamp check
      const render = (currentTime: number) => {
        const metadata = metadataRef.current;

        // Only render if we have new data
        if (!metadata || metadata.timestamp === lastRenderedTimestamp.current) {
          animationFrameRef.current = requestAnimationFrame(render);
          return;
        }

        lastRenderedTimestamp.current = metadata.timestamp;

        const dpr = window.devicePixelRatio || 1;
        const displayWidth = canvas.width / dpr;
        const displayHeight = canvas.height / dpr;

        // Clear canvas
        ctx.clearRect(0, 0, displayWidth, displayHeight);

        if (!metadata.detections.length) {
          animationFrameRef.current = requestAnimationFrame(render);
          return;
        }

        // Set styles once for all detections
        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 3;
        ctx.font = 'bold 14px sans-serif';

        // Draw each bounding box
        metadata.detections.forEach((detection) => {
          const { box, label, confidence, distance } = detection;

          // Convert normalized coordinates to pixel coordinates
          const x = box.x * displayWidth;
          const y = box.y * displayHeight;
          const width = box.width * displayWidth;
          const height = box.height * displayHeight;

          // Draw bounding box
          ctx.strokeRect(x, y, width, height);

          // Draw label (confidence and distance in meters)
          const labelText = `${label} ${(confidence * 100).toFixed(0)}%`;
          const distanceText = distance ? ` | ${distance.toFixed(2)}m` : '';
          const fullText = labelText + distanceText;

          const textMetrics = ctx.measureText(fullText);
          const textHeight = 20;
          const padding = 4;

          // Background for better readability
          ctx.fillStyle = 'rgba(0, 255, 0, 0.8)';
          ctx.fillRect(
            x,
            y - textHeight - padding,
            textMetrics.width + padding * 2,
            textHeight + padding
          );

          // Draw text
          ctx.fillStyle = '#000000';
          ctx.fillText(fullText, x + padding, y - padding - 2);

        });

        // FPS Counter
        const fpsCounter = fpsCounterRef.current;
        fpsCounter.frames++;
        if (currentTime - fpsCounter.lastTime >= 1000) {
          fpsCounter.fps = fpsCounter.frames;
          fpsCounter.frames = 0;
          fpsCounter.lastTime = currentTime;
          onFrameProcessed?.(fpsCounter.fps);
        }

        animationFrameRef.current = requestAnimationFrame(render);
      };

      animationFrameRef.current = requestAnimationFrame(render);

      return () => {
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current);
        }
        resizeObserver.disconnect();
      };
    }, [videoRef, onFrameProcessed]);

    return (
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          pointerEvents: 'none',
          willChange: 'transform',
          transform: 'translateZ(0)', // GPU acceleration
          ...style,
        }}
      />
    );
  }
);

export default VideoOverlay;