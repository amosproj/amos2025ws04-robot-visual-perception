import { useState, useEffect } from 'react';

function App() {
  const [status, setStatus] = useState('Ready');

  useEffect(() => {
    console.log('🤖 Robot Visual Perception initialized');
    setStatus('Connected ✓');
  }, []);

  return (
    <div id="app">
      <header>
        <h1>🤖 Robot Visual Perception</h1>
        <p>T-Systems Project - AMOS 2025</p>
      </header>
      <main>
        <div className="status">
          <h2>Status: {status}</h2>
          <p>Camera feed will appear here</p>
        </div>
      </main>
    </div>
  );
}

export default App;

