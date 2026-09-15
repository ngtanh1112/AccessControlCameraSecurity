# Local Video IVA Analysis

The local demo accepts an MP4 for an ADMIN-selected camera, stores it privately under `data/videos`, then runs a pretrained Ultralytics YOLO small model. No model training is included or required.

Set `VIDEO_ANALYZER_MODE=yolo` for the real local demo. `YOLO_MODEL` defaults to `yolo11n.pt` and can also be a local model path. The first real run may download pretrained weights. Set `VIDEO_ANALYZER_MODE=fake` only for deterministic debugging and automated tests.

Frames are sampled near `VIDEO_SAMPLE_FPS`. Supported detections are `person`, `car`, `motorcycle`, `bus`, and `truck`; they are aggregated into person or vehicle time-range events. Event metadata records the source recording, offsets, confidence, and absolute occurrence time. A best frame becomes a snapshot, while OpenCV attempts a padded MP4 clip without making clip encoding failure fatal.

Generated files are never publicly mounted. Use the existing protected media endpoints (`/api/v1/media/events/{event_id}/image` and `/video`), which apply the Access Control Gateway before returning a file. Chat searches stored event metadata; it does not run analysis again.
