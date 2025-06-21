import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.exception_handlers import http_exception_handler
from routers.learning_router import router as learning_router
from routers.detection_router import router as detection_router
from routers.mqtt_router import router as mqtt_router
from routers import rtsp_router, html_router
from services.face_detection_service import startup_event
from services.rtsp_service import rtsp_service
from services.streaming_service import streaming_service
from mqtt_handler import mqtt
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "dashboard")

app = FastAPI(
    title="RTSP CCTV 모니터링",
    description="실시간 움직임 감지 및 얼굴 인식 시스템",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    try:
        logger.info("애플리케이션 시작...")
    
        await startup_event()
        streaming_service.set_rtsp_service(rtsp_service)

        if not os.path.exists(STATIC_DIR):
            logger.warning(f"정적 파일 디렉토리가 없음: {STATIC_DIR}")
            os.makedirs(STATIC_DIR, exist_ok=True)
        
        logger.info("RTSP CCTV 모니터링 시스템이 시작되었습니다.")
    except Exception as e:
        logger.error(f"시작 오류: {e}")

@app.on_event("shutdown")
async def shutdown():
    try:
        logger.info("애플리케이션 종료...")
        
        # RTSP 서비스 정리
        try:
            from services.rtsp_service import rtsp_service
            await rtsp_service.disconnect()
        except ImportError:
            logger.info("RTSP 서비스가 초기화되지 않음.")
        except Exception as e:
            logger.error(f"RTSP 서비스 종료 오류: {e}")
        
        logger.info("애플리케이션이 종료되었습니다.")
    except Exception as e:
        logger.error(f"종료 오류: {e}")

# API 라우터 등록
app.include_router(learning_router)
app.include_router(detection_router)
app.include_router(rtsp_router.router)
app.include_router(html_router.router)
app.include_router(mqtt_router)

mqtt.init_app(app)

# 정적 파일 서빙
if os.path.exists(STATIC_DIR):
    app.mount("/dashboard", StaticFiles(directory=STATIC_DIR, html=True), name="dashboard")
    logger.info(f"정적 파일 디렉토리 마운트: {STATIC_DIR}")

# 루트 경로 리다이렉션
@app.get("/")
async def root():
    return {"message": "RTSP CCTV 모니터링 시스템", "dashboard": "/rtsp/dashboard"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
