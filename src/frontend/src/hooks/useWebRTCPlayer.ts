/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { logger } from '../lib/logger';

export type TransportMode = 'direct' | 'ion-sfu';

interface SfuConfig {
  url?: string;
  sessionId?: string;
  clientId?: string;
}

const ICE_SERVERS = [{ urls: ['stun:stun.l.google.com:19302'] }];

function serializeDescription(desc: RTCSessionDescriptionInit) {
  return { sdp: desc.sdp ?? '', type: desc.type ?? 'offer' };
}

function serializeCandidate(candidate: RTCIceCandidate) {
  return {
    candidate: candidate.candidate,
    sdpMid: candidate.sdpMid ?? undefined,
    sdpMLineIndex: candidate.sdpMLineIndex ?? undefined,
  };
}

function randomId() {
  if (
    typeof crypto !== 'undefined' &&
    typeof crypto.randomUUID === 'function'
  ) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

// ConnectionState: short union for connection lifecycle
export type ConnectionState = 'idle' | 'connecting' | 'connected' | 'error';

// Normalize a backend signaling URL into a full /offer endpoint (uses fallback when invalid)
export function normalizeOfferUrl(raw?: string): string {
  const fallback = 'http://localhost:8001/offer';
  if (!raw) return fallback;
  try {
    const url = new URL(raw);
    const path = url.pathname.replace(/\/+$/, '');
    url.pathname = path.endsWith('/offer') ? path : `${path}/offer`;
    return url.toString();
  } catch {
    try {
      const withScheme = /^https?:\/\//.test(raw) ? raw : `http://${raw}`;
      const url = new URL(withScheme);
      const path = url.pathname.replace(/\/+$/, '');
      url.pathname = path.endsWith('/offer') ? path : `${path}/offer`;
      return url.toString();
    } catch {
      return fallback;
    }
  }
}

// Hook options
export interface UseWebRTCPlayerOptions {
  signalingEndpoint?: string;
  autoPlay?: boolean;
  containerRef?: React.RefObject<HTMLDivElement>;
  transportMode?: TransportMode;
  sfuConfig?: SfuConfig;
}

// WebRTC Stats
export interface WebRTCStats {
  videoResolution?: { width: number; height: number };
  packetLoss?: number;
  jitter?: number;
  bitrate?: number;
  framesReceived?: number;
  framesDecoded?: number;
}

// Hook result
export interface UseWebRTCPlayerResult {
  videoRef: React.RefObject<HTMLVideoElement>;
  connectionState: ConnectionState;
  errorReason: string;
  isPaused: boolean;
  latencyMs?: number;
  stats: WebRTCStats;
  connect: () => Promise<void>;
  disconnect: () => void;
  togglePlayPause: () => Promise<void>;
  enterFullscreen: () => void;
}

// Hook: manages a WebRTC receiver (connect/disconnect, latency polling)
export function useWebRTCPlayer({
  signalingEndpoint,
  autoPlay = false,
  containerRef,
  transportMode,
  sfuConfig,
}: UseWebRTCPlayerOptions): UseWebRTCPlayerResult {
  const log = useMemo(() => logger.child({ component: 'useWebRTCPlayer' }), []);
  const offerUrl = useMemo(() => {
    const envUrl = (import.meta as any)?.env?.VITE_BACKEND_URL as
      | string
      | undefined;
    const base = signalingEndpoint ?? envUrl ?? 'http://localhost:8001';
    return normalizeOfferUrl(base);
  }, [signalingEndpoint]);

  const sfuClientIdRef = useRef<string | null>(null);
  const resolvedMode: TransportMode = useMemo(() => {
    const envMode = (
      (import.meta as any)?.env?.VITE_WEBRTC_MODE as string | undefined
    )?.toLowerCase();
    if (transportMode) return transportMode;
    if (envMode === 'ion-sfu') return 'ion-sfu';
    if (sfuConfig?.url || (import.meta as any)?.env?.VITE_SFU_URL)
      return 'ion-sfu';
    return 'direct';
  }, [transportMode, sfuConfig]);

  const sfuSettings = useMemo(() => {
    const env: any = (import.meta as any)?.env ?? {};
    const url = sfuConfig?.url ?? env?.VITE_SFU_URL ?? 'ws://localhost:7000/ws';
    const sessionId =
      sfuConfig?.sessionId ?? env?.VITE_SFU_SESSION ?? 'optibot';
    if (!sfuClientIdRef.current) {
      sfuClientIdRef.current =
        sfuConfig?.clientId ??
        env?.VITE_SFU_CLIENT_ID ??
        `frontend-${randomId()}`;
    }
    return { url, sessionId, clientId: sfuClientIdRef.current };
  }, [sfuConfig]);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const statsPollRef = useRef<number | null>(null);
  const sfuSignalRef = useRef<WebSocket | null>(null);
  const sfuPendingRef = useRef<Map<string, (msg: any) => void>>(new Map());
  const sfuTimeoutsRef = useRef<Map<string, number>>(new Map());
  const sfuPubPcRef = useRef<RTCPeerConnection | null>(null);
  const sfuSubPcRef = useRef<RTCPeerConnection | null>(null);

  const [connectionState, setConnectionState] =
    useState<ConnectionState>('idle');
  const [errorReason, setErrorReason] = useState('');
  const [isPaused, setIsPaused] = useState(false);
  const [latencyMs, setLatencyMs] = useState<number | undefined>(undefined);
  const [stats, setStats] = useState<WebRTCStats>({});

  const resetSfuState = useCallback(() => {
    sfuPendingRef.current.forEach((resolve) => resolve({ error: 'cancelled' }));
    sfuPendingRef.current.clear();
    sfuTimeoutsRef.current.forEach((timeoutId) =>
      window.clearTimeout(timeoutId)
    );
    sfuTimeoutsRef.current.clear();
    if (sfuSignalRef.current) {
      try {
        sfuSignalRef.current.onmessage = null;
        sfuSignalRef.current.onerror = null;
        sfuSignalRef.current.onclose = null;
        sfuSignalRef.current.close();
      } catch {}
    }
    sfuSignalRef.current = null;
    [sfuPubPcRef.current, sfuSubPcRef.current].forEach((pc) => {
      if (pc) {
        try {
          pc.getReceivers().forEach(
            (r) => r.track && (r.track.enabled = false)
          );
          pc.close();
        } catch {}
      }
    });
    sfuPubPcRef.current = null;
    sfuSubPcRef.current = null;
  }, []);

  const connectDirect = useCallback(async () => {
    if (pcRef.current) return;
    log.info('webrtc.connect.start', { offerUrl });
    setErrorReason('');
    setConnectionState('connecting');

    const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
    pcRef.current = pc;

    pc.addTransceiver('video', { direction: 'recvonly' });

    const waitForFirstCandidate = () =>
      new Promise<void>((resolve) => {
        let resolved = false;
        let timeoutId: number;
        const finish = () => {
          if (resolved) return;
          resolved = true;
          pc.removeEventListener('icecandidate', handler);
          window.clearTimeout(timeoutId);
          resolve();
        };
        const handler = (event: RTCPeerConnectionIceEvent) => {
          if (event.candidate || pc.iceGatheringState === 'complete') {
            finish();
          }
        };
        pc.addEventListener('icecandidate', handler);
        timeoutId = window.setTimeout(finish, 750);
      });

    pc.ontrack = (e) => {
      const [stream] = e.streams;
      if (!videoRef.current) return;
      videoRef.current.srcObject = stream;
      videoRef.current.onloadedmetadata = () => {
        if (autoPlay) {
          videoRef.current?.play().catch(() => {});
        }
      };
    };

    try {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      await waitForFirstCandidate();

      const localDesc = pc.localDescription;
      if (!localDesc?.sdp) {
        throw new Error('Missing local SDP');
      }

      const res = await fetch(offerUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sdp: localDesc.sdp,
          type: localDesc.type,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const answer = await res.json();
      await pc.setRemoteDescription(new RTCSessionDescription(answer));
      setConnectionState('connected');
      setIsPaused(false);
      log.info('webrtc.connect.success');
    } catch (err) {
      setConnectionState('error');
      setErrorReason(String(err));
      log.error('webrtc.connect.failed', { error: String(err) });
      try {
        pc.close();
      } catch {}
      pcRef.current = null;
    }
  }, [offerUrl, autoPlay, log]);

  const connectSfu = useCallback(async () => {
    if (sfuSignalRef.current || sfuSubPcRef.current) return;

    log.info('webrtc.sfu.connect.start', {
      signaling: sfuSettings.url,
      sessionId: sfuSettings.sessionId,
    });
    setErrorReason('');
    setConnectionState('connecting');

    const signal = new WebSocket(sfuSettings.url);
    sfuSignalRef.current = signal;

    const rpcNotify = (method: string, params: any) => {
      if (signal.readyState === WebSocket.OPEN) {
        signal.send(JSON.stringify({ method, params }));
      }
    };

    const rpcCall = (method: string, params: any) =>
      new Promise<any>((resolve, reject) => {
        const id = randomId();
        const timeoutId = window.setTimeout(() => {
          sfuPendingRef.current.delete(id);
          sfuTimeoutsRef.current.delete(id);
          reject(new Error(`SFU ${method} timeout`));
        }, 12000);
        sfuTimeoutsRef.current.set(id, timeoutId);
        sfuPendingRef.current.set(id, (msg: any) => {
          window.clearTimeout(timeoutId);
          sfuTimeoutsRef.current.delete(id);
          sfuPendingRef.current.delete(id);
          if (msg.error) reject(new Error(String(msg.error)));
          else resolve(msg.result ?? msg);
        });
        signal.send(JSON.stringify({ id, method, params }));
      });

    const pubPc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
    const subPc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
    sfuPubPcRef.current = pubPc;
    sfuSubPcRef.current = subPc;
    pcRef.current = subPc;

    pubPc.createDataChannel('ion-sfu');
    pubPc.onicecandidate = ({ candidate }) => {
      if (candidate) {
        rpcNotify('trickle', {
          candidate: serializeCandidate(candidate),
          target: 0,
        });
      }
    };
    subPc.onicecandidate = ({ candidate }) => {
      if (candidate) {
        rpcNotify('trickle', {
          candidate: serializeCandidate(candidate),
          target: 1,
        });
      }
    };
    subPc.ontrack = (e) => {
      const [stream] = e.streams;
      if (!videoRef.current) return;
      videoRef.current.srcObject = stream;
      videoRef.current.onloadedmetadata = () => {
        if (autoPlay) {
          videoRef.current?.play().catch(() => {});
        }
      };
      setConnectionState('connected');
      setIsPaused(false);
    };

    const handleOffer = async (params: any) => {
      const desc = params?.desc ?? params;
      if (!desc?.sdp || !desc?.type) return;
      await subPc.setRemoteDescription(desc);
      const answer = await subPc.createAnswer();
      await subPc.setLocalDescription(answer);
      rpcNotify('answer', { desc: serializeDescription(answer) });
    };

    const handleTrickle = async (params: any) => {
      const targetPc =
        params?.target === 0 ? pubPc : params?.target === 1 ? subPc : null;
      if (!targetPc || !params?.candidate) return;
      try {
        await targetPc.addIceCandidate(params.candidate);
      } catch (err) {
        log.debug('webrtc.sfu.candidate.reject', { error: String(err) });
      }
    };

    signal.onmessage = async (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.id && (message.result !== undefined || message.error)) {
          const handler = sfuPendingRef.current.get(message.id);
          if (handler) {
            handler(message);
          }
          return;
        }
        if (message.method === 'offer') {
          await handleOffer(message.params);
        } else if (message.method === 'trickle') {
          await handleTrickle(message.params);
        }
      } catch (err) {
        log.debug('webrtc.sfu.signal.parse_error', { error: String(err) });
      }
    };
    signal.onclose = () => {
      resetSfuState();
      sfuPendingRef.current.forEach((handler) =>
        handler({ error: 'signal closed' })
      );
      sfuPendingRef.current.clear();
      setConnectionState((prev) => (prev === 'idle' ? prev : 'error'));
    };

    const waitForSignal = new Promise<void>((resolve, reject) => {
      const timeoutId = window.setTimeout(() => {
        reject(new Error('SFU signaling timeout'));
      }, 8000);
      signal.onopen = () => {
        window.clearTimeout(timeoutId);
        resolve();
      };
      signal.onerror = () => {
        window.clearTimeout(timeoutId);
        reject(new Error('SFU signaling error'));
      };
      signal.onclose = () => {
        window.clearTimeout(timeoutId);
        reject(new Error('SFU signaling closed'));
      };
    });

    try {
      await waitForSignal;
      const offer = await pubPc.createOffer();
      await pubPc.setLocalDescription(offer);
      const answer = await rpcCall('join', {
        sid: sfuSettings.sessionId,
        uid: sfuSettings.clientId,
        offer: serializeDescription(offer),
        config: {
          no_subscribe: false,
          no_publish: false,
          no_auto_subscribe: false,
        },
      });
      await pubPc.setRemoteDescription(new RTCSessionDescription(answer));
      log.info('webrtc.sfu.joined', {
        sessionId: sfuSettings.sessionId,
        clientId: sfuSettings.clientId,
      });
    } catch (err) {
      setConnectionState('error');
      setErrorReason(String(err));
      log.error('webrtc.sfu.connect.failed', { error: String(err) });
      resetSfuState();
      pcRef.current = null;
    }
  }, [sfuSettings, autoPlay, log, resetSfuState]);

  const connect = useCallback(async () => {
    if (resolvedMode === 'ion-sfu') {
      await connectSfu();
      return;
    }
    await connectDirect();
  }, [resolvedMode, connectDirect, connectSfu]);

  const disconnect = useCallback(() => {
    const pc = pcRef.current;
    log.info('webrtc.disconnect');
    resetSfuState();
    if (pc) {
      try {
        pc.getReceivers().forEach((r) => r.track && (r.track.enabled = false));
        pc.close();
      } catch {}
    }
    pcRef.current = null;
    if (videoRef.current) {
      try {
        videoRef.current.pause();
        (videoRef.current as any).srcObject = null;
      } catch {}
    }
    setIsPaused(false);
    setConnectionState('idle');
    setLatencyMs(undefined);
    setStats({});
    if (statsPollRef.current) {
      window.clearInterval(statsPollRef.current);
      statsPollRef.current = null;
    }
  }, [log, resetSfuState]);

  const togglePlayPause = useCallback(async () => {
    if (connectionState !== 'connected') {
      await connect();
      return;
    }
    if (!videoRef.current) return;
    if (isPaused) {
      try {
        pcRef.current
          ?.getReceivers()
          .forEach((r) => r.track && (r.track.enabled = true));
      } catch {}
      await videoRef.current.play().catch(() => {});
      setIsPaused(false);
      log.info('webrtc.play.resumed');
    } else {
      try {
        pcRef.current
          ?.getReceivers()
          .forEach((r) => r.track && (r.track.enabled = false));
      } catch {}
      videoRef.current.pause();
      setIsPaused(true);
      log.info('webrtc.play.paused');
    }
  }, [connectionState, isPaused, connect, log]);

  const enterFullscreen = useCallback(() => {
    const el = (containerRef?.current ??
      videoRef.current?.parentElement ??
      videoRef.current) as any;
    if (!el) return;
    const doc: any = document as any;
    const isFull =
      doc.fullscreenElement ||
      doc.webkitFullscreenElement ||
      doc.msFullscreenElement;
    if (isFull) {
      const exit =
        doc.exitFullscreen || doc.webkitExitFullscreen || doc.msExitFullscreen;
      if (exit) exit.call(doc);
      return;
    }
    const req =
      el.requestFullscreen ||
      el.webkitRequestFullscreen ||
      el.msRequestFullscreen;
    if (req) req.call(el);
    log.info('webrtc.fullscreen.toggle');
  }, [containerRef, log]);

  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

  // Poll WebRTC stats for latency when connected
  useEffect(() => {
    if (connectionState !== 'connected' || !pcRef.current) {
      if (statsPollRef.current) {
        window.clearInterval(statsPollRef.current);
        statsPollRef.current = null;
      }
      return;
    }

    const poll = async () => {
      try {
        const pc = pcRef.current;
        if (!pc) return;
        const statsReports = await pc.getStats();
        let rttSeconds: number | undefined;
        const newStats: WebRTCStats = {};

        statsReports.forEach((report) => {
          // Latency (RTT)
          if (
            report.type === 'candidate-pair' &&
            (report as any).nominated &&
            (report as any).state === 'succeeded'
          ) {
            const v = (report as any).currentRoundTripTime;
            if (typeof v === 'number') {
              rttSeconds = v;
            }
          }
          if (
            report.type === 'remote-inbound-rtp' &&
            (report as any).roundTripTime != null
          ) {
            const v = (report as any).roundTripTime;
            if (typeof v === 'number') {
              rttSeconds = v;
            }
          }

          // Inbound RTP stats (video quality, packet loss, jitter, bitrate)
          if (
            report.type === 'inbound-rtp' &&
            (report as any).kind === 'video'
          ) {
            const inboundReport = report as any;

            // Video resolution
            if (inboundReport.frameWidth && inboundReport.frameHeight) {
              newStats.videoResolution = {
                width: inboundReport.frameWidth,
                height: inboundReport.frameHeight,
              };
            }

            // Frames statistics
            if (inboundReport.framesReceived !== undefined) {
              newStats.framesReceived = inboundReport.framesReceived;
            }
            if (inboundReport.framesDecoded !== undefined) {
              newStats.framesDecoded = inboundReport.framesDecoded;
            }

            // Packet loss (calculate from packets lost and received)
            if (
              inboundReport.packetsLost !== undefined &&
              inboundReport.packetsReceived !== undefined
            ) {
              const totalPackets =
                inboundReport.packetsReceived + inboundReport.packetsLost;
              if (totalPackets > 0) {
                newStats.packetLoss =
                  (inboundReport.packetsLost / totalPackets) * 100;
              }
            }

            // Jitter (in milliseconds)
            if (inboundReport.jitter !== undefined) {
              newStats.jitter = inboundReport.jitter * 1000; // Convert seconds to ms
            }

            // Bitrate (calculate from bytes received)
            if (
              inboundReport.bytesReceived !== undefined &&
              inboundReport.timestamp !== undefined
            ) {
              // Store previous values for bitrate calculation
              const prevBytes = (pcRef.current as any)._prevBytesReceived;
              const prevTimestamp = (pcRef.current as any)._prevTimestamp;

              if (prevBytes !== undefined && prevTimestamp !== undefined) {
                const bytesDiff = inboundReport.bytesReceived - prevBytes;
                const timeDiff =
                  (inboundReport.timestamp - prevTimestamp) / 1000; // Convert to seconds

                if (timeDiff > 0) {
                  // Bitrate in Mbps
                  newStats.bitrate = (bytesDiff * 8) / (timeDiff * 1000000);
                }
              }

              // Store current values for next calculation
              (pcRef.current as any)._prevBytesReceived =
                inboundReport.bytesReceived;
              (pcRef.current as any)._prevTimestamp = inboundReport.timestamp;
            }
          }
        });

        if (rttSeconds != null) {
          setLatencyMs(Math.max(0, Math.round(rttSeconds * 1000)));
        }

        setStats(newStats);
      } catch (err) {
        log.debug('webrtc.stats.error', { error: String(err) });
      }
    };

    // initial poll and interval
    poll();
    statsPollRef.current = window.setInterval(poll, 250);
    return () => {
      if (statsPollRef.current) {
        window.clearInterval(statsPollRef.current);
        statsPollRef.current = null;
      }
    };
  }, [connectionState, log]);

  return {
    videoRef,
    connectionState,
    errorReason,
    isPaused,
    latencyMs,
    stats,
    connect,
    disconnect,
    togglePlayPause,
    enterFullscreen,
  };
}
