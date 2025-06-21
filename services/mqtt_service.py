from mqtt_handler import mqtt
from fastapi import HTTPException
import time
import json

#복호화키를 불려오기 위한 패키지
from Crypto.PublicKey import RSA  # 오타 수정: Crypdeto -> Crypto
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
                "time_Alert":  time.strftime('%c', time.localtime(time.time()))  # 오타 수정: time_Arlet -> time_Alert
            }
            mqtt.publish(topic, json.dumps(json_data))
            return {"result": True, "message": "Published"}
        else:
          raise HTTPException(status_code=503, detail="Service Unavailable: Invalid password")            

    # 움직임 감지 + 얼굴 인식 MQTT 발행 함수
    @staticmethod
    async def publish_motion_and_face_detection(sensor_data=None):
        """
        움직임 감지와 얼굴 인식 결과를 MQTT로 발행하는 함수
        Args:
            sensor_data: 센서에서 받은 데이터
        """
        try:
            topic = "sensors/motion_face_detection"
            
            # 기본값 설정
            location = sensor_data.get("location", "unknown") if sensor_data else "unknown"
            person_detected = sensor_data.get("person_detected", False) if sensor_data else False
            confidence = sensor_data.get("confidence", 0.0) if sensor_data else 0.0
            
            json_data = {
                "event_type": "motion_and_face_detection",
                "location": location,
                "person_detected": person_detected,
                "confidence": confidence,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                "alert_level": "high" if person_detected else "medium",
                "message": f"Motion detected at {location}" + (" with person identified" if person_detected else " without person identification")
            }
            
            mqtt.publish(topic, json.dumps(json_data))
            print(f"Motion and face detection alert published to topic: {topic}")
            print(f"Data: {json.dumps(json_data, indent=2)}")
            
            return {"result": True, "message": "Motion and face detection alert published successfully"}
            
        except Exception as e:
            print(f"Failed to publish motion and face detection alert: {e}")
            return {"result": False, "message": f"Failed to publish: {str(e)}"}

    @staticmethod  # 데코레이터 추가
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
