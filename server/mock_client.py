import socket
import time
import os

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5)
s.connect(('localhost', 5000))
print('Connected')

image_folder = 'D:/Downloads/dcim/frametest'
image_files = [os.path.join(image_folder, f) for f in os.listdir(image_folder)]

try:
    frame_count = 0
    while True:
        image_file = image_files[frame_count % len(image_files)]
        # read image bytes
        with open(image_file, 'rb') as f:
            image_bytes = f.read()
        
        # send image
        s.sendall(b'\x19\x26\x08\x17\x02\x01')
        s.sendall(len(image_bytes).to_bytes(4, 'little'))
        s.sendall(image_bytes)
        print(f'Sent image {frame_count}')

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
        print(f'Received result {frame_count}')
        
        frame_count += 1
        time.sleep(0.1)
finally:
    s.sendall(b'\x19\x26\x08\x17\x00\x01')
    s.close()