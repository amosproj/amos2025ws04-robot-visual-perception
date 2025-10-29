/**
 * Real-time Object Detection and Distance Estimation
 * 
 * OBJECT DETECTION MODEL: COCO-SSD (Common Objects in Context - Single Shot Detector)
 * - Framework: TensorFlow.js running in browser
 * - Model: lite_mobilenet_v2 base architecture
 * - Classes: person, bottle, cup, chair, tv
 * - Input: Real-time video stream or video files
 * - Output: Bounding boxes with confidence scores
 * 
 * DISTANCE ESTIMATION MODEL: Pinhole Camera Geometry
 * - Method: distance = (knownHeight * focalLengthPixels) / bboxPixelHeight
 * - Known heights: person(1.7m), bottle(0.25m), cup(0.1m), chair(0.9m), tv(0.6m)
 * - Focal length: estimated from horizontal FOV and video width
 * - FOV options: laptop(60°), phone(75°), desktop(70°), wide(90°)
 * - Distance range: 0.5m to 10m with reasonable bounds
 * 
 * ARCHITECTURE: Client-side only
 * - No backend server required
 * - TensorFlow.js loads models from CDN
 * - HTML5 Canvas for bounding box rendering
 * - WebRTC getUserMedia for camera access
 */

(async () => {
const videoEl = document.getElementById('video');
const canvas = document.getElementById('overlay');
const ctx = canvas.getContext('2d');
const statusEl = document.getElementById('status');
const startBtn = document.getElementById('startBtn');
const videoBtn = document.getElementById('videoBtn');
const defaultVideoBtn = document.getElementById('defaultVideoBtn');
const videoInput = document.getElementById('videoInput');
const classFilter = document.getElementById('classFilter');
const fovSelect = document.getElementById('fovSelect');

const resolutionEl = document.getElementById('resolution');
const fpsEl = document.getElementById('fps');
const objectCountEl = document.getElementById('objectCount');
const currentFOVEl = document.getElementById('currentFOV');

const loadScript = (src, fallbackSrc = null) => new Promise((resolve, reject) => {
  const script = document.createElement('script');
  script.src = src;
  script.onload = resolve;
  script.onerror = () => {
    if (fallbackSrc) {
      console.warn(`Failed to load ${src}, trying fallback: ${fallbackSrc}`);
      script.src = fallbackSrc;
      script.onerror = reject;
    } else {
      reject(new Error(`Failed to load ${src}`));
    }
  };
  document.head.appendChild(script);
});

try {
  statusEl.textContent = 'Loading TensorFlow.js...';
  
  await loadScript(
    'https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.20.0/dist/tf.min.js',
    'https://unpkg.com/@tensorflow/tfjs@4.20.0/dist/tf.min.js'
  );
  statusEl.textContent = 'Loading COCO-SSD model...';
  
  await new Promise(resolve => setTimeout(resolve, 200));
  
  await loadScript(
    'https://cdn.jsdelivr.net/npm/@tensorflow-models/coco-ssd@2.2.3/dist/coco-ssd.min.js',
    'https://unpkg.com/@tensorflow-models/coco-ssd@2.2.3/dist/coco-ssd.min.js'
  );
  
  if (typeof tf === 'undefined') {
    throw new Error('TensorFlow.js failed to load');
  }
  
  statusEl.textContent = 'TensorFlow.js loaded. Ready to start camera.';
} catch (error) {
  statusEl.textContent = 'Error loading TensorFlow.js: ' + error.message;
  console.error('Failed to load TensorFlow.js:', error);
}

let model;
let running = false;
let rafId;
let frameCount = 0;
let currentStream = null;
let lastTime = 0;
let fps = 0;
let detectedObjects = 0;

const CLASS_HEIGHT_METERS = {
  person: 1.7,
  bottle: 0.25,
  cup: 0.1,
  chair: 0.9,
  tv: 0.6,
};

const CAMERA_FOV = {
  laptop: 60,
  phone: 75,
  desktop: 70,
  wide: 90
};

let currentFOV = CAMERA_FOV.laptop;

function estimateFocalLengthPixels(frameWidth){
  const hfovRad = (currentFOV * Math.PI) / 180;
  return (frameWidth/2) / Math.tan(hfovRad/2);
}

function estimateDistanceMeters(det, frameWidth){
  const knownHeight = CLASS_HEIGHT_METERS[det.class];
  if(!knownHeight){ return null; }
  const fh = estimateFocalLengthPixels(frameWidth);
  const bboxPxHeight = det.bbox[3];
  if(bboxPxHeight <= 1){ return null; }
  
  const distance = (knownHeight * fh) / bboxPxHeight;
  
  return Math.max(0.5, Math.min(10, distance));
}

function drawDetections(dets){
  const w = videoEl.videoWidth;
  const h = videoEl.videoHeight;
  canvas.width = w; canvas.height = h;
  ctx.clearRect(0,0,w,h);

  for(const det of dets){
    const [x,y,width,height] = det.bbox;
    const mirroredX = w - x - width;
    
    const label = det.class;
    const distance = estimateDistanceMeters(det, w);
    const color = distance != null ? '#80ffdb' : '#ffd166';

    ctx.lineWidth = 2;
    ctx.strokeStyle = color;
    ctx.beginPath();
    ctx.rect(mirroredX, y, width, height);
    ctx.stroke();

    const text = distance != null
      ? `${label} — ${distance.toFixed(2)} m`
      : `${label}`;

    ctx.font = '14px ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial';
    const metrics = ctx.measureText(text);
    const pad = 4;
    const tx = mirroredX; 
    const ty = Math.max(12, y - 2);
    
    ctx.fillStyle = 'rgba(0,0,0,0.6)';
    ctx.fillRect(tx-1, ty-12, metrics.width + pad*2, 16);
    
    ctx.fillStyle = color;
    ctx.fillText(text, tx + pad -1, ty);
  }
}

async function detectLoop(){
  if(!running) return;
  
  frameCount++;
  if(frameCount % 2 === 0) {
    const predictions = await model.detect(videoEl, 5);
    const filter = classFilter.value;
    const dets = filter ? predictions.filter(p => p.class === filter) : predictions;
    drawDetections(dets);
    updateMetadata(dets);
  } else {
    updateMetadata([]);
  }
  
  rafId = requestAnimationFrame(detectLoop);
}

function updateMetadata(detections = []){
  if(videoEl.videoWidth && videoEl.videoHeight) {
    resolutionEl.textContent = `${videoEl.videoWidth}×${videoEl.videoHeight}`;
  }
  
  currentFOVEl.textContent = `${currentFOV}°`;
  
  detectedObjects = detections.length;
  objectCountEl.textContent = detectedObjects;
  
  const now = performance.now();
  if(lastTime) {
    fps = Math.round(1000 / (now - lastTime));
    fpsEl.textContent = fps;
  }
  lastTime = now;
}

function stopDetection(){
  running = false;
  if(rafId) {
    cancelAnimationFrame(rafId);
    rafId = null;
  }
  if(currentStream) {
    currentStream.getTracks().forEach(track => track.stop());
    currentStream = null;
  }
  videoEl.srcObject = null;
  videoEl.src = '';
  startBtn.disabled = false;
  videoBtn.disabled = false;
  defaultVideoBtn.disabled = false;
  statusEl.textContent = 'Ready to start detection';
}

async function start(){
  if(running) return;
  stopDetection();
  
  startBtn.disabled = true;
  videoBtn.disabled = true;
  defaultVideoBtn.disabled = true;
  statusEl.textContent = 'Requesting camera…';
  
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ 
      video: { 
        width: { ideal: 640 }, 
        height: { ideal: 480 } 
      }, 
      audio: false 
    });
    currentStream = stream;
    videoEl.srcObject = stream;
    await videoEl.play();
    statusEl.textContent = 'Loading model…';
    
    model = await cocoSsd.load({ base: 'lite_mobilenet_v2' });
    statusEl.textContent = 'Running detection on camera';
  } catch (error) {
    statusEl.textContent = 'Error loading model: ' + error.message;
    console.error('Failed to load COCO-SSD model:', error);
    stopDetection();
    return;
  }
  running = true;
  detectLoop();
}

async function loadVideoFile(){
  if(running) return;
  stopDetection();
  
  startBtn.disabled = true;
  videoBtn.disabled = true;
  defaultVideoBtn.disabled = true;
  statusEl.textContent = 'Loading video file…';
  
  try {
    videoEl.src = 'person_video.mp4';
    videoEl.load();
    
    await videoEl.play();
    statusEl.textContent = 'Loading model…';
    
    model = await cocoSsd.load({ base: 'lite_mobilenet_v2' });
    statusEl.textContent = 'Running detection on person_video.mp4';
  } catch (error) {
    statusEl.textContent = 'Error loading video: ' + error.message;
    console.error('Failed to load video:', error);
    stopDetection();
    return;
  }
  running = true;
  detectLoop();
}

startBtn.addEventListener('click', start);
defaultVideoBtn.addEventListener('click', loadVideoFile);
videoBtn.addEventListener('click', () => {
  if (!running) {
    videoInput.click();
  }
});

videoInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  
  if(running) return;
  stopDetection();
  
  startBtn.disabled = true;
  videoBtn.disabled = true;
  defaultVideoBtn.disabled = true;
  statusEl.textContent = 'Loading custom video…';
  
  try {
    const url = URL.createObjectURL(file);
    videoEl.src = url;
    videoEl.load();
    
    await videoEl.play();
    statusEl.textContent = 'Loading model…';
    
    model = await cocoSsd.load({ base: 'lite_mobilenet_v2' });
    statusEl.textContent = `Running detection on ${file.name}`;
  } catch (error) {
    statusEl.textContent = 'Error loading custom video: ' + error.message;
    console.error('Failed to load custom video:', error);
    stopDetection();
    return;
  }
  running = true;
  detectLoop();
});

fovSelect.addEventListener('change', (e) => {
  currentFOV = parseInt(e.target.value);
  console.log(`FOV changed to: ${currentFOV}°`);
  updateMetadata([]);
});

try{
  const perms = await navigator.permissions.query({ name: 'camera' });
  if(perms.state === 'granted'){
    start();
  }
}catch(_){}

})();

