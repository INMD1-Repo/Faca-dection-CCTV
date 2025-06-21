import cv2
import asyncio
import threading
import logging
import queue
import time
import os
import socket
from typing import Optional, Callable
from datetime import datetime
from urllib.parse import urlparse
from core.config import settings
from services.motion_detection_service import motion_service
from services.mqtt_service import MQTTService

logger = logging.getLogger(__name__)

class RTSPService:
    def __init__(self):
        self.rtsp_url = None
        self.cap = None
        self.is_running = False
        self.is_connected = False
        self.frame_queue = queue.Queue(maxsize=3)
        self.current_frame = None
        self.capture_thread = None
        self.detection_enabled = True
        self.latest_detections = []
        self.detection_callbacks = []
        self.connection_timeout = 10  # 10초 타임아웃
        self.last_frame_time = time.time()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.successful_frames = 0
        self.decode_errors = 0
        
    def _validate_rtsp_url(self, url: str) -> bool:
        """RTSP URL 형식 검증"""
        if not url:
            return False
        
        # 기본적인 RTSP URL 형식 검증
        if not url.startswith(('rtsp://', 'rtmp://', 'http://')):
            logger.error(f"지원하지 않는 프로토콜: {url}")
            return False
        
        return True
        
    def set_rtsp_url(self, url: str):
        """RTSP URL 설정 (오류 허용 옵션 포함)"""
        if not self._validate_rtsp_url(url):
            raise ValueError(f"유효하지 않은 RTSP URL: {url}")
        
        # 디코딩 오류 허용을 위한 환경 변수 설정
        os.environ.update({
            "OPENCV_FFMPEG_CAPTURE_OPTIONS": (
                "rtsp_transport;tcp;"
                "stimeout;10000000;"
                "reorder_queue_size;0;"  # RTP 재정렬 큐 비활성화
                "err_detect;ignore_err;"
                "fflags;+igndts+ignidx;"
                "skip_frame;nokey"  # 키프레임이 아닌 손상된 프레임 건너뛰기
            ),
            "OPENCV_LOG_LEVEL": "ERROR"  # OpenCV 로그 레벨 조정
        })
        
        self.rtsp_url = url
        logger.info(f"RTSP URL 설정 (오류 허용 모드): {url}")
        
    def check_network_connectivity(self) -> bool:
        """네트워크 연결 상태 확인"""
        try:
            if not self.rtsp_url:
                return False
                
            parsed = urlparse(self.rtsp_url)
            host = parsed.hostname
            port = parsed.port or 554
            
            # 소켓 연결 테스트
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            return result == 0
        except Exception as e:
            logger.error(f"네트워크 연결 확인 실패: {e}")
            return False
        
    async def connect(self) -> bool:
        """RTSP 스트림 연결 (RTP 오류 허용)"""
        try:
            if not self.rtsp_url:
                logger.error("RTSP URL이 설정되지 않음")
                return False
                
            logger.info(f"RTSP 연결 시도: {self.rtsp_url}")
            
            # 네트워크 연결 확인
            if not self.check_network_connectivity():
                logger.error("네트워크 연결 불가")
                return False
            
            # 기존 연결이 있다면 해제
            if self.cap:
                self.cap.release()
                time.sleep(1)  # 카메라 정리 시간 제공
                self.cap = None
            
            # TCP 프로토콜 강제 사용
            rtsp_url_with_tcp = f"{self.rtsp_url}?tcp" if "?" not in self.rtsp_url else f"{self.rtsp_url}&tcp"
            
            # OpenCV VideoCapture 생성
            self.cap = cv2.VideoCapture(rtsp_url_with_tcp, cv2.CAP_FFMPEG)
            
            # 연결 확인
            if not self.cap.isOpened():
                logger.error("VideoCapture 객체 생성 실패")
                return False
            
            # 버퍼 설정 (버전 호환성 고려)
            try:
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except AttributeError:
                try:
                    self.cap.set(cv2.CAP_PROP_BUFFER_SIZE, 1)
                except AttributeError:
                    logger.warning("버퍼 크기 설정 불가 - OpenCV 버전 문제")
            
            # FPS 설정
            try:
                self.cap.set(cv2.CAP_PROP_FPS, 15)
            except AttributeError:
                logger.warning("FPS 설정 불가 - OpenCV 버전 문제")
            
            # 타임아웃 설정
            try:
                self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, self.connection_timeout * 1000)
                self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)  # 5초 읽기 타임아웃
            except AttributeError:
                logger.warning("타임아웃 설정 불가 - OpenCV 버전 문제")
                
            # 연결 테스트 (여러 번 시도)
            for attempt in range(5):
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.is_connected = True
                    self.last_frame_time = time.time()
                    self.reconnect_attempts = 0
                    logger.info("RTSP 연결 성공")
                    return True
                time.sleep(0.2)
            
            logger.error("RTSP 연결 실패")
            if self.cap:
                self.cap.release()
                self.cap = None
            return False
                
        except Exception as e:
            logger.error(f"RTSP 연결 오류: {e}")
            if self.cap:
                self.cap.release()
                self.cap = None
            return False
    
    async def connect_with_retry(self, max_retries: int = 3) -> bool:
        """재시도 로직이 포함된 RTSP 연결"""
        for attempt in range(max_retries):
            try:
                logger.info(f"RTSP 연결 시도 {attempt + 1}/{max_retries}")
                
                if await self.connect():
                    return True
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # 2초 대기 후 재시도
                    
            except Exception as e:
                logger.error(f"연결 시도 {attempt + 1} 실패: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
        
        logger.error("모든 연결 시도 실패")
        return False
    
    def start_streaming(self):
        """스트리밍 시작"""
        if self.is_running or not self.is_connected:
            return
            
        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.capture_thread.start()
        logger.info("RTSP 스트리밍 시작")
    
    def stop_streaming(self):
        """스트리밍 중지"""
        self.is_running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=3)
        logger.info("RTSP 스트리밍 중지")
    
    def _is_frame_corrupted(self, frame) -> bool:
        """프레임 손상 여부 간단 검사"""
        try:
            if frame is None or frame.size == 0:
                return True
            
            # 평균 밝기가 비정상적으로 낮거나 높은 경우
            mean_brightness = cv2.mean(frame)[0]
            if mean_brightness < 5 or mean_brightness > 250:
                return True
                
            return False
        except:
            return True
    
    def _capture_worker(self):
        """프레임 캡처 워커 (디코딩 오류 허용)"""
        consecutive_failures = 0
        max_consecutive_failures = 20  # 연속 실패 허용 횟수 증가
        rtp_error_count = 0
        
        while self.is_running and consecutive_failures < max_consecutive_failures:
            try:
                # 연결 상태 확인
                if not self.cap or not self.cap.isOpened():
                    logger.warning("VideoCapture가 열려있지 않음, 재연결 시도")
                    if not asyncio.run(self.connect()):
                        consecutive_failures += 1
                        time.sleep(2)
                        continue
                    consecutive_failures = 0
                    rtp_error_count = 0
                
                ret, frame = self.cap.read()
                
                # 프레임 읽기 실패 시 처리
                if not ret or frame is None:
                    consecutive_failures += 1
                    self.decode_errors += 1
                    
                    # 디코딩 오류는 경고 레벨로 처리 (너무 많은 로그 방지)
                    if consecutive_failures % 10 == 0:
                        logger.warning(f"프레임 디코딩 오류 발생 중 ({consecutive_failures}회)")
                    
                    # RTP 오류가 많이 발생하면 재연결
                    if consecutive_failures > 15:
                        logger.warning("연속 프레임 읽기 실패, 재연결 시도")
                        asyncio.run(self.disconnect())
                        time.sleep(3)  # 충분한 대기 시간
                        continue
                    
                    # 짧은 대기 후 다음 프레임 시도
                    time.sleep(0.05)
                    continue
                
                # 성공적으로 프레임을 읽었을 때
                consecutive_failures = 0
                self.successful_frames += 1
                self.current_frame = frame
                self.last_frame_time = time.time()
                
                # 프레임 품질 검사 (선택적)
                if self._is_frame_corrupted(frame):
                    logger.debug("손상된 프레임 감지, 건너뛰기")
                    continue
                
                # 기존 프레임 큐 비우기
                while not self.frame_queue.empty():
                    try:
                        self.frame_queue.get_nowait()
                    except queue.Empty:
                        break
                
                # 움직임 감지 및 처리
                try:
                    if self.detection_enabled:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        processed_frame = loop.run_until_complete(
                            motion_service.process_motion_detection(frame)
                        )
                        loop.close()
                        
                        try:
                            self.frame_queue.put_nowait(processed_frame)
                        except queue.Full:
                            pass
                    else:
                        try:
                            self.frame_queue.put_nowait(frame)
                        except queue.Full:
                            pass
                except Exception as motion_error:
                    logger.error(f"움직임 감지 처리 오류: {motion_error}")
                    # 원본 프레임이라도 큐에 추가
                    try:
                        self.frame_queue.put_nowait(frame)
                    except queue.Full:
                        pass
                        
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"프레임 캡처 오류: {e}")
                time.sleep(0.5)
        
        # 정리 작업
        if self.cap:
            self.cap.release()
            self.cap = None
        self.is_connected = False
        
        logger.info(f"프레임 캡처 종료 (성공: {self.successful_frames}프레임, 실패: {consecutive_failures}회)")
    
    def get_frame_generator(self):
        """프레임 제너레이터 (스트리밍용)"""
        empty_frame_count = 0
        max_empty_frames = 10
        
        while empty_frame_count < max_empty_frames:
            try:
                frame = self.frame_queue.get(timeout=2.0)
                empty_frame_count = 0  # 프레임을 받았으므로 카운트 리셋
                
                # 프레임 크기 조정
                height, width = frame.shape[:2]
                if width > 800:
                    scale = 800 / width
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    frame = cv2.resize(frame, (new_width, new_height))
                
                # JPEG 인코딩
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                           
            except queue.Empty:
                empty_frame_count += 1
                logger.warning(f"프레임 큐 비어있음 ({empty_frame_count}/{max_empty_frames})")
                # 빈 프레임 전송
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + b'' + b'\r\n')
            except Exception as e:
                logger.error(f"프레임 제너레이터 오류: {e}")
                break
        
        logger.error("프레임 제너레이터 종료 - 너무 많은 빈 프레임")
    
    async def handle_motion_detection(self, frame, timestamp):
        """움직임 감지 시 얼굴 인식 수행"""
        try:
            logger.info("얼굴 인식 시작...")
            
            # 프레임 품질 개선
            enhanced_frame = self._enhance_frame_for_recognition(frame)
            
            # 프레임을 바이트로 변환
            ret, buffer = cv2.imencode('.jpg', enhanced_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ret:
                logger.error("프레임 인코딩 실패")
                return
            
            image_bytes = buffer.tobytes()
            
            # 얼굴 인식 수행 (수정된 부분)
            try:
                from services.face_detection_service import face_detection_service
                face_results = await face_detection_service.detect_and_recognize_faces(image_bytes)
            except ImportError as import_error:
                logger.error(f"얼굴 인식 서비스 import 실패: {import_error}")
                face_results = []
            except Exception as face_error:
                logger.warning(f"얼굴 인식 서비스 오류: {face_error}")
                face_results = []
            
            # 감지 결과 저장
            detection_data = {
                "timestamp": timestamp.isoformat(),
                "faces": face_results,
                "image_size": len(image_bytes),
                "motion_type": "RTSP Motion Detection"
            }
            
            await MQTTService.publish_motion_and_face_detection({
                "location": "rtsp_camera",
                "person_detected": bool(face_results),
                "confidence": max([f.get("confidence", 0.0) for f in face_results], default=0.0)
            })
                        
            self.latest_detections.append(detection_data)
            
            if len(self.latest_detections) > 20:
                self.latest_detections.pop(0)
            
            # 결과 로깅
            if face_results:
                for face in face_results:
                    logger.info(f"얼굴 감지: {face['name']}, 신뢰도: {face['confidence']:.3f}")
                    #만약에 얼굴 감지에 `알 수 없음`이 있으면 경고 울리기 위해 알림 보내기
            else:
                logger.info("얼굴이 감지되지 않음")
                
            # 콜백 실행
            for callback in self.detection_callbacks:
                try:
                    await callback(detection_data)
                except Exception as callback_error:
                    logger.error(f"감지 콜백 실행 오류: {callback_error}")
                
        except Exception as e:
            logger.error(f"얼굴 인식 처리 오류: {e}")
    
    def _enhance_frame_for_recognition(self, frame):
        """얼굴 인식을 위한 프레임 품질 개선"""
        try:
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
            
            return enhanced
        except:
            return frame
    
    def detect_faces_opencv(self, image_bytes) -> list:
        """OpenCV를 사용한 기본 얼굴 감지"""
        try:
            import numpy as np
            
            # 바이트를 이미지로 변환
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return []
            
            # OpenCV Haar Cascade 얼굴 감지
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            # 결과 포맷팅
            face_results = []
            for (x, y, w, h) in faces:
                face_results.append({
                    "bounding_box": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                    "confidence": 0.8,  # 기본 신뢰도
                    "is_known": False,
                    "name": "Unknown"
                })
            
            return face_results
            
        except Exception as e:
            logger.error(f"OpenCV 얼굴 감지 오류: {e}")
            return []
    
    def add_detection_callback(self, callback: Callable):
        """감지 콜백 추가"""
        self.detection_callbacks.append(callback)
    
    def get_latest_detections(self):
        """최근 감지 결과 반환"""
        return self.latest_detections
    
    def get_current_snapshot(self) -> Optional[bytes]:
        """현재 프레임 스냅샷 반환"""
        if self.current_frame is not None:
            try:
                ret, buffer = cv2.imencode('.jpg', self.current_frame)
                if ret:
                    return buffer.tobytes()
            except Exception as e:
                logger.error(f"스냅샷 생성 오류: {e}")
        return None
    
    def get_connection_status(self) -> dict:
        """연결 상태 정보 반환"""
        return {
            "is_connected": self.is_connected,
            "is_running": self.is_running,
            "rtsp_url": self.rtsp_url,
            "last_frame_time": self.last_frame_time,
            "reconnect_attempts": self.reconnect_attempts,
            "frame_queue_size": self.frame_queue.qsize(),
            "detection_enabled": self.detection_enabled
        }
    
    def get_stream_statistics(self) -> dict:
        """스트림 통계 정보 반환"""
        return {
            "is_connected": self.is_connected,
            "is_running": self.is_running,
            "successful_frames": self.successful_frames,
            "decode_errors": self.decode_errors,
            "last_frame_time": self.last_frame_time,
            "frame_queue_size": self.frame_queue.qsize()
        }
    
    def enable_detection(self, enabled: bool = True):
        """움직임 감지 활성화/비활성화"""
        self.detection_enabled = enabled
        logger.info(f"움직임 감지 {'활성화' if enabled else '비활성화'}")
    
    async def disconnect(self):
        """연결 해제 (적절한 정리)"""
        logger.info("RTSP 연결 해제 시작")
        
        # 스트리밍 중지
        self.stop_streaming()
        
        # VideoCapture 적절히 해제
        if self.cap:
            # 몇 개의 프레임을 더 읽어서 버퍼 정리
            for _ in range(3):
                try:
                    self.cap.read()
                except:
                    break
            
            self.cap.release()
            self.cap = None
            # 카메라가 연결을 정리할 시간 제공
            time.sleep(2) 
        
        # 상태 초기화
        self.is_connected = False
        self.is_running = False
        self.current_frame = None
        
        # 큐 비우기
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break
        
        logger.info("RTSP 연결 해제 완료")

rtsp_service = RTSPService()

# 움직임 감지 콜백 등록 (에려반환을 위해)
try:
    motion_service.add_motion_callback(rtsp_service.handle_motion_detection)
    logger.info("움직임 감지 콜백 등록 완료")
except Exception as e:
    logger.error(f"움직임 감지 콜백 등록 실패: {e}")

