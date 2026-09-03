"""
AetherSAR - Person-detection interface and optional pretrained-model adapter.

The detector interface (BaseDetector) is dependency-free and testable without
model weights. Runtime person detection is provided by UltralyticsPersonDetector,
which lazily imports the optional 'ultralytics' package and downloads the
pretrained YOLO weights on first use. If the package cannot be loaded,
constructing the adapter raises BackendUnavailable; callers can catch it and
continue without detection.

No detection accuracy or frame-rate figures are claimed here.

CLI (real inference):

    python3 -m cv.detect <image> [--model yolov8n.pt] [--conf 0.35]
    python3 -m cv.detect <image> --json
"""

import json
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Union

if __package__ in (None, ""):
    # Allow running as a plain script: python3 cv/detect.py <image>
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cv.detection import build_detection, validate_confidence

ImageInput = Union[str, Path]


class DetectionError(RuntimeError):
    """Base error for the detection pipeline."""


class BackendUnavailable(DetectionError):
    """Raised when the optional ML backend (ultralytics) cannot be loaded."""


class BaseDetector(ABC):
    """Minimal detector interface: image in, validated detection dicts out."""

    @abstractmethod
    def detect(self, image: ImageInput, *, drone_id: str = "DRONE-01", frame_id: int = 0) -> List[dict]:
        """Run person detection on an image.

        Returns a list of canonical detection records (see cv/detection.py).
        The list is empty when no person is detected above the threshold.
        """


class UltralyticsPersonDetector(BaseDetector):
    """Person detector backed by a pretrained Ultralytics YOLO model.

    Requires the optional 'ultralytics' package (see requirements-cv.txt) and,
    on first use, network access to download the model weights. The default
    model name "yolov8n.pt" is auto-downloaded and cached by Ultralytics.
    """

    PERSON_CLASS_ID = 0  # COCO class id for "person"

    def __init__(self, model: str = "yolov8n.pt", confidence_threshold: float = 0.35):
        try:
            from ultralytics import YOLO  # optional dependency
        except ImportError as exc:
            raise BackendUnavailable(
                "ultralytics is not installed; run 'pip install -r requirements-cv.txt' "
                "to enable person detection"
            ) from exc
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model must be a non-empty string")
        self._confidence_threshold = validate_confidence(confidence_threshold)
        self._model = YOLO(model)

    def detect(self, image: ImageInput, *, drone_id: str = "DRONE-01", frame_id: int = 0) -> List[dict]:
        results = self._model.predict(str(image), verbose=False)
        detections: List[dict] = []
        for result in results:
            if result.boxes is None:
                continue
            boxes = result.boxes
            for index in range(len(boxes)):
                if int(boxes.cls[index]) != self.PERSON_CLASS_ID:
                    continue
                confidence = float(boxes.conf[index])
                if confidence < self._confidence_threshold:
                    continue
                x1, y1, x2, y2 = (int(value) for value in boxes.xyxy[index].tolist())
                detections.append(
                    build_detection(
                        drone_id=drone_id,
                        frame_id=frame_id,
                        class_name="person",
                        confidence=confidence,
                        bbox={"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                    )
                )
        return detections


def main(argv=None) -> int:
    """CLI entry point: run real person detection on a single image."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="cv.detect",
        description="Run person detection on an image with a pretrained YOLO model.",
    )
    parser.add_argument("image", help="path to the input image")
    parser.add_argument("--model", default="yolov8n.pt", help="YOLO model name/path (default: %(default)s)")
    parser.add_argument("--conf", type=float, default=0.35, help="confidence threshold (default: %(default)s)")
    parser.add_argument("--drone-id", default="DRONE-01", help="drone identifier for the records")
    parser.add_argument("--frame-id", type=int, default=0, help="frame identifier for the records")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args(argv)

    try:
        detector = UltralyticsPersonDetector(model=args.model, confidence_threshold=args.conf)
    except BackendUnavailable as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    detections = detector.detect(args.image, drone_id=args.drone_id, frame_id=args.frame_id)
    if args.json:
        print(json.dumps(detections, indent=2))
    else:
        print(f"Detected {len(detections)} person(s) in {args.image}")
        for detection in detections:
            box = detection["bbox"]
            print(
                f"  class={detection['class']} confidence={detection['confidence']:.3f} "
                f"bbox=({box['x1']}, {box['y1']}, {box['x2']}, {box['y2']})"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())