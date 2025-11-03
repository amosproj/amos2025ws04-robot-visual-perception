/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useEffect, useMemo, useRef, useState } from 'react';

function App() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const [status, setStatus] = useState('Ready');

  const offerUrl = useMemo(() => {
    const url = (import.meta as any)?.env?.VITE_BACKEND_URL as string | undefined;
    return (url ?? 'http://localhost:8000') + '/offer';
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
        };
      }
    };

    // No metadata UI; ignore data channels

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
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          style={{ width: '720px', maxWidth: '100%', borderRadius: 8, background: '#000' }}
        />
      </main>
    </div>
  );
}

export default App;
