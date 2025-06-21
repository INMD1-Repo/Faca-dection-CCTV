from pydantic_settings import BaseSettings
from typing import ClassVar
import os

class Settings(BaseSettings):
    # 모델 저장 경로
    MODEL_STORAGE_PATH: str = "/home/embednull/Desktop/Project/model_storage"
    SIMILARITY_THRESHOLD: float = 0.6
    KNOWN_FACES_DIR: ClassVar[str] = os.path.join(MODEL_STORAGE_PATH)
    
    # RTSP 설정
    RTSP_URL: str = "rtsp://admin:password@192.168.0.100:554/stream1"
    RTSP_USERNAME: str = "admin"
    RTSP_PASSWORD: str = "password"
    RTSP_HOST: str = "192.168.0.100"
    RTSP_PORT: int = 554
    
    # 움직임 감지 설정
    MOTION_DETECTION_ENABLED: bool = True
    MOTION_THRESHOLD: int = 30
    MOTION_AREA_THRESHOLD: int = 500
    FACE_DETECTION_ON_MOTION: bool = True
    
    # 로깅
    LOG_LEVEL: str = "INFO"

settings = Settings()
