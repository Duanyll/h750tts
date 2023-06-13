import socket
import time
import os
import cv2

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5)
s.connect(('localhost', 5000))
print('Connected')

try:
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        # compress frame to JPEG
        image_bytes = bytes(cv2.imencode('.jpg', frame)[1])
        
        # send image
        s.sendall(b'\x19\x26\x08\x17\x02\x01')
        s.sendall(len(image_bytes).to_bytes(4, 'little'))
        s.sendall(image_bytes)

        # receive result
        is_last = False
        while not is_last:
            header = s.recv(6)
            if header[0:4] != b'\x19\x26\x08\x17':
                raise Exception('Invalid header')
            data_type = header[4]
            is_last = header[5] == 1
            if data_type == 0x00 or data_type == 0x01:
                continue
            length = int.from_bytes(s.recv(4), 'little')
            body = s.recv(length)
            if data_type == 0x04:
                # JSON
                print(body.decode('utf-8'))
        
        # time.sleep(0.05)
finally:
    s.sendall(b'\x19\x26\x08\x17\x00\x01')
    s.close()