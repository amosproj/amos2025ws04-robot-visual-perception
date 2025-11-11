/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import VideoOverlay, { VideoOverlayHandle } from './VideoOverlay';

function App() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const overlayRef = useRef<VideoOverlayHandle | null>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const [status, setStatus] = useState('Ready');
  const [videoReady, setVideoReady] = useState(false);

  const offerUrl = useMemo(() => {
    const url = (import.meta as any)?.env?.VITE_BACKEND_URL as
      | string
      | undefined;
    return (url ?? 'http://localhost:8001') + '/offer';
  }, []);

  useEffect(() => {
    let stopped = false;
    const pc = new RTCPeerConnection({
      iceServers: [{ urls: ['stun:stun.l.google.com:19302'] }],
    });
    pcRef.current = pc;

    pc.ontrack = (e) => {
      const [stream] = e.streams;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        // ensure playback starts when metadata arrives
        videoRef.current.onloadedmetadata = () => {
          videoRef.current?.play().catch(() => {});
          // Wait a bit to ensure video is fully ready before enabling overlay
          setTimeout(() => setVideoReady(true), 200);
        };
      }
    };

    // TODO: Handle data channel for metadata stream from backend
    // When backend sends metadata, call: overlayRef.current?.updateMetadata(metadata)

    (async () => {
      setStatus('Connecting…');
      // ask for a recvonly video m-line in the offer (server sends camera)
      pc.addTransceiver('video', { direction: 'recvonly' });
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      // wait for ICE gather complete to avoid trickle complexity
      await new Promise<void>((resolve) => {
        if (pc.iceGatheringState === 'complete') return resolve();
        const check = () => {
          if (pc.iceGatheringState === 'complete') {
            pc.removeEventListener('icegatheringstatechange', check);
            resolve();
          }
        };
        pc.addEventListener('icegatheringstatechange', check);
      });

      const sdp = pc.localDescription?.sdp ?? '';
      const res = await fetch(offerUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sdp, type: 'offer' }),
      });

      if (!res.ok) {
        setStatus(`Error: ${res.status}`);
        return;
      }

      const answer = await res.json();
      await pc.setRemoteDescription(new RTCSessionDescription(answer));
      if (!stopped) setStatus('Connected ✓');
    })().catch((err) => setStatus(`Error: ${String(err)}`));

    return () => {
      stopped = true;
      setVideoReady(false);
      try {
        pc.getSenders().forEach((s) => s.track?.stop());
        pc.getReceivers().forEach((r) => r.track?.stop());
        pc.close();
      } catch {}
      pcRef.current = null;
    };
  }, [offerUrl]);

  return (
    <div id="app">
      <header>
        <h1>OptiBot</h1>
        <p>T-Systems Project - AMOS 2025</p>
      </header>
      <main>
        <div className="status">
          <h2>Status: {status}</h2>
        </div>
        <div style={{ position: 'relative', display: 'inline-block' }}>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{
              width: '720px',
              maxWidth: '100%',
              borderRadius: 8,
              background: '#000',
            }}
          />
          {/* Only render overlay when video is ready */}
          {videoReady && (
            <VideoOverlay
              ref={overlayRef}
              videoRef={videoRef}
              testMode={true} // Set to false when integrating real backend data
            />
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
