from fastapi import APIRouter, File, UploadFile, HTTPException
from services.face_detection_service import detect_and_recognize_faces
from typing import List, Dict, Any

router = APIRouter(prefix="/detection", tags=["Face Detection"])

@router.post("/detect", response_model=List[Dict[str, Any]])
async def recognize_faces_endpoint(image: UploadFile = File(...)) -> List[Dict[str, Any]]:
    """
    얼굴 인식 API 엔드포인트
    - image: 업로드된 이미지 파일 (JPEG, PNG 지원)
    """
    content_type = image.content_type.lower()
    if content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="지원하지 않는 이미지 타입입니다.")
    
    image_bytes = await image.read()
    
    try:
        faces = await detect_and_recognize_faces(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"얼굴 인식 처리 중 오류가 발생했습니다: {e}")
    
    return faces
