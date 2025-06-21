from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
import cv2
import tempfile
import os
import logging
from services.face_detection_service import detect_and_recognize_faces, face_detection_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["HTML Pages"])

def read_html_file(filename: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "dashboard", filename)
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"HTML 파일 누락: {path}")
        raise HTTPException(status_code=404, detail="페이지를 찾을 수 없음")

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return read_html_file("monitoring.html")

@router.get("/defect", response_class=HTMLResponse)
async def defect_page():
    return read_html_file("defect.html")

@router.get("/recoding", response_class=HTMLResponse)
async def recoding_page():
    return read_html_file("recoding.html")

@router.post("/detect")
async def detect_faces(image: UploadFile = File(...)):
    try:
        image_bytes = await image.read()
        results = await detect_and_recognize_faces(image_bytes)
        formatted = [{
            "name": res["name"],
            "confidence": res["confidence"],
            "box": [
                res["location"]["left"],
                res["location"]["top"],
                res["location"]["right"],
                res["location"]["bottom"]
            ]
        } for res in results]
        return formatted
    except Exception as e:
        raise HTTPException(500, f"얼굴 인식 오류: {str(e)}")

@router.post("/learn/video")
async def learn_from_video(
    personname: str = Form(...),
    videofile: UploadFile = File(...)
):
    try:
        video_bytes = await videofile.read()
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

        cap = cv2.VideoCapture(tmp_path)
        success_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if cap.get(cv2.CAP_PROP_POS_FRAMES) % 10 == 0:
                success = await face_detection_service.add_known_face(frame, personname)
                if success:
                    success_count += 1

        cap.release()
        os.unlink(tmp_path)

        if success_count > 0:
            return {"message": f"{personname}님의 얼굴 {success_count}개 학습 완료"}
        else:
            raise HTTPException(400, "비디오에서 얼굴을 찾을 수 없음")
    except Exception as e:
        raise HTTPException(500, f"비디오 처리 오류: {str(e)}")
