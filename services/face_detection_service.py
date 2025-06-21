import os
import cv2
import numpy as np
from typing import List, Dict, Any, Optional
import logging
from core.config import settings

try:
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False
    logging.warning("33 설치되지 않았습니다. pip install insightface로 설치하세요.")

logger = logging.getLogger(__name__)

class FaceDetectionService:
    def __init__(self):
        self._app: Optional[FaceAnalysis] = None
        self._known_faces_cache: Optional[Dict[str, List[np.ndarray]]] = None
        self._cache_timestamp: float = 0
            
    def _get_face_app(self) -> FaceAnalysis:
        """FaceAnalysis 객체를 지연 초기화"""
        if not INSIGHTFACE_AVAILABLE:
            raise ImportError("InsightFace가 설치되지 않았습니다.")
            
        if self._app is None:
            try:
                self._app = FaceAnalysis(
                    name='buffalo_l', 
                    providers=['CUDAExecutionProvider','CPUExecutionProvider']
		)
                self._app.prepare(ctx_id=0, det_size=(640, 640))
                logger.info("FaceAnalysis 모델이 성공적으로 로드되었습니다.")
            except Exception as e:
                logger.error(f"FaceAnalysis 모델 로드 실패: {e}")
                try:
                    self._app = FaceAnalysis(
                        name='buffalo_l', 
                        providers=['CUDAExecutionProvider','CPUExecutionProvider']
                    )
                    self._app.prepare(ctx_id=-1, det_size=(640, 640))
                    logger.info("CPU 모드로 FaceAnalysis 모델이 로드되었습니다.")
                except Exception as e2:
                    logger.error(f"CPU 모드 FaceAnalysis 모델 로드도 실패: {e2}")
                    raise e2
        return self._app
    
    def load_known_faces(self, force_reload: bool = False) -> Dict[str, List[np.ndarray]]:
        """알려진 얼굴 데이터를 캐시와 함께 로드"""
        current_time = os.path.getmtime(settings.KNOWN_FACES_DIR) if os.path.exists(settings.KNOWN_FACES_DIR) else 0
        
        if (self._known_faces_cache is None or 
            force_reload or 
            current_time > self._cache_timestamp):
            
            known_faces = {}
            
            if not os.path.exists(settings.KNOWN_FACES_DIR):
                logger.warning(f"알려진 얼굴 디렉토리가 존재하지 않습니다: {settings.KNOWN_FACES_DIR}")
                return known_faces
            
            try:
                for person_name in os.listdir(settings.KNOWN_FACES_DIR):
                    person_dir = os.path.join(settings.KNOWN_FACES_DIR, person_name)
                    if not os.path.isdir(person_dir):
                        continue
                    
                    embeddings = []
                    for file in os.listdir(person_dir):
                        if file.endswith(".npy"):
                            try:
                                emb = np.load(os.path.join(person_dir, file))
                                embeddings.append(emb)
                            except Exception as e:
                                logger.error(f"임베딩 파일 로드 실패 {file}: {e}")
                    
                    if embeddings:
                        known_faces[person_name] = embeddings
                        logger.info(f"{person_name}: {len(embeddings)}개 임베딩 로드됨")
                
                self._known_faces_cache = known_faces
                self._cache_timestamp = current_time
                
            except Exception as e:
                logger.error(f"알려진 얼굴 로드 중 오류: {e}")
                return {}
        
        return self._known_faces_cache

    def extract_face_embeddings(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """얼굴 탐지 및 임베딩 추출"""
        if not INSIGHTFACE_AVAILABLE:
            return []
            
        try:
            app = self._get_face_app()
            faces = app.get(image)
            
            results = []
            for face in faces:
                bbox = face.bbox.astype(int).tolist()
                embedding = face.embedding
                det_score = float(face.det_score)
                
                results.append({
                    "bbox": bbox, 
                    "embedding": embedding, 
                    "det_score": det_score
                })
            
            return results
            
        except Exception as e:
            logger.error(f"얼굴 임베딩 추출 실패: {e}")
            return []

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """코사인 유사도 계산"""
        try:
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
                
            return float(np.dot(a, b) / (norm_a * norm_b))
        except Exception:
            return 0.0

    def recognize_faces(self, image: np.ndarray, threshold: float = None) -> List[Dict[str, Any]]:
        """얼굴 인식 수행"""
        if threshold is None:
            threshold = settings.SIMILARITY_THRESHOLD
            
        detected = self.extract_face_embeddings(image)
        if not detected:
            return []
        
        known_faces = self.load_known_faces()
        recognized = []
        
        for face in detected:
            name = "알 수 없음"
            max_conf = 0.0
            emb = face['embedding']

            for person, embeddings in known_faces.items():
                for known_emb in embeddings:
                    sim = self.cosine_similarity(emb, known_emb)
                    if sim > max_conf and sim >= threshold:
                        max_conf = sim
                        name = person

            recognized.append({
                "name": name,
                "confidence": float(max_conf),
                "box": face["bbox"],
                "is_known": name != "알 수 없음",
                "detection_score": face["det_score"]
            })
            
        return recognized

    async def detect_and_recognize_faces(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """메인 얼굴 인식 함수 (바이트 데이터 처리)"""
        try:
            # 바이트를 OpenCV 이미지로 변환
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                logger.error("이미지 디코딩 실패")
                return []

            return self.recognize_faces(image)
            
        except Exception as e:
            logger.error(f"얼굴 인식 처리 중 오류: {e}")
            return []
        
    def add_known_face(self, person_name: str, image: np.ndarray) -> bool:
        """새로운 얼굴을 등록"""
        try:
            embeddings = self.extract_face_embeddings(image)
            if not embeddings:
                logger.warning("이미지에서 얼굴을 찾을 수 없습니다.")
                return False
            
            # 가장 높은 detection score를 가진 얼굴 선택
            best_face = max(embeddings, key=lambda x: x['det_score'])
            
            # 기존 임베딩 개수 확인
            person_dir = os.path.join(settings.KNOWN_FACES_DIR, person_name)
            existing_count = 0
            if os.path.exists(person_dir):
                existing_count = len([f for f in os.listdir(person_dir) if f.endswith('.npy')])
            
            # 임베딩 저장
            os.makedirs(person_dir, exist_ok=True)
            file_path = os.path.join(person_dir, f"{person_name}_{existing_count}.npy")
            np.save(file_path, best_face['embedding'])
            
            # 캐시 무효화
            self._known_faces_cache = None
            
            logger.info(f"얼굴 등록 완료: {person_name}")
            return True
            
        except Exception as e:
            logger.error(f"얼굴 등록 실패: {e}")
            return False

    def get_known_people(self) -> List[Dict[str, Any]]:
        """등록된 사람 목록 반환"""
        known_faces = self.load_known_faces()
        people = []
        
        for person_name, embeddings in known_faces.items():
            people.append({
                "name": person_name,
                "embedding_count": len(embeddings)
            })
        
        return people

face_detection_service = FaceDetectionService()

async def detect_and_recognize_faces(image_bytes: bytes) -> List[Dict[str, Any]]:
    """메인 얼굴 인식 함수"""
    return await face_detection_service.detect_and_recognize_faces(image_bytes)

async def startup_event():
    """서비스 시작 시 초기화"""
    try:
        if INSIGHTFACE_AVAILABLE:
            logger.info("얼굴 인식 서비스 사전 로드 중...")
            face_detection_service._get_face_app()
            face_detection_service.load_known_faces()
            logger.info("얼굴 인식 서비스 사전 로드 완료!")
        else:
            logger.warning("InsightFace가 설치되지 않아 얼굴 인식 기능이 비활성화됩니다.")
    except Exception as e:
        logger.error(f"사전 로드 오류: {e}")
