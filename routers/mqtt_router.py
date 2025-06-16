from fastapi import APIRouter
from services.mqtt_service import MQTTService

router = APIRouter(prefix="/mqtt", tags=["mqtt"])

@router.post("/publish")
async def publish_message(topic: str, message: str):
    return await MQTTService.publish_message(topic, message)
