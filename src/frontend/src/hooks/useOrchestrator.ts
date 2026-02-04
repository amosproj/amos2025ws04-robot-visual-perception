/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useCallback, useEffect, useRef, useState } from 'react';

export interface ServiceInfo {
  url: string;
  metadata: Record<string, any>;
  last_seen: number;
}

export interface OrchestratorServices {
  streamer: ServiceInfo[];
  analyzer: ServiceInfo[];
}

interface UseOrchestratorProps {
  orchestratorUrl: string;
  onServicesUpdate?: (services: OrchestratorServices) => void;
}

/**
 * Hook for managing orchestrator service discovery and live updates.
 * Fetches initial services and subscribes to WebSocket updates.
 */
export function useOrchestrator({
  orchestratorUrl,
  onServicesUpdate,
}: UseOrchestratorProps) {
  const [services, setServices] = useState<OrchestratorServices>({
    streamer: [],
    analyzer: [],
  });
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();

  // Fetch initial services list
  const fetchServices = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`${orchestratorUrl}/services`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data: OrchestratorServices = await response.json();
      setServices(data);
      onServicesUpdate?.(data);
    } catch (err) {
      console.error('[Orchestrator] Failed to fetch services:', err);
    } finally {
      setLoading(false);
    }
  }, [orchestratorUrl, onServicesUpdate]);

  // Connect to WebSocket for live updates
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const wsUrl = orchestratorUrl
      .replace(/^http/, 'ws')
      .replace(/^https/, 'wss');

    try {
      wsRef.current = new WebSocket(`${wsUrl}/ws`);

      wsRef.current.onopen = () => {
        console.log('[Orchestrator] WebSocket connected');
        setIsConnected(true);
      };

      wsRef.current.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === 'sync') {
            // Initial state sync
            setServices(msg.services);
            onServicesUpdate?.(msg.services);
          } else if (msg.type === 'registered') {
            // Service registered
            setServices((prev) => ({
              ...prev,
              [msg.service_type]: [
                ...prev[msg.service_type as keyof OrchestratorServices],
                { url: msg.service_url, metadata: {}, last_seen: Date.now() },
              ],
            }));
          } else if (msg.type === 'unregistered') {
            // Service unregistered
            setServices((prev) => ({
              ...prev,
              [msg.service_type]: prev[
                msg.service_type as keyof OrchestratorServices
              ].filter((s) => s.url !== msg.service_url),
            }));
          }
        } catch (err) {
          console.error(
            '[Orchestrator] Failed to parse WebSocket message:',
            err
          );
        }
      };

      wsRef.current.onerror = (err) => {
        console.error('[Orchestrator] WebSocket error:', err);
      };

      wsRef.current.onclose = () => {
        console.log('[Orchestrator] WebSocket disconnected');
        setIsConnected(false);
        // Attempt reconnection after 2 seconds
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 2000);
      };
    } catch (err) {
      console.error('[Orchestrator] Failed to connect WebSocket:', err);
      reconnectTimeoutRef.current = setTimeout(connectWebSocket, 2000);
    }
  }, [orchestratorUrl, onServicesUpdate]);

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  // Request analyzer assignment for streamer
  const assignAnalyzer = useCallback(
    async (
      streamerUrl: string
    ): Promise<{ analyzerUrl: string; streamerUrl: string } | null> => {
      try {
        const response = await fetch(
          `${orchestratorUrl}/assign-analyzer?streamer_url=${encodeURIComponent(streamerUrl)}`,
          { method: 'POST' }
        );
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        if (!data.analyzer_url) {
          console.warn('[Orchestrator] No analyzer available');
          return null;
        }

        // Configure the analyzer with the streamer URL
        const analyzerConfigUrl = `http://${data.analyzer_url.replace(/^https?:\/\//, '')}/configure`;
        const configResponse = await fetch(analyzerConfigUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ streamer_url: streamerUrl }),
        });

        if (!configResponse.ok) {
          throw new Error(
            `Failed to configure analyzer: HTTP ${configResponse.status}`
          );
        }

        console.log('[Orchestrator] Analyzer configured successfully');
        return {
          analyzerUrl: data.analyzer_url,
          streamerUrl: data.streamer_url,
        };
      } catch (err) {
        console.error('[Orchestrator] Failed to assign analyzer:', err);
        return null;
      }
    },
    [orchestratorUrl]
  );

  const unassignAnalyzer = useCallback(
    async (analyzerUrl: string): Promise<boolean> => {
      try {
        const response = await fetch(
          `${orchestratorUrl}/unassign-analyzer?analyzer_url=${encodeURIComponent(analyzerUrl)}`,
          { method: 'POST' }
        );
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        await response.json();
        return true;
      } catch (err) {
        console.error('[Orchestrator] Failed to unassign analyzer:', err);
        return false;
      }
    },
    [orchestratorUrl]
  );

  // Initialize: fetch services and connect WebSocket
  useEffect(() => {
    fetchServices();
    connectWebSocket();

    return () => {
      disconnect();
    };
  }, [orchestratorUrl, fetchServices, connectWebSocket, disconnect]);

  return {
    services,
    isConnected,
    loading,
    fetchServices,
    assignAnalyzer,
    unassignAnalyzer,
    disconnect,
  };
}
