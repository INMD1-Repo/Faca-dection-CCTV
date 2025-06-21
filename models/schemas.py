from pydantic import BaseModel, Field
from typing import List, Optional, Tuple, Any, Dict
from datetime import datetime

class LearningRequest(BaseModel):
    person_name: str = Field(..., description="등록할 사람의 이름")
    # UploadFile은 라우터에서 직접 처리

class LearningResponse(BaseModel):
    person_name: str
    embeddings_count: int
    message: str

class DetectionResultItem(BaseModel):
    name: str
    confidence: float
    box: List[int] # [x1, y1, x2, y2]
    is_known: bool

class DetectionResponse(BaseModel):
    detected_faces: List[DetectionResultItem]
    total_detected: int
    known_detected: int
    unknown_detected: int

# --- Webhook 관련 스키마 ---
class WebhookEventPayloadData(BaseModel): # Webhook 페이로드의 data 필드를 위한 기본 클래스
    pass

class UnknownFaceDetectedPayloadData(WebhookEventPayloadData):
    detected_at: datetime
    camera_id: Optional[str] = None
    # 필요한 경우 Base64 인코딩된 이미지 데이터 추가 가능
    # frame_image_base64: Optional[str] = None

class WebhookEventPayload(BaseModel):
    event_type: str
    timestamp: datetime
    data: Dict[str, Any] # 실제로는 위 PayloadData 클래스 중 하나가 될 것

class WebhookRegistrationRequest(BaseModel):
    url: str # pydantic HttpUrl 대신 str 사용 (Webhook URL 유효성 검사는 서비스 레벨에서)
    event_types: List[str]

class WebhookRegistrationResponse(BaseModel):
    id: str
    url: str
    event_types: List[str]

class FaceRecognitionResult(BaseModel):
    name: str
    confidence: float
    box: List[int]
    is_known: bool
    detection_score: float

class PersonInfo(BaseModel):
    name: str
    embedding_count: int

class TuyaONVIFConfig(BaseModel):
    host: str = "192.168.0.19"
    username: str = "admin"
    onvif_password: str = ""
    port: int = 835

class ONVIFStatus(BaseModel):
    is_monitoring: bool
    connection_status: str
    latest_detections: List[Dict[str, Any]]
    camera_info: Optional[Dict[str, Any]] = None

class DetectionEvent(BaseModel):
    timestamp: str
    faces: List[FaceRecognitionResult]
    image_size: int
    motion_detected: bool = True
    