import os
import re
import cv2
import numpy as np
import tempfile
import asyncio
import logging
from typing import Dict, Any
from core.config import settings
from insightface.app import FaceAnalysis
 
logger = logging.getLogger(__name__)

MIN_FACE_SIZE = 60

def safe_filename(name: str) -> str:
    """파일명으로 안전한 문자열로 변환"""
    return re.sub(r'[^a-zA-Z0-9_\-가-힣]', '_', name)

async def run_ffmpeg_convert(input_path: str, output_path: str) -> None:
    """ffmpeg를 실행하여 webm -> mp4 변환 (비동기 wrapper)"""
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-i", input_path, "-c:v", "libx264", "-preset", "ultrafast", output_path, "-y",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        err_msg = stderr.decode().strip()
        raise RuntimeError(f"ffmpeg 변환 실패: {err_msg}")

face_app = FaceAnalysis(
    name="buffalo_l",
    root= settings.KNOWN_FACES_DIR,
    providers = ['CUDAExecutionProvi','CPUExecutionProvider']
)
# GPU 사용 위해 ctx_id=0, CPU는 -1
face_app.prepare(ctx_id=0, det_size=(640, 640))

async def learn_new_face_from_video(person_name: str, video_bytes: bytes) -> Dict[str, Any]:
    person_name = safe_filename(person_name)
    person_dir = os.path.join(settings.KNOWN_FACES_DIR, person_name)
    os.makedirs(person_dir, exist_ok=True)

    webm_path = None
    mp4_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm", dir= settings.KNOWN_FACES_DIR + "/tmp") as webm_file:
            webm_file.write(video_bytes)
            webm_path = webm_file.name

        mp4_path = webm_path.replace(".webm", ".mp4")

        try:
            await run_ffmpeg_convert(webm_path, mp4_path)
        except FileNotFoundError:
            return {"error": "ffmpeg가 설치되어 있지 않습니다."}
        except RuntimeError as e:
            return {"error": str(e)}

        cap = cv2.VideoCapture(mp4_path)
        if not cap.isOpened():
            return {"error": "비디오 파일을 열 수 없습니다."}

        frame_count = 0
        saved_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % 3 == 0: 
                faces = face_app.get(frame)
                valid_faces = [face for face in faces
                               if (face.bbox[3] - face.bbox[1]) >= MIN_FACE_SIZE and
                                  (face.bbox[2] - face.bbox[0]) >= MIN_FACE_SIZE]

                for i, face in enumerate(valid_faces):
                    try:
                        embedding = face.embedding  # (512,) numpy array
                        np.save(os.path.join(person_dir, f"{frame_count}_{i}.npy"), embedding)
                        saved_count += 1
                    except Exception as e:
                        logger.warning(f"[인코딩 에러] frame {frame_count} 얼굴 {i}: {e}")

            frame_count += 1

        cap.release()

        return {
            "person_name": person_name,
            "samples": saved_count,
            "message": f"{saved_count}개 샘플 학습 완료 (GPU 지원)"
        }

    finally:
        for path in (webm_path, mp4_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    logger.warning(f"임시 파일 삭제 실패: {path}, {e}")
