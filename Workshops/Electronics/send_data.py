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

# SPI setup (DON'T CHANGE)
esp32_cs = digitalio.DigitalInOut(board.D9)
esp32_ready = digitalio.DigitalInOut(board.D11)
esp32_reset = digitalio.DigitalInOut(board.D12)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

# Sensors: uncomment/edit the ones you're using
#photo_sensor = analogio.AnalogIn(board.A0)
#temp_sensor = board.A2
#pot_sensor = analogio.AnalogIn(board.A4)
#dist_sensor = adafruit_vl53l0x.VL53L0X(i2c_port)

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
MQTT_TOPIC = 'PF/social_media' # enter your topic here (should match MCU #2 "receive_data.py")


# labels for types of input user can select (example: text or sensor))
class_names = ['Text input','Sensor input'] 

# --- Functions

# function to get sensor data (uncomment/comment particular sensors as needed)
def get_sensor_data():
    """Get real-time sensor data."""
    #temp = thermistor.temperature
    #light = photo_sensor.value
    dist = dist_sensor.range
    #return (temp, light, dist)
    return (dist)

def connected(client, userdata, flags, rc):
    print("Connected to MQTT Broker!")

def disconnected(client, userdata, rc):
    print("Disconnected from MQTT Broker!")

# MQTT client setup (DON'T CHANGE)
pool = adafruit_esp32spi_socketpool.SocketPool(esp)

mqtt_client = MQTT.MQTT(
    broker=MQTT_BROKER,
    username=MQTT_USERNAME,
    password=MQTT_PASSWORD,
    socket_pool=pool
)
# MQTT callback functions (DON'T CHANGE)
mqtt_client.on_connect = connected
mqtt_client.on_disconnect = disconnected

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

# connect to MQTT (DON'T CHANGE)
print("Connecting to MQTT...")
mqtt_client.connect()

# start data collection
print("Starting gesture data collection.")
print("Press Ctrl+C to exit.")

try:
    while True:
        # user can select to input text or read sensor(s)
        print("\nTypes of input:")
        for i, c in enumerate(class_names):
            print(f"{i}: {c}")

        try:
            class_index = int(input("Enter the number corresponding to the type of input to record: "))
            if class_index < 0 or class_index >= len(class_names):
                print("Invalid selection. Try again.")
                continue
        except ValueError:
            print("Invalid input. Please enter a number.")
            continue

        class_name = class_names[class_index]
        
        print(f"Collecting data for: {class_name}")
        
        # for text input, publish user input on serial straight to MQTT
        if class_name is 'Text input':
            message = input("Enter text: ")
            mqtt_client.publish(MQTT_TOPIC, message)
            print(message + " published to " + MQTT_TOPIC)
        
        # for sensor input, collect data for 5 seconds and then publish to MQTT
        else:
            mqtt_client.publish(MQTT_TOPIC, class_name)
            
            print("Do the thing now. Recording for 5 seconds.")
            start_time = time.monotonic()
            #collected_data = []

            while True:
                # Collect data for exactly 5 seconds
                elapsed_time = time.monotonic() - start_time
                # after 5 sec of data collection, publish "END" to MQTT broker (optional)
                if elapsed_time >= 5:
                    print(f"Completed 5 seconds of data collection for '{class_name}'.")
                    mqtt_client.publish(MQTT_TOPIC, "END") 
                    break

                timestamp = elapsed_time
                sensor_data = get_sensor_data()

                # Publish data at the current timestep to mqtt
                #message = f"{timestamp:.2f},{sensor_data[0]:.2f},{sensor_data[1]:.2f}" # example for multiple sensors' data
                message = f"{timestamp:.2f},{sensor_data}"
                mqtt_client.publish(MQTT_TOPIC, message)
                print(message)
                
                time.sleep(0.1)  # Wait for 0.1 seconds before repeating


except KeyboardInterrupt:
    print("\nData collection stopped.")