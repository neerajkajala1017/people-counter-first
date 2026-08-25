import cv2
import os
import shutil
import subprocess
import tempfile
from ultralytics import YOLO


PERSON_CLASS_ID = 0

BOX_COLOR = (0, 200, 100)
TEXT_COLOR = (255, 255, 255)
COUNT_BG_COLOR = (15, 15, 35)
FONT = cv2.FONT_HERSHEY_SIMPLEX

def load_model(model_path: str = "yolov8n.pt") -> YOLO:
    return YOLO(model_path)

def detect_people(model: YOLO, frame):

    results = model(frame, verbose=False)[0]
    detections = []

    for box in results.boxes:
        class_id = int(box.cls[0])
        if class_id != PERSON_CLASS_ID:
            continue
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        confidence = float(box.conf[0])
        detections.append((x1, y1, x2, y2, confidence))

    return detections

def draw_detections(frame, detections: list):

    count = len(detections)

    for x1, y1, x2, y2, confidence in detections:
        cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR, 2)

        label = f"{confidence:.0%}"
        label_size, baseline = cv2.getTextSize(label, FONT, 0.55, 1)
        label_y = max(y1 - 8, label_size[1]+4)
        cv2.rectangle(
            frame,
            (x1, label_y - label_size[1] - 4),
            (x1 + label_size[0] + 4, label_y + baseline),
            BOX_COLOR, cv2.FILLED
        )

        cv2.putText(frame, label, (x1 + 2, label_y), FONT, 0.55, TEXT_COLOR, 1)
    badge_text = f"People: {count}"
    badge_size, _ = cv2.getTextSize(badge_text, FONT, 0.8, 2)

    pad = 10
    cv2.rectangle(
        frame,
        (pad, pad),
        (pad * 2 + badge_size[0], pad * 2 + badge_size[1]),
        COUNT_BG_COLOR, cv2.FILLED
    )
    cv2.putText(
        frame, badge_text,
        (pad + 5, pad + badge_size[1] + 2),
        FONT, 0.8, (0, 230, 120), 2
    )

    return frame

def process_video(model: YOLO, input_path: str, output_path: str) -> int:

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {input_path}")
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

    tmp_fd, tmp_path = tempfile.mkstemp(suffix="_tmp.mp4")
    os.close(tmp_fd)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(tmp_path, fourcc, fps, (width, height))

    max_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        detections = detect_people(model, frame)
        max_count = max(max_count, len(detections))
        annotated = draw_detections(frame, detections)
        writer.write(annotated)

    cap.release()
    writer.release()

    if shutil.which("ffmpeg"):
        cmd = [
            "ffmpeg", "-y",
            "-i", tmp_path,
            "-vcodec", "libx264",
            "-crf", "23",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True)
        os.remove(tmp_path)
        print("Correct encoding")
        if result.returncode != 0:
            raise RuntimeError("ffmpeg re-encode failed: \n"+ result.stderr.decode())
        else:
            pass
    else:
        print("Doing default encoding not working with the browser")
        shutil.move(tmp_path, output_path)

    return max_count