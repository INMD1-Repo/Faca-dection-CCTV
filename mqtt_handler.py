from fastapi_mqtt import FastMQTT, MQTTConfig

mqtt_config = MQTTConfig()
mqtt = FastMQTT(config=mqtt_config)

@mqtt.on_connect()
def connect(client, flags, rc, properties):
    mqtt.client.subscribe("/mqtt")
    print("MQTT Connected")

@mqtt.on_message()
async def on_message(client, topic, payload, qos, properties):
    print(f"Received: {topic}, {payload.decode()}")

# 움직임 감지 핸들러 함수 추가
async def motion_detected_handler(sensor_data=None):
    """
    움직임 감지 시 호출되는 핸들러 함수
    Args:
        sensor_data: 센서 데이터 (선택사항)
    """
    from services.mqtt_service import MQTTService
    
    try:
        print("Motion detected! Processing...")
        
        # 얼굴 인식과 함께 MQTT 메시지 전송
        result = await MQTTService.publish_motion_and_face_detection(sensor_data)
        
        if result["result"]:
            print("Motion and face detection alert sent successfully")
        else:
            print(f"Failed to send alert: {result['message']}")
            
    except Exception as e:
        print(f"Error in motion detection handler: {e}")

# 테스트용 움직임 감지 시뮬레이션 함수
async def simulate_motion_detection(location="living_room", person_detected=True):
    """테스트용 움직임 감지 시뮬레이션"""
    test_data = {
        "location": location,
        "person_detected": person_detected,
        "confidence": 0.95
    }
    await motion_detected_handler(test_data)
