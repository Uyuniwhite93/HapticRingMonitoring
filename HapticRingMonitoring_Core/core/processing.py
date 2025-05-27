import time
import numpy as np
from collections import deque
from numba import jit, prange
from PyQt6.QtCore import Qt, QPointF, QTimer, QRectF, QThread, pyqtSignal, QMargins

class MovingAverage:
    def __init__(self, window_size=15):
        self.window_size = window_size
        self.values = deque(maxlen=window_size)
        self.sum = 0.0

    def add_value(self, value):
        if len(self.values) == self.window_size:
            self.sum -= self.values[0]
        self.values.append(value)
        self.sum += value

    def get_average(self):
        if not self.values:
            return 0.0
        return self.sum / len(self.values)

    def reset(self):
        self.values.clear()
        self.sum = 0.0

@jit(nopython=True)
def calculate_speed(dx, dy, dt):
    return np.sqrt(dx * dx + dy * dy) / dt if dt > 0 else 0.0

@jit(nopython=True, parallel=True)
def smooth_data(data, window_size):
    result = np.zeros_like(data)
    for i in prange(len(data)):
        start = max(0, i - window_size // 2)
        end = min(len(data), i + window_size // 2 + 1)
        result[i] = np.mean(data[start:end])
    return result

class DataProcessor(QThread):
    data_processed = pyqtSignal(float, float)  # (current_speed, average_speed) signal

    def __init__(self, window_size=30):
        super().__init__()
        self.speed_avg = MovingAverage(window_size)
        self.queue = deque(maxlen=100)
        self.running = True
        self.is_pressed = False
        self.last_known_speed = 0.0
        self.last_known_avg_speed = 0.0
        self.last_emit_time_when_not_pressed = 0

    def set_pressed(self, is_pressed):
        self.is_pressed = is_pressed
        if not is_pressed:
            self.speed_avg.reset()
            self.queue.clear()
            self.last_known_speed = 0.0
            self.last_known_avg_speed = 0.0 # Ensure avg_speed is also reset
            self.data_processed.emit(0.0, 0.0)
            self.last_emit_time_when_not_pressed = time.time()

    def stop(self):
        self.running = False

    def add_data(self, dx, dy, dt):
        self.queue.append((dx, dy, dt))

    def run(self):
        while self.running:
            if self.is_pressed and self.queue:
                dx, dy, dt = self.queue.popleft()
                current_speed = calculate_speed(dx, dy, dt)
                self.speed_avg.add_value(current_speed)
                avg_speed = self.speed_avg.get_average()

                self.last_known_speed = current_speed
                self.last_known_avg_speed = avg_speed
                self.data_processed.emit(current_speed, avg_speed)

            elif not self.is_pressed:
                current_time = time.time()
                if current_time - self.last_emit_time_when_not_pressed > 0.05: # Approx 20Hz
                    # When not pressed, always emit (0.0, 0.0)
                    # last_known_speed and last_known_avg_speed should be 0 here due to set_pressed(False)
                    self.data_processed.emit(0.0, 0.0)
                    self.last_emit_time_when_not_pressed = current_time
            
            # Sleep logic to prevent busy waiting
            if not self.queue:
                if not self.is_pressed:
                    time.sleep(0.05)  # Longer sleep if not pressed and queue is empty
                else:
                    time.sleep(0.005) # Shorter sleep if pressed but queue is empty
            else:
                time.sleep(0.001)   # Very short sleep if queue has data (processing quickly)

class ChartUpdater(QThread):
    def __init__(self, chart_view, data_points=100):
        super().__init__()
        self.chart_view = chart_view
        self.data_points = data_points
        self.current_speeds = np.zeros(data_points)
        self.avg_speeds = np.zeros(data_points)
        self.running = True

    def stop(self):
        self.running = False

    def update_data(self, current_speed, avg_speed):
        self.current_speeds = np.roll(self.current_speeds, -1)
        self.avg_speeds = np.roll(self.avg_speeds, -1)
        self.current_speeds[-1] = current_speed
        self.avg_speeds[-1] = avg_speed

        current_series = self.chart_view.chart().series()[0]
        avg_series = self.chart_view.chart().series()[1]

        current_series.clear()
        avg_series.clear()

        for i in range(self.data_points):
            current_series.append(i, self.current_speeds[i])
            avg_series.append(i, self.avg_speeds[i]) 