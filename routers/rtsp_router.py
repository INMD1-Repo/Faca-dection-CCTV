from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
import cv2
import tempfile
import os
import logging
import numpy as np

from services.rtsp_service import rtsp_service
from services.streaming_service import streaming_service
from services.face_detection_service import face_detection_service, detect_and_recognize_faces
from services.mqtt_service import MQTTService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rtsp", tags=["RTSP"])

class RTSPConfig(BaseModel):
    rtsp_url: str
    username: Optional[str] = None
    password: Optional[str] = None

class RTSPStatus(BaseModel):
    is_connected: bool
    is_streaming: bool
    detection_enabled: bool
    latest_detections: List[Dict[str, Any]]
    rtsp_url: Optional[str]

@router.post("/connect")
async def connect_rtsp(config: RTSPConfig):
    try:
        rtsp_service.set_rtsp_url(config.rtsp_url)
        success = await rtsp_service.connect()
        if success:
            streaming_service.set_rtsp_service(rtsp_service)
            return {
                "status": "connected",
                "message": "RTSP 연결 성공",
                "rtsp_url": config.rtsp_url
            }
        raise HTTPException(500, "RTSP 연결 실패")
    except Exception as e:
        raise HTTPException(500, f"연결 오류: {str(e)}")

@router.post("/start-streaming")
async def start_streaming(background_tasks: BackgroundTasks):
    if not rtsp_service.is_connected:
        raise HTTPException(400, "RTSP 연결 필요")
    try:
        rtsp_service.start_streaming()
        return {"status": "started", "message": "스트리밍 시작"}
    except Exception as e:
        raise HTTPException(500, f"스트리밍 시작 오류: {str(e)}")

@router.post("/stop-streaming")
async def stop_streaming():
    try:
        rtsp_service.stop_streaming()
        return {"status": "stopped", "message": "스트리밍 중지"}
    except Exception as e:
        raise HTTPException(500, f"스트리밍 중지 오류: {str(e)}")

@router.get("/status", response_model=RTSPStatus)
async def get_status():
    return RTSPStatus(
        is_connected=rtsp_service.is_connected,
        is_streaming=rtsp_service.is_running,
        detection_enabled=rtsp_service.detection_enabled,
        latest_detections=rtsp_service.get_latest_detections(),
        rtsp_url=rtsp_service.rtsp_url
    )

@router.post("/manual-detect")
async def manual_detect():
    sensor_data = {
        "location": "lab",
        "person_detected": False,
        "confidence": 0.12
    }
    await MQTTService.publish_motion_and_face_detection(sensor_data)
    return {"message": "MQTT 이벤트 발행 완료"}

@router.get("/snapshot")
async def get_snapshot():
    if not rtsp_service.is_connected:
        raise HTTPException(400, "RTSP 연결 필요")
    try:
        image_bytes = rtsp_service.get_current_snapshot()
        if image_bytes:
            return Response(content=image_bytes, media_type="image/jpeg")
        raise HTTPException(404, "스냅샷 없음")
    except Exception as e:
        raise HTTPException(500, f"스냅샷 오류: {str(e)}")

@router.get("/stream")
async def video_stream():
    try:
        logger.info("비디오 스트림 요청 받음")
        return StreamingResponse(
            streaming_service.get_frame_generator(),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "Connection": "close"
            }
        )
    except Exception as e:
        logger.error(f"스트림 엔드포인트 오류: {e}")
        raise HTTPException(status_code=500, detail=f"스트리밍 오류: {str(e)}")

@router.get("/stream/status")
async def stream_status():
    return streaming_service.get_status()

@router.get("/detections")
async def get_detections():
    return {"detections": rtsp_service.get_latest_detections()}

@router.post("/toggle-detection")
async def toggle_detection():
    rtsp_service.detection_enabled = not rtsp_service.detection_enabled
    status = "활성화" if rtsp_service.detection_enabled else "비활성화"
    return {"status": status, "enabled": rtsp_service.detection_enabled}
