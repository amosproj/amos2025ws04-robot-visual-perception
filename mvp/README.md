# Real-time Distance Video (MVP)

A web app that detects objects in real-time using TensorFlow.js COCO-SSD and estimates their distance using pinhole camera geometry. Supports both webcam and video file input.

## 🚀 Quick Start (30 seconds)

### Option 1: npm (Recommended)
```bash
git clone https://github.com/saribx/realtimedistancevideo.git
cd realtimedistancevideo
npm install
npm start
```
**Open:** http://localhost:5173

### Option 2: Docker
```bash
git clone https://github.com/saribx/realtimedistancevideo.git
cd realtimedistancevideo
docker build -t realtimedistancevideo .
docker run -p 5173:5173 realtimedistancevideo
```
**Open:** http://localhost:5173

## 🎯 Features

- **Real-time object detection** using COCO-SSD (person, bottle, cup, chair, tv), to see if competetive against YOLOv8
- **Distance estimation** using pinhole camera geometry
- **Multiple input sources**: Webcam, video files, or built-in person_video.mp4
- **Object filtering** by class
- **Camera FOV calibration** for accurate distance measurement
- **Live metadata**: Resolution, FPS, object count, FOV
- **Modern dark UI** with mirrored video

## 📋 Requirements

- **Node.js** 16+ (for npm option)
- **Docker** (for Docker option)
- **Modern browser** with WebRTC support
- **Camera permissions** (for webcam mode)

## 🎮 How to Use

1. **Start Camera** - Use your webcam for live detection
2. **Use person_video.mp4** - Test with the included sample video
3. **Load Video File** - Upload any video file for detection
4. **Adjust FOV** - Select camera type for better distance accuracy
5. **Filter Objects** - Show only specific object types

## 📏 Distance Estimation

Uses pinhole camera model with configurable FOV:
- **person**: 1.7m height
- **bottle**: 0.25m height  
- **cup**: 0.1m height
- **chair**: 0.9m height
- **tv**: 0.6m height

## 🛠️ Development

```bash
npm run dev    # Start dev server
npm run format # Format code
```

## 📁 Project Structure
```
realtimedistancevideo/
├── public/
│   ├── index.html         # Main app
│   ├── main.js           # Detection & distance logic
│   ├── styles.css        # Dark theme styling
│   └── person_video.mp4  # Sample video file
├── package.json          # Dependencies & scripts
├── Dockerfile           # Container support
├── requirements.txt     # Dependencies list
└── README.md           # This file
```