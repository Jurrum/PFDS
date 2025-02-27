Product Futures DDAI Hardware Primer

Setup
For communicating with Connected IoT kit: Mu Editor (or VS Code)
To install libraries, download appropriate packages from https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases/download/20250206/adafruit-circuitpython-bundle-9.x-mpy-20250206.zip and drag and drop into lib/ folder on CIRCUITPY device

Instructions
On MCU #1, copy contents of send_data.py into code.py on CIRCUITPY device
On MCU #2, copy contents of receive_data.py into code.py on CIRCUITPY device
On both: modify Wifi credentials and MQTT topic (topic needs to match on both MCUs)
Note: a "subscriber" to an MQTT topic cannot read messages that existed before the subscription was created, so the code on MCU #2 needs to be running before MCU #1 publishes any messages
Open a serial monitor to communicate with MCU

Authors and acknowledgment
Starter code written by Katherine Song, with assistance from various genAI tools ;)