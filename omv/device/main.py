import network, time, sensor
import sub_board
import imgrequests
from led import blue_led

def initialize_network():
    blue_led.on()
    network_if = network.WLAN(network.STA_IF)
    network_if.active(True)
    network_if.connect('DUANYLL-LEGION', '12345678')
    while not network_if.isconnected():
        print("Trying to connect. Note this may take a while...")
        time.sleep_ms(1000)
    print(network_if.ifconfig())
    blue_led.off()


sub_board.init()
sub_board.speak("正在连接网络")
initialize_network()
sub_board.speak("网络连接成功")

sensor.reset()                      # Reset and initialize the sensor.
sensor.set_pixformat(sensor.RGB565) # Set pixel format to RGB565 (or GRAYSCALE)
sensor.set_framesize(sensor.HD)     # Set frame size to QVGA (320x240)
sensor.skip_frames(time = 2000)     # Wait for settings take effect.
clock = time.clock()                # Create a clock object to track the FPS.

while(True):
    clock.tick()                    # Update the FPS clock.
    img = sensor.snapshot()
    img = img.lens_corr(1.8)
    img = img.compress(quality=70)
    # res = imgrequests.request('POST', 'http://192.168.137.1:5000/ocr', image_bytes=img)
