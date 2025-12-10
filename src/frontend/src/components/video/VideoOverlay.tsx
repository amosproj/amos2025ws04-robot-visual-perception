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
  position: {
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
  /** Whether the video is currently paused */
  isPaused?: boolean;
  /** Callback when metadata frame is processed (for debugging/stats) */
  onFrameProcessed?: (fps: number) => void;
  /** Optional: custom styling for the container */
  style?: React.CSSProperties;
}

export interface VideoOverlayHandle {
  /** Send metadata to be rendered (will be called by backend data stream) */
  updateMetadata: (metadata: MetadataFrame) => void;
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
  ({ videoRef, isPaused, onFrameProcessed, style }, ref) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const metadataRef = useRef<MetadataFrame | null>(null);
    const animationFrameRef = useRef<number>();
    const fpsCounterRef = useRef({ lastTime: 0, frames: 0, fps: 0 });
    const lastRenderedTimestamp = useRef<number>(0);
    const lastCanvasStateRef = useRef({
      width: 0,
      height: 0,
      offsetX: 0,
      offsetY: 0,
      dpr: 1,
    });

    // Expose methods to parent component
    useImperativeHandle(ref, () => ({
      updateMetadata: (metadata: MetadataFrame) => {
        metadataRef.current = metadata;
      },
    }));

    // Main render loop
    useEffect(() => {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      if (!canvas || !video) return;

      const ctx = canvas.getContext('2d', {
        alpha: true,
        desynchronized: true,
      });
      if (!ctx) return;

      // Make canvas exactly match video element position and size
      const updateCanvasSize = () => {
        if (video.videoWidth === 0 || video.videoHeight === 0) return;

        const videoRect = video.getBoundingClientRect();
        const containerRect = video.parentElement?.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;

        // Stabilize against subpixel jitter (round to avoid constant resizes)
        const displayWidth = Math.round(videoRect.width);
        const displayHeight = Math.round(videoRect.height);
        const offsetX = containerRect
          ? Math.round(videoRect.left - containerRect.left)
          : 0;
        const offsetY = containerRect
          ? Math.round(videoRect.top - containerRect.top)
          : 0;

        const scaledWidth = Math.max(1, Math.round(displayWidth * dpr));
        const scaledHeight = Math.max(1, Math.round(displayHeight * dpr));

        const last = lastCanvasStateRef.current;
        if (
          last.width === scaledWidth &&
          last.height === scaledHeight &&
          last.offsetX === offsetX &&
          last.offsetY === offsetY &&
          last.dpr === dpr
        ) {
          return;
        }
        lastCanvasStateRef.current = {
          width: scaledWidth,
          height: scaledHeight,
          offsetX,
          offsetY,
          dpr,
        };

        canvas.width = scaledWidth;
        canvas.height = scaledHeight;
        canvas.style.width = `${displayWidth}px`;
        canvas.style.height = `${displayHeight}px`;

        canvas.style.position = 'absolute';
        canvas.style.top = `${offsetY}px`;
        canvas.style.left = `${offsetX}px`;
        canvas.style.zIndex = '10';

        // Map drawing coordinates to CSS pixels for crisp lines on HiDPI
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      };

      // Update canvas on video load or resize
      video.addEventListener('loadedmetadata', updateCanvasSize);

      // Watch for any changes to video element or container
      const resizeObserver = new ResizeObserver(updateCanvasSize);
      resizeObserver.observe(video);
      if (video.parentElement) {
        resizeObserver.observe(video.parentElement);
      }

      // Also listen for window resize (which can affect container layout)
      window.addEventListener('resize', updateCanvasSize);

      updateCanvasSize();

      const render = (currentTime: number) => {
        // Update canvas position regularly to handle dynamic layout changes
        updateCanvasSize();

        const dpr = lastCanvasStateRef.current.dpr || 1;
        const canvasWidth = canvas.width / dpr;
        const canvasHeight = canvas.height / dpr;

        const metadata = metadataRef.current;

        // Don't render bounding boxes if video is paused or no metadata
        if (
          !metadata ||
          metadata.timestamp === lastRenderedTimestamp.current ||
          isPaused
        ) {
          // If paused, clear the canvas but keep the animation loop running for when it resumes
          if (isPaused) {
            ctx.clearRect(0, 0, canvasWidth, canvasHeight);
          }
          animationFrameRef.current = requestAnimationFrame(render);
          return;
        }

        lastRenderedTimestamp.current = metadata.timestamp;

        // Clear canvas
        ctx.clearRect(0, 0, canvasWidth, canvasHeight);

        metadata.detections.forEach((detection, index) => {
          const { box, label, confidence, distance } = detection;

          const bboxX = box.x * canvasWidth;
          const bboxY = box.y * canvasHeight;
          const bboxWidth = box.width * canvasWidth;
          const bboxHeight = box.height * canvasHeight;

          // Color scheme
          const colors = [
            '#00d4ff',
            '#00ff88',
            '#ff6b9d',
            '#ffd93d',
            '#ff8c42',
            '#a8e6cf',
            '#b4a5ff',
            '#ffb347',
          ];
          const color = colors[index % colors.length];

          // Draw bounding box using calculated coordinates
          ctx.shadowColor = color;
          ctx.shadowBlur = 8;
          ctx.strokeStyle = color;
          ctx.lineWidth = 3;
          ctx.strokeRect(bboxX, bboxY, bboxWidth, bboxHeight);
          ctx.strokeRect(bboxX + 1, bboxY + 1, bboxWidth - 2, bboxHeight - 2);
          ctx.shadowBlur = 0;

          // Label + distance
          const labelText = `${label} ${(confidence * 100).toFixed(0)}%`;
          const distanceText = distance ? ` | ${distance.toFixed(2)}m` : '';
          const fullText = labelText + distanceText;

          ctx.font = 'bold 14px "SF Pro Display", -apple-system, sans-serif';
          const textMetrics = ctx.measureText(fullText);
          const textHeight = 18;
          const padding = 6;
          const labelY =
            bboxY > textHeight + padding
              ? bboxY - 4
              : bboxY + bboxHeight + textHeight + 4;

          // Background
          const bgGradient = ctx.createLinearGradient(
            bboxX,
            labelY - textHeight,
            bboxX,
            labelY
          );
          bgGradient.addColorStop(0, `${color}ee`);
          bgGradient.addColorStop(1, `${color}cc`);
          ctx.fillStyle = bgGradient;
          ctx.fillRect(
            bboxX,
            labelY - textHeight - padding / 2,
            textMetrics.width + padding * 2,
            textHeight + padding
          );

          // Text
          ctx.fillStyle = '#000000';
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 3;
          ctx.strokeText(fullText, bboxX + padding, labelY - padding / 2);
          ctx.fillText(fullText, bboxX + padding, labelY - padding / 2);
        });

        // FPS
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
        if (animationFrameRef.current)
          cancelAnimationFrame(animationFrameRef.current);
        resizeObserver.disconnect();
        window.removeEventListener('resize', updateCanvasSize);
        video.removeEventListener('loadedmetadata', updateCanvasSize);
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
