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
    const lastLayoutRef = useRef({
      width: 0,
      height: 0,
      top: 0,
      left: 0,
      dpr: typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1,
    });

    const clamp = (value: number, min: number, max: number) =>
      Math.min(Math.max(value, min), max);

    const computeDisplayedVideoRect = (
      video: HTMLVideoElement,
      videoRect: DOMRect
    ) => {
      const intrinsicWidth = video.videoWidth || videoRect.width;
      const intrinsicHeight = video.videoHeight || videoRect.height;
      const elementWidth = videoRect.width;
      const elementHeight = videoRect.height;
      const objectFit =
        window.getComputedStyle(video).objectFit?.toLowerCase() || 'contain';

      if (!intrinsicWidth || !intrinsicHeight) {
        return {
          width: elementWidth,
          height: elementHeight,
          offsetX: 0,
          offsetY: 0,
        };
      }

      const widthRatio = elementWidth / intrinsicWidth;
      const heightRatio = elementHeight / intrinsicHeight;
      let renderWidth = elementWidth;
      let renderHeight = elementHeight;

      switch (objectFit) {
        case 'cover': {
          const scale = Math.max(widthRatio, heightRatio);
          renderWidth = intrinsicWidth * scale;
          renderHeight = intrinsicHeight * scale;
          break;
        }
        case 'fill': {
          renderWidth = elementWidth;
          renderHeight = elementHeight;
          break;
        }
        case 'none': {
          renderWidth = intrinsicWidth;
          renderHeight = intrinsicHeight;
          break;
        }
        case 'scale-down': {
          const scale = Math.min(1, Math.min(widthRatio, heightRatio));
          renderWidth = intrinsicWidth * scale;
          renderHeight = intrinsicHeight * scale;
          break;
        }
        case 'contain':
        default: {
          const scale = Math.min(widthRatio, heightRatio);
          renderWidth = intrinsicWidth * scale;
          renderHeight = intrinsicHeight * scale;
        }
      }

      const offsetX = (elementWidth - renderWidth) / 2;
      const offsetY = (elementHeight - renderHeight) / 2;

      return { width: renderWidth, height: renderHeight, offsetX, offsetY };
    };

    const syncCanvasLayout = (
      canvas: HTMLCanvasElement,
      video: HTMLVideoElement,
      ctx: CanvasRenderingContext2D
    ) => {
      const videoRect = video.getBoundingClientRect();
      const containerRect = video.parentElement?.getBoundingClientRect();
      const { width, height, offsetX, offsetY } = computeDisplayedVideoRect(
        video,
        videoRect
      );
      const dpr = window.devicePixelRatio || 1;

      const top =
        (containerRect ? videoRect.top - containerRect.top : 0) + offsetY;
      const left =
        (containerRect ? videoRect.left - containerRect.left : 0) + offsetX;

      const sizeChanged =
        Math.abs(width - lastLayoutRef.current.width) > 0.5 ||
        Math.abs(height - lastLayoutRef.current.height) > 0.5 ||
        dpr !== lastLayoutRef.current.dpr;
      const positionChanged =
        Math.abs(top - lastLayoutRef.current.top) > 0.5 ||
        Math.abs(left - lastLayoutRef.current.left) > 0.5;

      if (sizeChanged) {
        canvas.width = Math.max(1, Math.round(width * dpr));
        canvas.height = Math.max(1, Math.round(height * dpr));
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      }

      if (sizeChanged || positionChanged) {
        canvas.style.position = 'absolute';
        canvas.style.top = `${top}px`;
        canvas.style.left = `${left}px`;
        canvas.style.zIndex = '10';
      }

      if (sizeChanged || positionChanged) {
        lastLayoutRef.current = { width, height, top, left, dpr };
      }

      return sizeChanged || positionChanged;
    };

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

      // Update canvas on video load or resize
      const updateCanvasSize = () => syncCanvasLayout(canvas, video, ctx);

      video.addEventListener('loadedmetadata', updateCanvasSize);

      // Watch for any changes to video element or container
      const resizeObserver = new ResizeObserver(updateCanvasSize);
      resizeObserver.observe(video);
      if (video.parentElement) {
        resizeObserver.observe(video.parentElement);
      }

      // Also listen for window resize and zoom changes (devicePixelRatio)
      const handleWindowResize = () => updateCanvasSize();
      window.addEventListener('resize', handleWindowResize);

      updateCanvasSize();

      const render = (currentTime: number) => {
        // Keep canvas aligned with the actually drawn video area (handles zoom/fullscreen/object-fit)
        updateCanvasSize();

        const dpr = lastLayoutRef.current.dpr || 1;
        const canvasWidth = lastLayoutRef.current.width;
        const canvasHeight = lastLayoutRef.current.height;

        const metadata = metadataRef.current;

        // Don't render bounding boxes if video is paused or no metadata
        if (
          !metadata ||
          metadata.timestamp === lastRenderedTimestamp.current ||
          isPaused
        ) {
          // If paused, clear the canvas but keep the animation loop running for when it resumes
          if (isPaused) {
            ctx.setTransform(1, 0, 0, 1, 0, 0);
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
          }
          animationFrameRef.current = requestAnimationFrame(render);
          return;
        }

        lastRenderedTimestamp.current = metadata.timestamp;

        // Clear canvas
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        metadata.detections.forEach((detection, index) => {
          const { box, label, confidence, distance } = detection;

          const rawX = box.x * canvasWidth;
          const rawY = box.y * canvasHeight;
          const rawWidth = box.width * canvasWidth;
          const rawHeight = box.height * canvasHeight;

          const bboxX = clamp(rawX, 0, canvasWidth);
          const bboxY = clamp(rawY, 0, canvasHeight);
          const bboxMaxX = clamp(rawX + rawWidth, 0, canvasWidth);
          const bboxMaxY = clamp(rawY + rawHeight, 0, canvasHeight);
          const bboxWidth = Math.max(0, bboxMaxX - bboxX);
          const bboxHeight = Math.max(0, bboxMaxY - bboxY);

          if (bboxWidth === 0 || bboxHeight === 0) {
            return;
          }

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
              : Math.min(canvasHeight - 2, bboxY + bboxHeight + textHeight + 4);
          const maxLabelWidth = Math.min(
            canvasWidth,
            textMetrics.width + padding * 2
          );
          const labelX = clamp(bboxX, 0, canvasWidth - maxLabelWidth);

          // Background
          const bgGradient = ctx.createLinearGradient(
            labelX,
            labelY - textHeight,
            labelX,
            labelY
          );
          bgGradient.addColorStop(0, `${color}ee`);
          bgGradient.addColorStop(1, `${color}cc`);
          ctx.fillStyle = bgGradient;
          ctx.fillRect(
            labelX,
            labelY - textHeight - padding / 2,
            maxLabelWidth,
            textHeight + padding
          );

          // Text
          ctx.fillStyle = '#000000';
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 3;
          ctx.strokeText(fullText, labelX + padding, labelY - padding / 2);
          ctx.fillText(fullText, labelX + padding, labelY - padding / 2);
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
        window.removeEventListener('resize', handleWindowResize);
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
