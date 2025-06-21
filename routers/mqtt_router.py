from fastapi import APIRouter
from services.mqtt_service import MQTTService

router = APIRouter(prefix="/mqtt", tags=["mqtt"])

#해당 메서드는 Any 테스트 용도로만 쓰세요.
#URL: /mqtt/publish
@router.post("/publish")
async def publish_message(topic: str, message: str, password: str):
    return await MQTTService.publish_message(topic, message, password)

@router.post("/embed_test")
async def embed_test(type: int, RSA_PL: str):
    return await MQTTService.embed(type, RSA_PL)

# 움직임 감지 + 얼굴 인식 테스트용 엔드포인트 추가
@router.post("/test_motion_face")
async def test_motion_and_face_detection(
    location: str = "living_room", 
    person_detected: bool = True,
    confidence: float = 0.95
):
    """움직임 감지 + 얼굴 인식 테스트용 엔드포인트"""
    
    # mqtt_handler의 핸들러 함수 호출
    from mqtt_handler import motion_detected_handler
    
    test_data = {
        "location": location,
        "person_detected": person_detected,
        "confidence": confidence
    }
    
    await motion_detected_handler(test_data)
    return {"message": "Motion and face detection test triggered", "data": test_data}

@router.post("/direct_motion_face_publish")
async def direct_motion_face_publish(
    location: str = "living_room",
    person_detected: bool = True,
    confidence: float = 0.95
):
    """직접 움직임 감지 + 얼굴 인식 MQTT 메시지 발행"""
    
    sensor_data = {
        "location": location,
        "person_detected": person_detected,
        "confidence": confidence
    }
    
    result = await MQTTService.publish_motion_and_face_detection(sensor_data)
    return result
