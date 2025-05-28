from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                           QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton)
from PyQt6.QtCore import Qt, QPointF, QTimer, QRectF, QThread, pyqtSignal, QMargins
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QPainterPath, QPixmap, QRadialGradient, QFont, QFontDatabase, QCursor
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis

import numpy as np
import time
import psutil
import gc
import multiprocessing as mp
from numba import jit, prange
from collections import deque
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from ui.touch_pad import TouchPadWidget
from ui.charts import ChartView
from core.audio_player import HapticAudioPlayer
from core.processing import DataProcessor, ChartUpdater

class HapticMonitor(QMainWindow):
    DATA_POINTS = 50  
    PERFORMANCE_LOG_INTERVAL = 1.0
    
    def __init__(self):
        super().__init__()
        
        self.setupFonts()
        
        # 데이터 포인터 수 설정
        self.data_points = self.DATA_POINTS
        
        # 메모리 사전 할당 (데이터 타입 명시하여 메모리 최적화)
        self.speed_data = np.zeros(self.data_points, dtype=np.float32)
        self.avg_speed_data = np.zeros(self.data_points, dtype=np.float32)
        self.sa_data = np.zeros(self.data_points, dtype=np.float32)
        self.ra_data = np.zeros(self.data_points, dtype=np.float32)
        
        # 성능 모니터링 버퍼 (크기 제한)
        self.frame_times = deque(maxlen=60)
        
        # 이동 평균 버퍼 (크기 조정으로 반응성 향상)
        self.speed_window = deque(maxlen=5)  # 5로 줄여 더 빠른 반응
        
        # 차트 업데이트 최적화
        self.chart_update_counter = 0
        self.chart_update_interval = 3
        
        # 프로세스 우선순위 설정
        try:
            this_process = psutil.Process()
            this_process.nice(psutil.HIGH_PRIORITY_CLASS)
        except:
            pass
            
        # 메모리 관리 변수
        self.last_gc_time = time.time()
        self.last_perf_log_time = time.time()
        self.gc_interval = 60
        
        # 스레드풀 최적화
        cpu_count = mp.cpu_count()
        self.thread_pool = ThreadPoolExecutor(max_workers=cpu_count)
        self.process_pool = ProcessPoolExecutor(max_workers=cpu_count // 2)
        
        # 미리 계산된 값 캐싱
        self._cached_points = np.arange(self.data_points, dtype=np.float32)  # 포인트 인덱스 캐싱
        
        # 오디오 플레이어 초기화
        self.audio_player = HapticAudioPlayer()
        
        self.initUI()
        self.initVariables()
        self.initChart()
        self.initThreads()
        
        # 메모리 모니터링
        self.memory_check_timer = QTimer()
        self.memory_check_timer.timeout.connect(self.checkMemoryUsage)
        self.memory_check_timer.start(30000)  # 30초마다 체크
        
        # 업데이트 타이머 - 60Hz로 고정
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.updateDisplay)
        self.update_timer.start(16)  # 60Hz (약 16.67ms)
        
        # 차트 업데이트 타이머 - 20Hz로 고정
        self.chart_timer = QTimer()
        self.chart_timer.timeout.connect(self.updateCharts)
        self.chart_timer.start(50)  # 20Hz (50ms)
        
        # 마지막 업데이트 시간 초기화
        self._last_update_time = time.time()
        self.last_process_time = time.perf_counter()
        
        # 실시간 처리 간격 (1kHz)
        self.process_interval = 0.001
        
    def setupFonts(self):
        available_fonts = QFontDatabase.families()
        
        preferred_fonts = [
            "SF Pro", "San Francisco", "SF Pro Display", 
            "Apple SD Gothic Neo", "Helvetica Neue", "Helvetica",
            "Segoe UI", "Roboto", "Arial", "Malgun Gothic"
        ]
        
        self.app_font = None
        for font_name in preferred_fonts:
            for available in available_fonts:
                if font_name.lower() in available.lower():
                    self.app_font = QFont(available, 10)
                    QApplication.setFont(self.app_font)
                    return
                    
        self.app_font = QFont("Sans Serif", 10)
        self.app_font.setStyleHint(QFont.StyleHint.SansSerif)
        QApplication.setFont(self.app_font)
        
    def initUI(self):
        self.setWindowTitle('Haptic Monitor')
        self.setGeometry(100, 100, 1200, 600)
        
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #222428;
            }
            QLabel {
                color: #E8E8E8;
            }
        """)
        
        palette = QApplication.instance().palette()
        palette.setColor(palette.ColorRole.Window, QColor(34, 36, 40))      
        palette.setColor(palette.ColorRole.Base, QColor(34, 36, 40))        
        palette.setColor(palette.ColorRole.AlternateBase, QColor(40, 42, 46))
        palette.setColor(palette.ColorRole.Text, QColor(232, 232, 232))      
        palette.setColor(palette.ColorRole.ButtonText, QColor(232, 232, 232))
        palette.setColor(palette.ColorRole.WindowText, QColor(232, 232, 232))
        QApplication.instance().setPalette(palette)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        info_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(50, 52, 56, 0.9);
                border-radius: 10px;
                border: 1px solid #3C3E44;
            }
        """)
        
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(8)
        info_layout.setContentsMargins(15, 15, 15, 15)
        
        self.click_status_label = QLabel('Touch Status: Not Touching')
        self.press_duration_label = QLabel('Touch Duration: 0.000 sec')
        self.stationary_duration_label = QLabel('Stationary Duration: 0.000 sec')
        self.avg_speed_label = QLabel('Average Speed: 0.0 px/s')
        self.sa_value_label = QLabel('SA Receptor Value: 0.000')
        self.ra_value_label = QLabel('RA Receptor Value: 0.000')
        
        label_style = """
            QLabel {
                color: #E8E8E8;
                background-color: rgba(55, 57, 62, 0.9);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 10.5pt;
                font-weight: 500;
                border: 1px solid #45474D;
                qproperty-alignment: AlignCenter;
            }
        """
        
        for label in [self.click_status_label, self.press_duration_label,
                     self.stationary_duration_label, self.avg_speed_label,
                     self.sa_value_label, self.ra_value_label]:
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            label.setMinimumHeight(36)
            label.setStyleSheet(label_style)
            info_layout.addWidget(label)
        
        left_layout.addWidget(info_frame, stretch=1)
        
        graphs_widget = QWidget()
        graphs_layout = QVBoxLayout(graphs_widget)
        graphs_layout.setSpacing(15)
        
        speed_chart_frame = QFrame()
        speed_chart_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        speed_chart_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(50, 52, 56, 0.9);
                border-radius: 10px;
                border: 1px solid #3C3E44;
            }
        """)
        
        speed_chart_layout = QVBoxLayout(speed_chart_frame)
        speed_chart_layout.setContentsMargins(10, 10, 10, 10)
        
        self.speed_chart_view = ChartView()
        self.speed_chart_view.setMinimumSize(400, 150)
        speed_chart_layout.addWidget(self.speed_chart_view)
        
        graphs_layout.addWidget(speed_chart_frame)
        
        tactile_chart_frame = QFrame()
        tactile_chart_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        tactile_chart_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(50, 52, 56, 0.9);
                border-radius: 10px;
                border: 1px solid #3C3E44;
            }
        """)
        
        tactile_chart_layout = QVBoxLayout(tactile_chart_frame)
        tactile_chart_layout.setContentsMargins(10, 10, 10, 10)
        
        self.tactile_chart_view = ChartView()
        self.tactile_chart_view.setMinimumSize(400, 150)
        tactile_chart_layout.addWidget(self.tactile_chart_view)
        
        graphs_layout.addWidget(tactile_chart_frame)
        
        left_layout.addWidget(graphs_widget, stretch=2)
        
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(20)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        material_title = QLabel("Material Selection")
        material_title.setStyleSheet("""
            font-size: 16pt; 
            font-weight: 600; 
            color: #E8E8E8; 
            margin-bottom: 10px;
        """)
        material_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(material_title)
        
        material_buttons_layout = QHBoxLayout()
        material_buttons_layout.setSpacing(8)
        material_buttons_layout.setContentsMargins(0, 0, 0, 15)
        
        materials = {
            "metal": ("Metal", "#738ADB"),
            "glass": ("Glass", "#56CCF2"),
            "wood": ("Wood", "#D4A76A"),
            "fabric": ("Fabric", "#4ECDC4"),
            "silk": ("Silk", "#FF7A8A")
        }
        
        button_style_template = """
            QPushButton {{
                background-color: {};
                color: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 12px 18px;
                font-size: 12pt;
                font-weight: 600;
                min-width: 90px;
            }}
            QPushButton:hover {{
                background-color: #3D3F45;
                color: #ffffff;
                border: 2px solid {};
            }}
            QPushButton:checked {{
                background-color: #3D3F45;
                color: #ffffff;
                font-weight: 700;
                border: 2px solid {};
            }}
        """
        self.material_buttons = {}
        
        for material_id, (material_name, color) in materials.items():
            button = QPushButton(material_name)
            button.setCheckable(True)
            button.setStyleSheet(button_style_template.format(color, color, color))
            button.setProperty("material_id", material_id)
            button.clicked.connect(self.change_material)
            material_buttons_layout.addWidget(button)
            self.material_buttons[material_id] = button
        
        self.material_buttons["metal"].setChecked(True)
        
        right_layout.addLayout(material_buttons_layout)
        
        touchpad_title = QLabel("Touchpad")
        touchpad_title.setStyleSheet("""
            font-size: 16pt; 
            font-weight: 600; 
            color: #E8E8E8; 
            margin-bottom: 10px;
        """)
        touchpad_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(touchpad_title)
        
        # 터치패드 영역
        self.touch_pad = TouchPadWidget(self)
        self.touch_pad.setMinimumSize(350, 350)
        right_layout.addWidget(self.touch_pad, stretch=1)
        
        main_layout.addWidget(left_widget, stretch=2)
        main_layout.addWidget(right_widget, stretch=3)
        
    def initChart(self):
        self.speed_chart = QChart()
        self.current_series = QLineSeries()
        self.avg_series = QLineSeries()
        
        pen = QPen(QColor(66, 133, 244))
        pen.setWidth(2)
        self.current_series.setPen(pen)
        self.current_series.setName("Current Speed")
        
        pen = QPen(QColor(234, 67, 53))
        pen.setWidth(2)
        self.avg_series.setPen(pen)
        self.avg_series.setName("Average Speed")
        
        time_scale = 0.5 
        for i in range(self.data_points):
            scaled_time = i * time_scale
            self.current_series.append(scaled_time, 0)
            self.avg_series.append(scaled_time, 0)
        
        self.speed_chart.addSeries(self.current_series)
        self.speed_chart.addSeries(self.avg_series)
        
        value_axis = QValueAxis()
        value_axis.setRange(0, 3000)
        value_axis.setLabelsVisible(True)
        value_axis.setLabelFormat("%d")
        value_axis.setTitleText("Speed (px/s)")
        value_axis.setGridLineVisible(True)
        value_axis.setGridLineColor(QColor(60, 62, 66))  # 다크 그리드 라인
        value_axis.setTitleBrush(QColor(200, 200, 200))  # 밝은 타이틀 색상
        value_axis.setLabelsBrush(QColor(200, 200, 200)) # 밝은 라벨 색상
        
        time_axis = QValueAxis()
        time_axis.setRange(0, self.data_points * time_scale)
        time_axis.setLabelFormat("%.1f")
        time_axis.setTickCount(6)
        time_axis.setTitleText("Time (sec)")
        time_axis.setGridLineVisible(True)
        time_axis.setGridLineColor(QColor(60, 62, 66))  # 다크 그리드 라인
        time_axis.setTitleBrush(QColor(200, 200, 200))  # 밝은 타이틀 색상
        time_axis.setLabelsBrush(QColor(200, 200, 200)) # 밝은 라벨 색상
        
        self.speed_chart.addAxis(value_axis, Qt.AlignmentFlag.AlignLeft)
        self.speed_chart.addAxis(time_axis, Qt.AlignmentFlag.AlignBottom)
        
        self.current_series.attachAxis(time_axis)
        self.current_series.attachAxis(value_axis)
        self.avg_series.attachAxis(time_axis)
        self.avg_series.attachAxis(value_axis)
        
        self.speed_chart.legend().setVisible(True)
        self.speed_chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        self.speed_chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
        self.speed_chart.setBackgroundVisible(False)
        self.speed_chart.setMargins(QMargins(5, 5, 5, 5))
        self.speed_chart.setBackgroundBrush(QColor(45, 47, 51))  # 다크 배경색
        self.speed_chart.legend().setLabelColor(QColor(200, 200, 200))
        
        self.speed_chart_view.setChart(self.speed_chart)
        self.speed_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        self.tactile_chart = QChart()
        self.sa_series = QLineSeries()
        self.ra_series = QLineSeries()
        self.combined_series = QLineSeries()
        
        pen = QPen(QColor(52, 168, 83))  # 초록색
        pen.setWidth(2)
        self.sa_series.setPen(pen)
        self.sa_series.setName("SA (Slowly Adaptive)")
        
        pen = QPen(QColor(251, 188, 5))  # 노란색
        pen.setWidth(2)
        self.ra_series.setPen(pen)
        self.ra_series.setName("RA (Rapidly Adaptive)")
        
        pen = QPen(QColor(180, 180, 180))  # 회색
        pen.setWidth(2)
        self.combined_series.setPen(pen)
        self.combined_series.setName("SA+RA")
        
        for i in range(self.data_points):
            scaled_time = i * time_scale
            self.sa_series.append(scaled_time, 0)
            self.ra_series.append(scaled_time, 0)
            self.combined_series.append(scaled_time, 0)
        
        self.tactile_chart.addSeries(self.sa_series)
        self.tactile_chart.addSeries(self.ra_series)
        self.tactile_chart.addSeries(self.combined_series)
        
        value_axis = QValueAxis()
        value_axis.setRange(0, 2.0)  # 최대값 2.0으로 확장
        value_axis.setLabelsVisible(True)
        value_axis.setLabelFormat("%.1f")
        value_axis.setTitleText("Response Intensity")
        value_axis.setGridLineVisible(True)
        value_axis.setGridLineColor(QColor(60, 62, 66))  # 다크 그리드 라인
        value_axis.setTitleBrush(QColor(200, 200, 200))  # 밝은 타이틀 색상
        value_axis.setLabelsBrush(QColor(200, 200, 200)) # 밝은 라벨 색상
        
        time_axis = QValueAxis()
        time_axis.setRange(0, self.data_points * time_scale)
        time_axis.setLabelFormat("%.1f")
        time_axis.setTickCount(6)
        time_axis.setTitleText("Time (sec)")
        time_axis.setGridLineVisible(True)
        time_axis.setGridLineColor(QColor(60, 62, 66))  # 다크 그리드 라인
        time_axis.setTitleBrush(QColor(200, 200, 200))  # 밝은 타이틀 색상
        time_axis.setLabelsBrush(QColor(200, 200, 200)) # 밝은 라벨 색상
        
        self.tactile_chart.addAxis(value_axis, Qt.AlignmentFlag.AlignLeft)
        self.tactile_chart.addAxis(time_axis, Qt.AlignmentFlag.AlignBottom)
        
        self.sa_series.attachAxis(time_axis)
        self.sa_series.attachAxis(value_axis)
        self.ra_series.attachAxis(time_axis)
        self.ra_series.attachAxis(value_axis)
        self.combined_series.attachAxis(time_axis)
        self.combined_series.attachAxis(value_axis)
        
        # 차트 설정 - One UI 다크테마 스타일
        self.tactile_chart.legend().setVisible(True)
        self.tactile_chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        self.tactile_chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
        self.tactile_chart.setBackgroundVisible(False)
        self.tactile_chart.setMargins(QMargins(5, 5, 5, 5))
        self.tactile_chart.setBackgroundBrush(QColor(45, 47, 51))  # 다크 배경색
        self.tactile_chart.legend().setLabelColor(QColor(200, 200, 200))
        
        self.tactile_chart_view.setChart(self.tactile_chart)
        self.tactile_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)

    def initThreads(self):
        # 데이터 처리 스레드
        self.data_processor = DataProcessor()
        self.data_processor.data_processed.connect(self.onDataProcessed)
        self.data_processor.start()
        
        # 차트 업데이트 스레드
        self.chart_updater = ChartUpdater(self.speed_chart_view)
        self.chart_updater.start()
        
    def initVariables(self):
        # 클릭 관련 변수
        self.is_pressed = False
        self.press_start_time = 0
        self.last_move_time = 0
        self.press_duration = 0
        self.stationary_duration = 0
        
        # 속도 관련 변수
        self.last_pos = QPointF(0, 0)
        self.last_time = time.time()
        self.current_speed = 0
        self.avg_speed = 0
        self.last_speed = 0.0
        self.last_speed_change = 0.0
        
        # 촉각 수용체 변수
        self.sa_value = 0.0
        self.ra_value = 0.0
        self.sa_decay_rate = 0.996  # 5초에 걸쳐 0.3으로 감쇠 (60Hz 기준)
        self.sa_fast_decay_rate = 0.5  # SA 빠른 감쇠율 (클릭 해제 시)
        self.ra_decay_rate = 0.8   # RA 감쇠율
        self.sa_target = 0.0
        self.ra_target = 0.0
        self.sa_rise_rate = 1.0    # SA 상승률 (즉시 1.0으로)
        self.ra_sensitivity = 0.01  # RA 감도 (속도 변화율 기준)
        self.last_speed = 0.0
        self.last_click_state = False  # 클릭 상태 변화 감지용
        self.sa_start_value = 0.0  # SA 감쇠 시작값
        self.sa_decay_start_time = 0  # SA 감쇠 시작 시간
        self.sa_is_decaying = False  # SA 감쇠 상태
        
        # 실시간 처리를 위한 변수
        self.last_process_time = time.perf_counter()
        self.process_interval = 0.001
        
        self.wood_patterns = {}

    def periodicCleanup(self):
        current_time = time.time()
        if current_time - self.last_gc_time > self.gc_interval:
            gc.collect()
            self.last_gc_time = current_time
            
    def updatePerformanceMetrics(self):
        current_time = time.time()
        frame_time = (current_time - self._last_update_time) * 1000
        self.frame_times.append(frame_time)
        self._last_update_time = current_time
        
        if current_time - self.last_perf_log_time > self.PERFORMANCE_LOG_INTERVAL:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            print(f"Average frame time: {avg_frame_time:.2f}ms")
            self.last_perf_log_time = current_time
        
    def updateDisplay(self):
        current_time = time.perf_counter()
        
        if current_time - self.last_process_time >= self.process_interval:
            self.processData()
            self.last_process_time = current_time
            
            self.updateInfoDisplay()
            
    def processData(self):
        current_time = time.time()
        
        if not self.is_pressed or (current_time - self.last_move_time) > 0.05:  # 50ms 이상 움직임 없으면
            self.current_speed = 0
            
        self.speed_window.append(self.current_speed)
        self.avg_speed = np.mean(self.speed_window) if self.speed_window else 0
            
        self.updateTactileResponse()
        
        frame_time = (time.perf_counter() - self.last_process_time) * 1000
        self.frame_times.append(frame_time)
        
        if len(self.frame_times) == 60:
            avg_frame_time = np.mean(self.frame_times)
            print(f"Average frame time: {avg_frame_time:.2f}ms")
            self.frame_times.clear()

    def updateTactileResponse(self):
        current_time = time.time()

        is_touch_started = self.is_pressed and not self.last_click_state  # (False → True): 터치 시작 순간
        is_touch_released = not self.is_pressed and self.last_click_state  # (True → False): 터치 종료 순간

        if self.is_pressed:
            if is_touch_started:
                self.sa_value = 1.0
                self.sa_start_value = 1.0
                self.sa_decay_start_time = current_time
                self.sa_is_decaying = True
            elif self.sa_is_decaying:
                elapsed = current_time - self.sa_decay_start_time
                if elapsed <= 3.0:
                    decay = (elapsed / 3.0) ** 1.5
                    reduction = (self.sa_start_value - 0.3) * decay
                    self.sa_value = max(0.3, self.sa_start_value - reduction)
                else:
                    self.sa_value = 0.3
                    self.sa_is_decaying = False
        else:
            self.sa_value *= self.sa_fast_decay_rate
            self.sa_is_decaying = False

        if is_touch_started or is_touch_released:
            self.ra_value = 1.0
        elif self.is_pressed:
            if (current_time - self.last_move_time) > 0.05:
                self.ra_value *= self.ra_decay_rate
            else:
                max_speed = 3000.0
                norm_speed = min(1.0, self.avg_speed / max_speed)

                if self.avg_speed > 1500:
                    osc = 0.15 * np.sin(2 * np.pi * 5 * (current_time % 0.2))
                    norm_speed = min(1.0, norm_speed * (1.0 + osc))

                curve_factor = 2.5
                curved = 1.0 - np.exp(-curve_factor * norm_speed)

                material = self.audio_player.current_material
                if material == "metal" and self.avg_speed > 1000:
                    curved *= 1.2
                elif material == "wood":
                    curved *= 1.15
                elif material == "silk":
                    curved *= 0.9

                self.ra_value = max(curved, self.ra_value * 0.85)
                self.ra_value = min(1.0, self.ra_value)
        else:
            self.ra_value *= self.ra_decay_rate

        self.last_click_state = self.is_pressed

        material_weights = {
            "metal": {"sa": 0.7, "ra": 0.3},
            "glass": {"sa": 0.4, "ra": 0.6},
            "wood": {"sa": 0.6, "ra": 0.4},
            "fabric": {"sa": 0.4, "ra": 0.6},
            "silk": {"sa": 0.5, "ra": 0.5}
        }

        weights = material_weights.get(self.audio_player.current_material, {"sa": 0.5, "ra": 0.5})
        weighted_sa = self.sa_value * weights["sa"]
        weighted_ra = self.ra_value * weights["ra"]
        combined_value = min(1.0, weighted_sa + weighted_ra)

        self.audio_player.update_volume(combined_value)


    @jit(nopython=True)
    def _calculate_decay_progress(elapsed_time, duration=3.0, exponent=1.5):
        if elapsed_time <= duration:
            return (elapsed_time / duration) ** exponent
        return 1.0

    def updateInfoDisplay(self):
        current_time = time.time()
        
        touch_status = "Touching" if self.is_pressed else "Non Touching"
        status_color = "#4CAF50" if self.is_pressed else "#FF5252"  # 초록색/빨간색
        self.click_status_label.setText(f'<span style="color: {status_color}">{touch_status}</span>')
        
        if self.is_pressed:
            self.press_duration = current_time - self.press_start_time
        self.press_duration_label.setText(f'Touch Duration: {self.press_duration:.1f} sec')
        
        if self.is_pressed:
            self.stationary_duration = current_time - self.last_move_time
        self.stationary_duration_label.setText(f'Stationary Duration: {self.stationary_duration:.1f} sec')
        
        display_avg_speed = int(self.avg_speed) if self.avg_speed > 0.1 else 0
        self.avg_speed_label.setText(f'Average Speed: {display_avg_speed} px/s')
        
        self.sa_value_label.setText(f'SA Receptor Value: {self.sa_value:.1f}')
        self.ra_value_label.setText(f'RA Receptor Value: {self.ra_value:.1f}')

    def updateCharts(self):
        for i in range(self.data_points - 1):
            self.speed_data[i] = self.speed_data[i+1]
            self.avg_speed_data[i] = self.avg_speed_data[i+1]
            self.sa_data[i] = self.sa_data[i+1]
            self.ra_data[i] = self.ra_data[i+1]
        
        # 새 포인트 추가 (맨 마지막 인덱스)
        self.speed_data[self.data_points-1] = self.current_speed
        self.avg_speed_data[self.data_points-1] = self.avg_speed
        self.sa_data[self.data_points-1] = self.sa_value
        self.ra_data[self.data_points-1] = self.ra_value
        
        if hasattr(self, 'parallel_config') and self.parallel_config['use_threading']:
            time_scale = 0.5
            scaled_points = self._cached_points * time_scale
            
            self.scheduleParallelTask(self._update_chart_series, 
                                    self.current_series, scaled_points, self.speed_data)
            self.scheduleParallelTask(self._update_chart_series, 
                                    self.avg_series, scaled_points, self.avg_speed_data)
            self.scheduleParallelTask(self._update_chart_series, 
                                    self.sa_series, scaled_points, self.sa_data)
            self.scheduleParallelTask(self._update_chart_series, 
                                    self.ra_series, scaled_points, self.ra_data)
            
            combined = np.minimum(2.0, self.sa_data + self.ra_data)
            self.scheduleParallelTask(self._update_chart_series, 
                                    self.combined_series, scaled_points, combined)
        else:
            self._update_charts_direct()
            
    def _update_charts_direct(self):
        self.current_series.clear()
        self.avg_series.clear()
        self.sa_series.clear()
        self.ra_series.clear()
        self.combined_series.clear()
        
        time_scale = 0.5  
        
        for i in range(self.data_points):
            scaled_time = i * time_scale
            
            self.current_series.append(scaled_time, self.speed_data[i])
            self.avg_series.append(scaled_time, self.avg_speed_data[i])
            
            self.sa_series.append(scaled_time, self.sa_data[i])
            self.ra_series.append(scaled_time, self.ra_data[i])
            
            combined = min(2.0, self.sa_data[i] + self.ra_data[i]) 
            self.combined_series.append(scaled_time, combined)
            
    def _update_chart_series(self, series, points, values):
        series.blockSignals(True)
        
        try:
            series.clear()
            
            for i in range(len(points)):
                series.append(points[i], values[i])
        finally:
            series.blockSignals(False)
        
    def onDataProcessed(self, current_speed, avg_speed):
        max_speed = 3000
        current_speed = min(current_speed, max_speed)
        
        if abs(current_speed - self.current_speed) > max_speed / 2:
            current_speed = (current_speed + self.current_speed) / 2
            
        self.current_speed = current_speed
        self.avg_speed = avg_speed
        self.chart_updater.update_data(current_speed, avg_speed)
        
    def checkMemoryUsage(self):
        process = psutil.Process()
        memory_info = process.memory_info()
        
        if memory_info.rss > 300 * 1024 * 1024:  
            gc.collect()
            
            if hasattr(self, '_temp_objects'):
                self._temp_objects.clear()
        
    def closeEvent(self, event):
        self.data_processor.stop()
        self.data_processor.wait()
        self.thread_pool.shutdown()
        self.process_pool.shutdown()
        self.update_timer.stop()
        self.chart_timer.stop()
        
        self.audio_player.cleanup()
        
        super().closeEvent(event)
        
    def change_material(self):
        sender = self.sender()
        if isinstance(sender, QPushButton) and sender.isChecked():
            for button in self.material_buttons.values():
                if button != sender:
                    button.setChecked(False)
            
            material_id = sender.property("material_id")
            print(f"재질 변경: {material_id}")
            
            self.audio_player.set_material(material_id)
            
            self.touch_pad.set_material(material_id)
        
    def handlePress(self, position):
        self.is_pressed = True
        current_time = time.time()
        self.press_start_time = current_time
        self.last_move_time = current_time
        self.last_pos = position
        self.last_time = current_time
        self.stationary_duration = 0
        self.data_processor.set_pressed(True)
        
        self.audio_player.play_event("touch_start")
        
    def handleRelease(self):
        self.is_pressed = False
        self.press_duration = time.time() - self.press_start_time
        self.current_speed = 0
        self.avg_speed = 0
        self.data_processor.set_pressed(False)
        
        self.audio_player.play_event("touch_end")
        
    def handleMove(self, position):
        if not self.is_pressed:
            return
        
        current_time = time.time()
        dt = current_time - self.last_time
        
        if dt > 0:
            # QPointF 연산 최적화
            dx = position.x() - self.last_pos.x()
            dy = position.y() - self.last_pos.y()
            
            # 속도 계산 최적화 (제곱근 직접 구현)
            dist_squared = dx * dx + dy * dy
            if dist_squared > 1.0:  
                self.current_speed = min(np.sqrt(dist_squared) / dt, 3000) 
                self.last_move_time = current_time
                
                if dist_squared > 100:  # 10픽셀 이상 이동

                    angle = np.degrees(np.arctan2(dy, dx))
                    
                    haptic_angle = (90 - angle) % 360
                    
                    direction_intensity = min(self.current_speed / 1000, 0.8)
                    self.audio_player.set_direction(haptic_angle, direction_intensity)
        
        self.last_pos = position
        self.last_time = current_time

    def handleExit(self, position):
        if not self.is_pressed:
            return
        
        print("터치패드 이탈 감지!")

        self.is_pressed = False
        self.press_duration = time.time() - self.press_start_time
        self.current_speed = 0
        self.avg_speed = 0
        self.data_processor.set_pressed(False)
        
        self.audio_player.event_channel.set_volume(1.0)
        self.audio_player.play_event("touch_exit")
        
        QTimer.singleShot(150, lambda: self.audio_player.update_volume(0.0))