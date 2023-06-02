import json
from pyb import UART
from LED import red_led, green_led, blue_led, ir_led

uart = None

def init():
    global uart, pinyin_data
    uart = UART(3, 115200)
    uart.init(115200, bits=8, parity=None, stop=1, timeout=1000)

def speak(str):
    green_led.on()
    global uart
    print(f'> Speak: {str}')
    data = json.dumps({"command": "speak", "text": str})
    uart.write(data)
    uart.write("\n")
    green_led.off()
    try:
        line = uart.readline().decode().strip()
        res = json.loads(line)
        if res["code"] != 0:
            print("Error: Speak failed. Code %d" % res["code"])
            return False
        return True
    except:
        print("Error: Speak failed.")
        return False
