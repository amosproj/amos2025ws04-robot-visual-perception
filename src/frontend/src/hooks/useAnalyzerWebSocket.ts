/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

// hooks/useAnalyzerWebSocket.ts
import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import type { MetadataFrame } from '../components/video/VideoOverlay';
import { logger } from '../lib/logger';
import { roundToDecimals, exponentialBackoff } from '../lib/mathUtils';

interface AnalyzerWebSocketOptions {
  endpoint?: string;
  autoConnect?: boolean;
  onBeforeDisconnect?: () => void;
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
  onBeforeDisconnect,
}: AnalyzerWebSocketOptions = {}): UseAnalyzerWebSocketResult {
  const log = useMemo(
    () => logger.child({ component: 'useAnalyzerWebSocket', endpoint }),
    [endpoint]
  );
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
  const manualDisconnectRef = useRef(false);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      log.info('analyzer.connect.start');
      const ws = new WebSocket(endpoint);
      wsRef.current = ws;

      ws.onopen = () => {
        log.info('analyzer.connect.success');
        setIsConnected(true);
        reconnectAttempts.current = 0;
        manualDisconnectRef.current = false; // Reset flag on successful connection

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
        // Ignore messages if manually disconnected (race condition protection)
        if (manualDisconnectRef.current) {
          log.debug('analyzer.message.ignored', {
            reason: 'manual_disconnect',
          });
          return;
        }

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
              labelText: det.label_text ?? det.labelText,
              confidence: det.confidence,
              box: det.box,
              distance: det.distance,
              position: det.position,
              interpolated: det.interpolated,
            })),
          };

          setLatestMetadata(metadata);

          // Update FPS if available
          if (data.fps !== null && data.fps !== undefined) {
            setFps(roundToDecimals(data.fps, 1)); // Round to 1 decimal
          }
          log.debug('analyzer.message.received', {
            frameId: metadata.frameId,
            detections: metadata.detections.length,
            fps: data.fps,
          });
        } catch (error) {
          log.error('analyzer.message.parse_error', { error: String(error) });
        }
      };

      ws.onclose = (event) => {
        log.warn('analyzer.disconnect', {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean,
          manual: manualDisconnectRef.current,
        });
        setIsConnected(false);
        setLatestMetadata(null);
        wsRef.current = null;

        // Auto-reconnect with exponential backoff (but not after manual disconnect)
        if (
          autoConnect &&
          !manualDisconnectRef.current &&
          reconnectAttempts.current < 10
        ) {
          const delay = exponentialBackoff(reconnectAttempts.current);
          reconnectAttempts.current++;
          log.info('analyzer.reconnect.scheduled', {
            attempt: reconnectAttempts.current,
            delayMs: delay,
          });

          reconnectTimeoutRef.current = setTimeout(connect, delay);
        }
      };

      ws.onerror = (error) => {
        log.error('analyzer.socket.error', { error: String(error) });
      };
    } catch (error) {
      log.error('analyzer.connect.failed', { error: String(error) });
    }
  }, [endpoint, autoConnect, log]);

  const disconnectImmediate = useCallback(() => {
    // Mark as manual disconnect to prevent auto-reconnect
    manualDisconnectRef.current = true;
    reconnectAttempts.current = 0;

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

  const disconnect = useCallback(() => {
    // Call pre-disconnect callback if provided (only on manual disconnect)
    if (onBeforeDisconnect) {
      log.info('analyzer.disconnect.requested');
      onBeforeDisconnect();
      // Wait 1 second before proceeding with disconnect
      setTimeout(() => {
        disconnectImmediate();
      }, 200);
    } else {
      disconnectImmediate();
    }
  }, [onBeforeDisconnect, disconnectImmediate, log]);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      // Skip pre-disconnect callback on cleanup (not a manual disconnect)
      disconnectImmediate();
    };
  }, [connect, disconnectImmediate, autoConnect]);

  return {
    isConnected,
    latestMetadata,
    fps,
    connect,
    disconnect,
  };
}
