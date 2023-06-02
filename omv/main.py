import network, time, sensor
import sub_board
import imgrequests
import protocol

sub_board.init()
sub_board.speak("正在连接网络")
protocol.initialize_network()
sub_board.speak("网络连接成功")

sensor.reset()                     
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.HD)    
sensor.skip_frames(time = 2000)    
clock = time.clock()               


def handle_server_data(data_type, data_bytes):
    if data_type == protocol.TYPE_NONE:
        return
    elif data_type == protocol.TYPE_JSON:
        json_str = data_bytes.decode('utf-8')
        print(json_str)
        # TODO: handle json

def run():
    try:
        sub_board.speak("正在连接服务器")
        s = protocol.open_connection()
        sub_board.speak("服务器连接成功")
        while(True):
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
    time.sleep(1)
    