# Webcam Bird-Watcher Design Document

## Problem Statement
Extend the existing GeminiPhotoSearch app to ingest photos automatically from a webcam (e.g., a bird feeder), run species-level recognition, and store the results in the same Qdrant-backed search pipeline.

## Core Cost-Saving Strategy
Instead of sending every frame to the Gemini Embedding API (~$15-30/month at 1 frame/min), use **local motion detection** with a **1-minute debounce** to trigger captures only when an animal is actually present. Expected cost: **$1-3/month** assuming ~2 hours of daily activity.

## Core Design Choice: Search Over Images, Play the Video

The **search index always contains the single extracted snapshot image** (the frame chosen for Gemini Embedding). The envelope video is stored as a companion file. When a search result is returned, the frontend displays the snapshot image and offers a **"Play Video"** button that loads the corresponding envelope MP4, letting the user watch the full context around the detected moment.

This keeps the vector database small (one point per event) while giving rich playback context.

## High-Level Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Webcam     │────▶│  Motion Detector │────▶│  Frame Buffer   │
│  (OpenCV)    │     │  (Mac Mini CPU)  │     │  (rolling 30s)  │
└──────────────┘     └──────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │  Trigger event  │
                                               │  (motion + 1min │
                                               │   debounce)     │
                                               └─────────────────┘
                                                        │
                            ┌───────────────────────────┼───────────────────────────┐
                            ▼                           ▼                           ▼
                   ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
                   │  Save snapshot  │         │  Save envelope  │         │  Extract best   │
                   │  to samplePhotos│         │  video to disk  │         │  frame for API  │
                   │  (search index) │         │  (MP4 companion)│         │  (center frame) │
                   └─────────────────┘         └─────────────────┘         └─────────────────┘
                            │                           │                           │
                            └───────────────────────────┼───────────────────────────┘
                                                        ▼
                                               ┌─────────────────┐
                                               │  Gemini Embed   │
                                               │  (1 call/event) │
                                               └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │  Qdrant Store   │
                                               │  snapshot +     │
                                               │  video_path     │
                                               └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │  Search Result  │
                                               │  image + labels │
                                               │  + play video   │
                                               └─────────────────┘
```

## Components

### 1. Motion Detector (`motion_detector.py`)
Runs locally on the Mac Mini, consuming the webcam feed at low CPU cost.

- **Input**: Raw frames from `cv2.VideoCapture(0)` (or RTSP/IP cam URL)
- **Technique**: OpenCV `BackgroundSubtractorMOG2()` or simple absdiff between current and reference frame
- **Threshold**: Configurable pixel-change percentage (e.g., 1-3% of frame area)
- **Erosion/dilation**: Small morphological ops to suppress wind/shadow noise
- **Cooldown**: After a trigger, ignore further motion for **60 seconds**

Why MOG2 vs simple differencing:
- MOG2 adapts to slow lighting changes (sun moving, clouds)
- Less false positives from swaying branches
- Still ~5-10% CPU on a modern Mac Mini at 10 fps, 640x480 analysis resolution

### 2. Rolling Frame Buffer (`frame_buffer.py`)
A fixed-size circular buffer holding the last N seconds of raw frames in memory.

- **Size**: 30 seconds pre-trigger + 30 seconds post-trigger = 60s total envelope
- **Format**: Keep frames as numpy arrays in a `collections.deque` (maxlen based on fps)
- **Memory**: ~100 MB for 60s @ 5fps, 1920x1080, 3-channel uint8 — trivial on a Mac Mini
- **On trigger**: Dump the buffered frames to disk as an MP4 via `cv2.VideoWriter`

### 3. Envelope Expander
After initial trigger, keep recording until motion ceases.

- **Initial trigger**: Motion detected → start saving buffer + live frames
- **Extend**: If motion re-appears before the buffer would close, extend the recording
- **Close condition**: No motion for 3 consecutive seconds (configurable)
- **Result**: One MP4 file per visit, containing the full animal presence

### 4. Snapshot Extractor
The Gemini Embedding API needs a single image, not video. Choose the best frame from the envelope.

- **Strategy A**: Center frame (simple, works for brief visits)
- **Strategy B**: Frame with largest bounding box from MOG2 foreground mask (animal is biggest/most visible)
- **Strategy C**: Send 2-3 frames and pick the one with highest similarity to "bird" label (one extra API call, but better quality)

### 5. Integration with Existing Pipeline
The saved snapshot goes into `samplePhotos/webcam/` and is picked up by the existing indexer.

- Option A: Motion detector writes directly to `samplePhotos/webcam/`, existing `indexer.py` cron/loop scans it
- Option B: Motion detector calls the `/index` API endpoint directly

## Rolling Buffer / Envelope Discard Logic

```
timeline:
  [========== buffer ==========][==== recording ====][== tail ==]
       ^ trigger here              ^ motion continues   ^ motion stops
       │                           │                    │
       └─ 30s pre saved            └─ live append        └─ 3s grace, then finalize
```

1. **Always keep** the last 30 seconds in RAM (circular buffer)
2. **On motion**: Start appending live frames to disk; lockout timer = 60s
3. **While motion active**: Continue appending; buffer effectively "expands"
4. **Motion stops**: Keep appending for 3-second grace period, then finalize MP4
5. **Lockout**: For 60 seconds after finalization, ignore all motion (prevents re-trigger on same animal)
6. **Discard**: Everything outside the envelope is dropped from RAM — never touches disk or API

## Cost Model

| Scenario | Frames/Month | Tokens/Month | Cost (paid) | Cost (batch) |
|----------|-------------|--------------|-------------|--------------|
| Naive (1/min, 24h) | 43,200 | ~67M | ~$30 | ~$15 |
| Motion + debounce (2h/day active) | 3,600 | ~5.6M | ~$2.50 | ~$1.25 |
| Light activity (30 min/day) | 900 | ~1.4M | ~$0.63 | ~$0.32 |

*Assumes 1920x1080 = ~1,548 tokens/frame (6 tiles × 258 tokens/tile). Gemini Embedding 2: $0.45/1M tokens (paid), $0.225/1M (batch).*

## File Layout (Proposed)

```
backend/
  services/
    motion_detector.py      # MOG2 + trigger logic
    frame_buffer.py         # circular buffer + envelope writer
    webcam_ingest.py        # orchestrator tying it all together
  config.py                 # add WEBCAM_* settings
  main.py                   # optional: /webcam/start /webcam/stop endpoints
samplePhotos/
  webcam/                   # auto-created at runtime
  webcam_video/             # optional: saved envelopes as MP4
```

## Data Model Changes

To support the "search image, play video" flow, the following schema additions are needed:

### Backend (`backend/models/schemas.py`)
Add `video_path: str | None` to `SearchResultItem`. The indexer writes this field when it detects a companion `.mp4` alongside the image file.

### Qdrant Payload
Each point stores:
- `image_path`: absolute path to the snapshot (existing)
- `video_path`: absolute path to the envelope MP4 (new, nullable)
- `labels`: list of computed semantic labels (existing)
- `timestamp`: ISO-8601 string of when the event was captured (new)

### Companion File Naming Convention
```
samplePhotos/webcam/
  2026-04-27_14-32-01.jpg      # snapshot sent to Gemini
  2026-04-27_14-32-01.mp4      # envelope video (same basename, different ext)
```

The indexer resolves the MP4 path by checking if `Path(image_path).with_suffix(".mp4").exists()`.

### Frontend (`frontend/src/components/ImagePreview.tsx`)
- Add a small play-overlay icon on thumbnail hover when `video_path` is present
- Clicking opens a modal or inline `<video>` player showing the envelope
- Video playback starts at the center timestamp (roughly when the snapshot was extracted)

## Open Questions for Next Session

1. **Multi-animal**: If a cardinal arrives, then a sparrow 30s later, do we want one envelope or two? (Current design: 60s lockout merges them into one event.)
2. **Night vision**: IR camera or daytime-only? MOG2 works with IR but noise profile changes.
3. **Notification**: Push/email when a rare species is detected? (Could use Gemini text generation on the labels.)
4. **Realtime search**: Should the frontend show "live today" photos in a separate section, or mix with historical search?
5. **Video serving**: Serve MP4s via FastAPI static file route (`/videos/{filename}`), or direct filesystem path in dev mode?
