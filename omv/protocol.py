import network, time
import usocket
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

# data format: [0x19260817][type (1)][is last (1)][length (4)][data]
# type 0x00: Terminating connection (length is not present)
# type 0x01: None (length is not present)
# type 0x02: JPEG image
# type 0x03: WAV audio
# type 0x04: JSON

HEADER = b'\x19\x26\x08\x17'
TYPE_TERMINATE = 0x00
TYPE_NONE = 0x01
TYPE_IMAGE = 0x02
TYPE_AUDIO = 0x03
TYPE_JSON = 0x04

def open_connection():
    blue_led.on()
    s = usocket.socket()
    sockaddr = usocket.getaddrinfo('192.168.137.1', 5000)[0][-1]
    s.settimeout(5.0)
    s.connect(sockaddr)
    blue_led.off()
    return s

def send_image(s, image_bytes):
    blue_led.on()
    s.sendall(HEADER + TYPE_IMAGE.to_bytes(1, 'little') + (0x01).to_bytes(1, 'little'))
    s.sendall(len(image_bytes).to_bytes(4, 'little'))
    s.sendall(image_bytes)
    blue_led.off()
    
def receive_data(s):
    header = s.recv(6)
    if header[0:4] != HEADER:
        raise Exception('Invalid header')
    data_type = header[4]
    is_last = header[5] == 0x01
    if data_type == TYPE_TERMINATE or data_type == TYPE_NONE:
        return data_type, None, is_last
    length = int.from_bytes(s.recv(4), 'little')
    data_bytes = s.recv(length)
    return data_type, data_bytes, is_last