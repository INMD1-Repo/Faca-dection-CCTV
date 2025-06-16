from fastapi import APIRouter
from services.mqtt_service import MQTTService

router = APIRouter(prefix="/mqtt", tags=["mqtt"])

#해당 메서드는 Any 테스트 용도로만 쓰세요.
#URL: /mqtt/publish
@router.post("/publish")
async def publish_message(topic: str, message: str, password: str):
    return await MQTTService.publish_message(topic, message, password)


@router.post("/embed_test")
async def publish_message(type: int, RSA_PL: str):
      return await MQTTService.embed(type, RSA_PL)
