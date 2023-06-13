import network
import time
import sensor
import sub_board
import imgrequests
import protocol
import ujson

sub_board.init()
sub_board.speak("正在连接网络")
protocol.initialize_network()
sub_board.speak("网络连接成功")

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.HD)
sensor.skip_frames(time=2000)
clock = time.clock()

# State for directions
last_direction = None
direction_cooldown = time.ticks_ms()


def update_direction(direction):
    global last_direction
    global direction_cooldown
    current_time = time.ticks_ms()
    if current_time > direction_cooldown or (last_direction == 'stop' and direction != 'stop'):
        last_direction = direction
        direction_cooldown = current_time
        sub_board.stop_speech()
        if direction == 'front':
            sub_board.speak("前进")
            direction_cooldown = current_time + 3000
        elif direction == 'left':
            sub_board.speak("靠左")
            direction_cooldown = current_time + 1500
        elif direction == 'right':
            sub_board.speak("靠右")
            direction_cooldown = current_time + 1500
        elif direction == 'stop':
            sub_board.speak("小心通行")
            direction_cooldown = current_time + 1000
        elif direction == 'far_left':
            sub_board.speak("向左看")
            direction_cooldown = current_time + 3000
        elif direction == 'far_right':
            sub_board.speak("向右看")
            direction_cooldown = current_time + 3000


def update_text(text):
    # sub_board.stop_speech()
    sub_board.speak(text)  # TODO: Text priority


# Capture Mode
capture_lp_frames = 5
capture_hp_frames = 0
current_frame = 0


def configure_capture_mode(json):
    global capture_lp_frames
    global capture_hp_frames
    global current_frame
    capture_lp_frames = json['lp_frames']
    capture_hp_frames = json['hp_frames']
    current_frame = 0

# Capture lp_frames frames with low quality, then capture hp_frames frames with high quality
# Before capturing, call update_capture_mode to update the capture mode


def update_capture_mode():
    global current_frame
    if current_frame < capture_lp_frames:
        sensor.set_framesize(sensor.VGA)
    else:
        sensor.set_framesize(sensor.HD)
    current_frame = (
        current_frame + 1) % (capture_lp_frames + capture_hp_frames)


def handle_server_data(data_type, data_bytes):
    if data_type == protocol.TYPE_NONE:
        return
    elif data_type == protocol.TYPE_JSON:
        json_str = data_bytes.decode('utf-8')
        print(json_str)
        json = ujson.loads(json_str)
        if json['type'] == 'direction':
            update_direction(json['direction'])
        elif json['type'] == 'text':
            update_text(json['text'])
        elif json['type'] == 'capture_mode':
            configure_capture_mode(json)


def run():
    try:
        sub_board.speak("正在连接服务器")
        s = protocol.open_connection()
        sub_board.speak("服务器连接成功")
        while(True):
            update_capture_mode()
            img = sensor.snapshot()
            img = img.compress(quality=50)
            protocol.send_image(s, img)
            is_last = False
            while(not is_last):
                data_type, data_bytes, is_last = protocol.receive_data(s)
                if data_type == protocol.TYPE_TERMINATE:
                    sub_board.speak("服务器断开连接")
                    return
                else:
                    handle_server_data(data_type, data_bytes)

    except Exception as e:
        sub_board.speak("连接断开")
        print(e)
    finally:
        s.close()


while(True):
    run()
    time.sleep(2)
