import time

class FrameRateCounter:
    def __init__(self, interval=1):
        self.interval = interval
        self.last_time = time.time()
        self.frame_count = 0
        self.fps = 0
    
    def update(self):
        self.frame_count += 1
        if time.time() - self.last_time > self.interval:
            self.fps = self.frame_count / (time.time() - self.last_time)
            self.frame_count = 0
            self.last_time = time.time()
    
    def get_fps(self):
        return self.fps