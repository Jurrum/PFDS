import analogio
import board
import busio
import digitalio
import time
import json
import adafruit_vl53l0x
import adafruit_thermistor
import adafruit_esp32spi.adafruit_esp32spi as esp32spi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_esp32spi import adafruit_esp32spi_socketpool

# --- Setup
# I2C Port (DON'T CHANGE)
i2c_port = busio.I2C(board.SCL, board.SDA)

# Sensors: uncomment/edit the ones you're usingg
#photo_sensor = analogio.AnalogIn(board.A0)
#temp_sensor = board.A2
#pot_sensor = analogio.AnalogIn(board.A4)
# Test
dist_sensor = adafruit_vl53l0x.VL53L0X(i2c_port)

# Thermistor setup (uncomment if using; also uncomment "temp_sensor" above)
"""
resistor = 10000
resistance = 10000
nominal_temp = 25
b_coefficient = 3950
thermistor = adafruit_thermistor.Thermistor(
    temp_sensor, resistor, resistance, nominal_temp, b_coefficient
)
"""

# WiFi Credentials - fill in your own here
WIFI_SSID = 'iPhoneKat'
WIFI_PASSWORD = 'sparkypi'

# MQTT Credentials
MQTT_BROKER = 'ide-education.cloud.shiftr.io' # DON'T CHANGE
MQTT_USERNAME = 'ide-education' # DON'T CHANGE
MQTT_PASSWORD = 'iOF42Md4VQ3CXJxS' # DON'T CHANGE
MQTT_TOPIC = 'perlin' # enter your topic here (should match the topic you set on MCU #1)

# SPI setup (DON'T CHANGE)
esp32_cs = digitalio.DigitalInOut(board.D9)
esp32_ready = digitalio.DigitalInOut(board.D11)
esp32_reset = digitalio.DigitalInOut(board.D12)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

# --- Functions

# function to get sensor data (uncomment/comment particular sensors as needed)
def get_sensor_data():
    """Get real-time sensor data."""
    #temp = thermistor.temperature
    #light = photo_sensor.value
    dist = dist_sensor.range
    #return (temp, light, dist)
    return (dist)

# MQTT callback functions
def connected(client, userdata, flags, rc):
    print("Connected to MQTT Broker!")

def disconnected(client, userdata, rc):
    print("Disconnected from MQTT Broker!")

def subscribe(mqtt_client, userdata, topic, granted_qos):
    print(f"Subscribed to {topic} with QOS level {granted_qos}")

def message_received(client, topic, message):
    print(f"New message on topic {topic}: {message}")
    # do something with the received message! :
    #
    #
    #
    #
    #

# MQTT Client setup (DON'T CHANGE)
pool = adafruit_esp32spi_socketpool.SocketPool(esp)

mqtt_client = MQTT.MQTT(
    broker=MQTT_BROKER,
    username=MQTT_USERNAME,
    password=MQTT_PASSWORD,
    socket_pool=pool
)
mqtt_client.on_connect = connected
mqtt_client.on_disconnect = disconnected
mqtt_client.on_subscribe = subscribe
mqtt_client.on_message = message_received

# --- Main program:

# connect to WiFi (DON'T CHANGE)
print("Connecting to WiFi...")
wifi_connecting = True
while wifi_connecting:
    try:
        esp.connect_AP(WIFI_SSID, WIFI_PASSWORD)
        wifi_connecting = False
    except ConnectionError:
        print(f"Couldn't connect to {WIFI_SSID}, trying again.")
print("Connected!")

# connect to MQTT client (DON'T CHANGE)
print("Connecting to MQTT...")
mqtt_client.connect()

# subscribe to MQTT topic
mqtt_client.subscribe(MQTT_TOPIC)

# keep looping
while True: 
    try:
        mqtt_client.loop() # check for new messages from MQTT broker
        
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        mqtt_client.reconnect()
        continue