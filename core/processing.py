import time
import numpy as np
from collections import deque
from numba import jit, prange
from PyQt6.QtCore import Qt, QPointF, QTimer, QRectF, QThread, pyqtSignal, QMargins

# 일정 길이의 이동 평균 계산 클래스 (e.g. 속도 평균화)
class MovingAverage:
    def __init__(self, window_size=5):
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

# 속도 계산을 위한 Numba 최적화 함수
@jit(nopython=True)
def calculate_speed(dx, dy, dt):
    return np.sqrt(dx * dx + dy * dy) / dt if dt > 0 else 0.0

# 시계열 smoothing 함수 (단순 평균 필터)
@jit(nopython=True, parallel=True)
def smooth_data(data, window_size):
    result = np.zeros_like(data)
    for i in prange(len(data)):
        start = max(0, i - window_size // 2)
        end = min(len(data), i + window_size // 2 + 1)
        result[i] = np.mean(data[start:end])
    return result

# 실시간 데이터 처리용 QThread
class DataProcessor(QThread):
    data_processed = pyqtSignal(float, float)  # (현재 속도, 평균 속도) 시그널

    def __init__(self, window_size=30):
        super().__init__()
        self.speed_avg = MovingAverage(window_size)
        self.queue = deque(maxlen=100)
        self.running = True
        self.is_pressed = False  # 터치 여부
        self.last_speed = 0

    def set_pressed(self, is_pressed):
        self.is_pressed = is_pressed

    def stop(self):
        self.running = False

    def add_data(self, dx, dy, dt):
        self.queue.append((dx, dy, dt))

    def run(self):
        while self.running:
            if self.queue:
                dx, dy, dt = self.queue.popleft()
                current_speed = calculate_speed(dx, dy, dt)

                # 터치 중이 아닐 경우 속도는 0으로 처리
                if not self.is_pressed:
                    current_speed = 0

                self.speed_avg.add_value(current_speed)
                avg_speed = self.speed_avg.get_average()

                # 실시간 속도와 평균값 전송
                self.data_processed.emit(current_speed, avg_speed)

            time.sleep(0.001)  # 1kHz 처리 루프 (1ms 간격)

# 실시간 차트 업데이트 전용 QThread
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
        # 최신 데이터를 큐처럼 밀어넣음
        self.current_speeds = np.roll(self.current_speeds, -1)
        self.avg_speeds = np.roll(self.avg_speeds, -1)
        self.current_speeds[-1] = current_speed
        self.avg_speeds[-1] = avg_speed

        # 그래프 시리즈 갱신 (현재 속도, 평균 속도)
        current_series = self.chart_view.chart().series()[0]
        avg_series = self.chart_view.chart().series()[1]

        current_series.clear()
        avg_series.clear()

        for i in range(self.data_points):
            current_series.append(i, self.current_speeds[i])
            avg_series.append(i, self.avg_speeds[i])
