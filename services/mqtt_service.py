from mqtt_handler import mqtt
from fastapi import HTTPException
import time
import json

class MQTTService:
    @staticmethod
    async def publish_message(topic, message, password):
        if(password == "nullcodoe"):
            json_data = {
                "message": message,
                "time_Arlet":  time.strftime('%c', time.localtime(time.time()))
            }
            mqtt.publish(topic, json.dumps(json_data))
            return {"result": True, "message": "Published"}
        else:
          raise HTTPException(status_code=503, detail="Service Unavailable: Invalid password")            

    async def embed(type, RSA_PL):
        