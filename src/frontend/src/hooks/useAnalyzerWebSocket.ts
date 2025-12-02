/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

// hooks/useAnalyzerWebSocket.ts
import { useEffect, useRef, useState, useCallback } from 'react';
import type { MetadataFrame } from '../components/video/VideoOverlay';

interface AnalyzerWebSocketOptions {
  endpoint?: string;
  autoConnect?: boolean;
}

interface UseAnalyzerWebSocketResult {
  isConnected: boolean;
  latestMetadata: MetadataFrame | null;
  fps: number | null;
  connect: () => void;
  disconnect: () => void;
}

export function useAnalyzerWebSocket({
  endpoint = 'ws://localhost:8001/ws',
  autoConnect = true,
}: AnalyzerWebSocketOptions = {}): UseAnalyzerWebSocketResult {
  const [isConnected, setIsConnected] = useState(false);
  const [latestMetadata, setLatestMetadata] = useState<MetadataFrame | null>(
    null
  );
  const [fps, setFps] = useState<number | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null
  );
  const reconnectAttempts = useRef(0);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      console.log(`Connecting to Analyzer WebSocket: ${endpoint}`);
      const ws = new WebSocket(endpoint);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('✅ Analyzer WebSocket connected');
        setIsConnected(true);
        reconnectAttempts.current = 0;

        // Send ping every 30 seconds to keep connection alive
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          } else {
            clearInterval(pingInterval);
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'pong') return;

          // Convert analyzer format to VideoOverlay format
          const metadata: MetadataFrame = {
            timestamp: data.timestamp,
            frameId: data.frame_id,
            detections: data.detections.map((det: any, index: number) => ({
              id: `detection-${data.frame_id}-${index}`,
              label: det.label,
              confidence: det.confidence,
              box: det.box,
              distance: det.distance,
              position: det.position,
            })),
          };

          setLatestMetadata(metadata);

          // Update FPS if available
          if (data.fps !== null && data.fps !== undefined) {
            setFps(Math.round(data.fps * 10) / 10); // Round to 1 decimal
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = (event) => {
        console.log(`Analyzer WebSocket disconnected (code: ${event.code})`);
        setIsConnected(false);
        setLatestMetadata(null);
        wsRef.current = null;

        // Auto-reconnect with exponential backoff
        if (autoConnect && reconnectAttempts.current < 10) {
          const delay = Math.min(
            1000 * Math.pow(2, reconnectAttempts.current),
            30000
          );
          reconnectAttempts.current++;
          console.log(
            `Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`
          );

          reconnectTimeoutRef.current = setTimeout(connect, delay);
        }
      };

      ws.onerror = (error) => {
        console.error('Analyzer WebSocket error:', error);
      };
    } catch (error) {
      console.error('Failed to connect to Analyzer WebSocket:', error);
    }
  }, [endpoint, autoConnect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setLatestMetadata(null);
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [connect, disconnect, autoConnect]);

  return {
    isConnected,
    latestMetadata,
    fps,
    connect,
    disconnect,
  };
}
