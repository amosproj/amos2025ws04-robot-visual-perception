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

    // Main render loop
    useEffect(() => {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      if (!canvas || !video) return;

      const ctx = canvas.getContext('2d', {
        alpha: true,
        desynchronized: true, // reduce latency
      });
      if (!ctx) return;

      // Update canvas size to match video EXACTLY
      const updateCanvasSize = () => {
        // Wait for video to load its metadata
        if (video.videoWidth === 0 || video.videoHeight === 0) {
          return;
        }

        const rect = video.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;

        // Set canvas size to match video display size
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        canvas.style.width = `${rect.width}px`;
        canvas.style.height = `${rect.height}px`;

        // Position canvas exactly over video
        canvas.style.position = 'absolute';
        canvas.style.top = '0px';
        canvas.style.left = '0px';

        ctx.scale(dpr, dpr);
        
        console.log(`Canvas resized: ${rect.width}x${rect.height}, video: ${video.videoWidth}x${video.videoHeight}`);
      };

      // Listen for video metadata loaded
      const handleVideoLoad = () => {
        console.log('Video loaded, updating canvas size');
        updateCanvasSize();
      };

      video.addEventListener('loadedmetadata', handleVideoLoad);
      video.addEventListener('resize', updateCanvasSize);
      
      updateCanvasSize();
      const resizeObserver = new ResizeObserver(() => {
        // Small delay to ensure video has updated
        setTimeout(updateCanvasSize, 10);
      });
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

        // Draw each bounding box with enhanced dark mode styling
        metadata.detections.forEach((detection, index) => {
          const { box, label, confidence, distance } = detection;

          // Convert normalized coordinates to pixel coordinates
          const x = box.x * displayWidth;
          const y = box.y * displayHeight;
          const width = box.width * displayWidth;
          const height = box.height * displayHeight;

          // Color scheme for different objects
          const colors = [
            '#00d4ff', // cyan
            '#00ff88', // green
            '#ff6b9d', // pink
            '#ffd93d', // yellow
            '#ff8c42', // orange
            '#a8e6cf', // mint
            '#b4a5ff', // purple
            '#ffb347'  // peach
          ];
          const color = colors[index % colors.length];

          // Draw glowing bounding box
          ctx.shadowColor = color;
          ctx.shadowBlur = 8;
          ctx.strokeStyle = color;
          ctx.lineWidth = 3;
          
          // Draw double border for better visibility
          ctx.strokeRect(x, y, width, height);
          ctx.strokeRect(x + 1, y + 1, width - 2, height - 2);
          
          // Reset shadow
          ctx.shadowBlur = 0;

          // Prepare label text
          const labelText = `${label} ${(confidence * 100).toFixed(0)}%`;
          const distanceText = distance ? ` | ${distance.toFixed(2)}m` : '';
          const fullText = labelText + distanceText;

          // Enhanced text styling
          ctx.font = 'bold 14px "SF Pro Display", -apple-system, sans-serif';
          const textMetrics = ctx.measureText(fullText);
          const textHeight = 22;
          const padding = 8;
          
          // Calculate label position (avoid going off-screen)
          const labelY = y > textHeight + padding ? y - 4 : y + height + textHeight + 4;

          // Draw rounded background with gradient
          const bgGradient = ctx.createLinearGradient(x, labelY - textHeight, x, labelY);
          bgGradient.addColorStop(0, `${color}ee`);
          bgGradient.addColorStop(1, `${color}cc`);
          
          ctx.fillStyle = bgGradient;
          const bgWidth = textMetrics.width + padding * 2;
          const bgHeight = textHeight + padding;
          
          // Rounded rectangle background (manual implementation for compatibility)
          const radius = 6;
          const rectX = x;
          const rectY = labelY - bgHeight;
          
          ctx.beginPath();
          ctx.moveTo(rectX + radius, rectY);
          ctx.lineTo(rectX + bgWidth - radius, rectY);
          ctx.quadraticCurveTo(rectX + bgWidth, rectY, rectX + bgWidth, rectY + radius);
          ctx.lineTo(rectX + bgWidth, rectY + bgHeight - radius);
          ctx.quadraticCurveTo(rectX + bgWidth, rectY + bgHeight, rectX + bgWidth - radius, rectY + bgHeight);
          ctx.lineTo(rectX + radius, rectY + bgHeight);
          ctx.quadraticCurveTo(rectX, rectY + bgHeight, rectX, rectY + bgHeight - radius);
          ctx.lineTo(rectX, rectY + radius);
          ctx.quadraticCurveTo(rectX, rectY, rectX + radius, rectY);
          ctx.closePath();
          ctx.fill();

          // Draw text with outline for better readability
          ctx.fillStyle = '#000000';
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 3;
          ctx.strokeText(fullText, x + padding, labelY - padding - 2);
          ctx.fillText(fullText, x + padding, labelY - padding - 2);
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