import cv2
import numpy as np
import asyncio
import threading
import logging
from typing import Optional, Callable, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class MotionDetectionService:
    def __init__(self):
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=True, 
            varThreshold=50
        )
        self.is_running = False
        self.motion_callbacks = []
        self.last_motion_time = None
        self.motion_cooldown = 3  # 3초 쿨다운
        
    def add_motion_callback(self, callback: Callable):
        """움직임 감지 콜백 추가"""
        self.motion_callbacks.append(callback)
        
    def detect_motion(self, frame: np.ndarray) -> tuple[bool, np.ndarray]:
        """프레임에서 움직임 감지"""
        try:
            # 프레임 유효성 검사
            if frame is None or not isinstance(frame, np.ndarray) or frame.ndim != 3:
                logger.warning(f"잘못된 프레임 입력: {type(frame)}, shape: {getattr(frame, 'shape', None)}")
                return False, np.zeros((1, 1, 3), dtype=np.uint8)

            # 그레이스케일 변환
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            
            # 배경 차분 적용
            fg_mask = self.background_subtractor.apply(gray)
            
            # 노이즈 제거
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
            
            # 윤곽선 찾기
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            motion_detected = False
            motion_frame = frame.copy()
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 500:  # 최소 면적 임계값
                    motion_detected = True
                    x, y, w, h = cv2.boundingRect(contour)
                    cv2.rectangle(motion_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(motion_frame, "Motion Detected", (10, 30), 
                              cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            return motion_detected, motion_frame
            
        except Exception as e:
            logger.error(f"움직임 감지 오류: {e}")
            return False, frame if frame is not None else np.zeros((1, 1, 3), dtype=np.uint8)
    
    async def process_motion_detection(self, frame: np.ndarray):
        """움직임 감지 처리 및 콜백 실행"""
        try:
            motion_detected, processed_frame = self.detect_motion(frame)
            
            if motion_detected:
                current_time = datetime.now()
                
                # 쿨다운 체크
                if (self.last_motion_time is None or 
                    (current_time - self.last_motion_time).seconds >= self.motion_cooldown):
                    
                    self.last_motion_time = current_time
                    logger.info("움직임 감지됨 - 얼굴 인식 시작")
                    
                    # 모든 콜백 실행
                    for callback in self.motion_callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(frame, current_time)
                            else:
                                callback(frame, current_time)
                        except Exception as e:
                            logger.error(f"움직임 콜백 오류: {e}")
            
            return processed_frame
            
        except Exception as e:
            logger.error(f"움직임 감지 처리 오류: {e}")
            return frame if frame is not None else np.zeros((1, 1, 3), dtype=np.uint8)

# 전역 인스턴스
motion_service = MotionDetectionService()
