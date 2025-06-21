import cv2
import threading
import queue
import time
import logging
from typing import Optional, Generator
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

class StreamingService:
    def __init__(self):
        self.rtsp_service = None
        
    def set_rtsp_service(self, rtsp_service):
        """RTSP 서비스 설정"""
        self.rtsp_service = rtsp_service
        logger.info("RTSP 서비스가 스트리밍 서비스에 설정됨")
        
    def get_frame_generator(self) -> Generator[bytes, None, None]:
        """프레임 제너레이터 (개선된 버전)"""
        if not self.rtsp_service:
            logger.error("RTSP 서비스가 설정되지 않음")
            # 에러 이미지 생성
            error_frame = self._create_error_frame("RTSP 서비스가 연결되지 않음")
            while True:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n')
                time.sleep(1)
        
        if not self.rtsp_service.is_connected:
            logger.warning("RTSP가 연결되지 않음")
            error_frame = self._create_error_frame("RTSP 연결 대기 중...")
            while not self.rtsp_service.is_connected:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n')
                time.sleep(1)
        
        # RTSP 서비스의 프레임 제너레이터 사용
        try:
            frame_generator = self.rtsp_service.get_frame_generator()
            for frame_data in frame_generator:
                yield frame_data
        except Exception as e:
            logger.error(f"스트리밍 중 오류: {e}")
            error_frame = self._create_error_frame(f"스트리밍 오류: {str(e)}")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n')
    
    def _create_error_frame(self, message: str) -> bytes:
        """오류 메시지가 포함된 프레임 생성"""
        try:
            import numpy as np
            
            # 640x480 검은 이미지 생성
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # 텍스트 추가
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            color = (255, 255, 255)  # 흰색
            thickness = 2
            
            # 텍스트 크기 계산
            text_size = cv2.getTextSize(message, font, font_scale, thickness)[0]
            text_x = (img.shape[1] - text_size[0]) // 2
            text_y = (img.shape[0] + text_size[1]) // 2
            
            cv2.putText(img, message, (text_x, text_y), font, font_scale, color, thickness)
            
            # JPEG로 인코딩
            ret, buffer = cv2.imencode('.jpg', img)
            if ret:
                return buffer.tobytes()
            else:
                return b''
        except Exception as e:
            logger.error(f"오류 프레임 생성 실패: {e}")
            return b''
    
    @property
    def is_streaming(self) -> bool:
        """스트리밍 상태"""
        return self.rtsp_service.is_running if self.rtsp_service else False
    
    def get_status(self) -> dict:
        """스트리밍 상태 정보"""
        if not self.rtsp_service:
            return {
                "is_streaming": False,
                "is_connected": False,
                "error": "RTSP 서비스가 설정되지 않음"
            }
        
        return {
            "is_streaming": self.rtsp_service.is_running,
            "is_connected": self.rtsp_service.is_connected,
            "rtsp_url": self.rtsp_service.rtsp_url,
            "frame_queue_size": self.rtsp_service.frame_queue.qsize() if hasattr(self.rtsp_service, 'frame_queue') else 0
        }

# 전역 인스턴스
streaming_service = StreamingService()
