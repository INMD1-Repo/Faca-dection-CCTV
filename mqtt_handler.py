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
