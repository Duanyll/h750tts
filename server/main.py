from __future__ import annotations
import multiprocessing as mp
import asyncio
import time

def run_inference_server(infer_queue: mp.Queue, info_queue: mp.Queue, monitor_queue: mp.Queue):
    from backend.inference_server import InferenceServer
    inference_server = InferenceServer(infer_queue, info_queue, monitor_queue)
    asyncio.run(inference_server.run())

def run_monitor_server(monitor_queue: mp.Queue):
    from backend.monitor_server import MonitorServer
    monitor_server = MonitorServer(monitor_queue)
    asyncio.run(monitor_server.run())

def run_stream_server(infer_queue: mp.Queue, info_queue: mp.Queue, monitor_queue: mp.Queue):
    from backend.stream_server import StreamServer
    stream_server = StreamServer(infer_queue, info_queue, monitor_queue)
    asyncio.run(stream_server.run())

def main():
    # create queues
    infer_queue = mp.Queue()
    info_queue = mp.Queue()
    monitor_queue = mp.Queue()

    # create processes
    inference_server_process = mp.Process(target=run_inference_server, args=(infer_queue, info_queue, monitor_queue))
    monitor_server_process = mp.Process(target=run_monitor_server, args=(monitor_queue,))
    stream_server_process = mp.Process(target=run_stream_server, args=(infer_queue, info_queue, monitor_queue))

    # start processes
    inference_server_process.start()
    stream_server_process.start()
    monitor_server_process.start()

    # handle keyboard interrupt
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        # kill processes
        inference_server_process.kill()
        monitor_server_process.kill()
        stream_server_process.kill()

        inference_server_process.join()
        monitor_server_process.join()
        stream_server_process.join()

if __name__ == '__main__':
    main()
