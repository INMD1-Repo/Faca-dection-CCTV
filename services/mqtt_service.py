from mqtt_handler import mqtt
from fastapi import HTTPException
import time
import json

#복호화키를 불려오기 위한 패키지
from Crypdeto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import base64
from pydantic import BaseModel

class MQTTService:
    @staticmethod
    async def publish_message(topic, message, password):
        if(password == "nullcodoe"):
            json_data = {
                "notice": "this is sample",
                "message": message,
                "time_Arlet":  time.strftime('%c', time.localtime(time.time()))
            }
            mqtt.publish(topic, json.dumps(json_data))
            return {"result": True, "message": "Published"}
        else:
          raise HTTPException(status_code=503, detail="Service Unavailable: Invalid password")            

    async def embed(type, RSA_PL):
       # 추후 환경변수로 넣을 예정입니다.
       EXPECTED_SECRET = "NSs2zpNqvb8pNuD"

       # 키를 불려오기
       with open("model/keys/rsa_private.pem", "rb") as f:
        private_key = RSA.import_key(f.read())

        # 복호화 검증
        try:
            # Base64 디코딩
            encrypted_bytes = base64.b64decode(RSA_PL)
            
            # 복호화
            cipher = PKCS1_OAEP.new(private_key)
            decrypted = cipher.decrypt(encrypted_bytes).decode()
            
            # 매칭 검증
            return decrypted == EXPECTED_SECRET
        except (ValueError, TypeError) as e:
            print(f"복호화 실패: {e}")
            return False