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
  /** Callback when metadata is updated (for syncing with parent components) */
  onMetadataUpdated?: (metadata: MetadataFrame) => void;
  /** Optional: custom styling for the container */
  style?: React.CSSProperties;
  /** Optional: custom class name */
  className?: string;
  /** Enable test mode with simulated moving bounding box */
  testMode?: boolean;
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
  ({ videoRef, onFrameProcessed, onMetadataUpdated, style, className, testMode = false }, ref) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const metadataRef = useRef<MetadataFrame | null>(null);
    const animationFrameRef = useRef<number>();
    const fpsCounterRef = useRef({ lastTime: 0, frames: 0, fps: 0 });

    // Expose methods to parent component
    useImperativeHandle(ref, () => ({
      updateMetadata: (metadata: MetadataFrame) => {
        metadataRef.current = metadata;
        onMetadataUpdated?.(metadata);
      },
      clear: () => {
        metadataRef.current = null;
        const canvas = canvasRef.current;
        const ctx = canvas?.getContext('2d');
        if (ctx && canvas) {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
      },
    }));

    // Generate simulated test data (moving bounding box)
    useEffect(() => {
      if (!testMode) return;

      let frameCount = 0;
      const interval = setInterval(() => {
        const time = Date.now() / 1000;

        // Create a moving test bounding box
        const x = 0.3 + Math.sin(time * 0.5) * 0.2; // oscillate x position
        const y = 0.3 + Math.cos(time * 0.7) * 0.2; // oscillate y position
        const width = 0.25 + Math.sin(time * 1.2) * 0.05; // slight size variation
        const height = 0.25 + Math.cos(time * 1.2) * 0.05;

        // Calculate dynamic 3D position based on 2D position and distance
        const distance = 1.5 + Math.sin(time * 0.3) * 0.5;
        // Map normalized 2D coordinates to 3D space
        // x: horizontal position (center of frame = 0)
        // y: vertical position (center of frame = 0, inverted because y increases downward in screen coords)
        // z: distance from camera
        const pos3D = {
          x: (x + width / 2 - 0.5) * distance * 2, // centered, scaled by distance
          y: -(y + height / 2 - 0.5) * distance * 2, // inverted and centered
          z: distance,
        };

        const testMetadata: MetadataFrame = {
          timestamp: Date.now(),
          frameId: frameCount++,
          detections: [
            {
              id: 'test-object-1',
              label: 'Test Object',
              confidence: 0.95,
              box: { x, y, width, height },
              distance,
              position: pos3D,
            },
          ],
        };

        metadataRef.current = testMetadata;
        onMetadataUpdated?.(testMetadata);
      }, 16); // ~60 fps for test data generation

      return () => clearInterval(interval);
    }, [testMode, onMetadataUpdated]);

    // Main render loop using requestAnimationFrame
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

        // Set internal resolution (accounting for device pixel ratio)
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;

        // Set display size
        canvas.style.width = `${rect.width}px`;
        canvas.style.height = `${rect.height}px`;

        // Reset transform to identity matrix before applying new scale
        // This prevents cumulative scaling that causes flickering
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.scale(dpr, dpr);
      };

      // Initial size and resize observer
      updateCanvasSize();
      const resizeObserver = new ResizeObserver(updateCanvasSize);
      resizeObserver.observe(video);

      // Rendering function
      const render = (currentTime: number) => {
        if (!canvas || !video) return;

        const dpr = window.devicePixelRatio || 1;
        const displayWidth = canvas.width / dpr;
        const displayHeight = canvas.height / dpr;

        // Clear canvas
        ctx.clearRect(0, 0, displayWidth, displayHeight);

        // Get current metadata
        const metadata = metadataRef.current;
        if (!metadata || !metadata.detections.length) {
          animationFrameRef.current = requestAnimationFrame(render);
          return;
        }

        // Draw each bounding box
        metadata.detections.forEach((detection) => {
          const { box, label, confidence, distance } = detection;

          // Convert normalized coordinates to pixel coordinates
          const x = box.x * displayWidth;
          const y = box.y * displayHeight;
          const width = box.width * displayWidth;
          const height = box.height * displayHeight;

          // Draw bounding box
          ctx.strokeStyle = '#00ff00';
          ctx.lineWidth = 3;
          ctx.strokeRect(x, y, width, height);

          // Draw label background
          const labelText = `${label} ${(confidence * 100).toFixed(0)}%`;
          const distanceText = distance ? ` | ${distance.toFixed(2)}m` : '';
          const fullText = labelText + distanceText;

          ctx.font = 'bold 14px sans-serif';
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

          // Optional: Draw center point
          ctx.fillStyle = '#00ff00';
          ctx.beginPath();
          ctx.arc(x + width / 2, y + height / 2, 4, 0, Math.PI * 2);
          ctx.fill();
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

        // Continue animation loop
        animationFrameRef.current = requestAnimationFrame(render);
      };

      // Start render loop
      animationFrameRef.current = requestAnimationFrame(render);

      // Cleanup
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
        className={`absolute top-0 left-0 pointer-events-none ${className || ''}`}
        style={style}
      />
    );
  }
);

VideoOverlay.displayName = 'VideoOverlay';

export default VideoOverlay;
