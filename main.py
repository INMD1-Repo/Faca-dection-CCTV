from fastapi import FastAPI
from mqtt_handler import mqtt
from routers.mqtt_router import router as mqtt_router

app = FastAPI()

# 라우터 등록
app.include_router(mqtt_router)
# MQTT 핸들러 초기화
mqtt.init_app(app)

# Uvicorn 실행 코드 (직접 실행 시)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)