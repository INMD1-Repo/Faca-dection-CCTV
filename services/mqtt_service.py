from mqtt_handler import mqtt

class MQTTService:
    @staticmethod
    async def publish_message(topic, message):
        mqtt.publish(topic, message)
        return {"result": True, "message": "Published"}
