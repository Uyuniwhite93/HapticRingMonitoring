from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget,
                           QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QComboBox, QGridLayout) # Added QGridLayout
from PyQt6.QtCore import Qt, QPointF, QTimer, QRectF, QThread, pyqtSignal, QMargins
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QPainterPath, QPixmap, QRadialGradient, QFont, QFontDatabase, QCursor
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis

import numpy as np
import time
from collections import deque

from ui.touch_pad import TouchPadWidget
from ui.charts import ChartView
# from core.audio_player import HapticAudioPlayer # Removed
from core.processing import DataProcessor, ChartUpdater

class HapticMonitor(QMainWindow):
    DATA_POINTS = 50

    def __init__(self):
        super().__init__()

        # self.setupFonts() # Simplified: Use system default font

        self.data_points = self.DATA_POINTS
        self.speed_data = np.zeros(self.data_points, dtype=np.float32)
        self.avg_speed_data = np.zeros(self.data_points, dtype=np.float32)
        # self.sa_data = np.zeros(self.data_points, dtype=np.float32) # Removed
        # self.ra_data = np.zeros(self.data_points, dtype=np.float32) # Removed

        self.speed_window = deque(maxlen=5)
        self.chart_update_counter = 0
        self.chart_update_interval = 3 # Update chart every 3 data points

        # self.audio_player = HapticAudioPlayer() # Removed

        self.initUI()
        self.initVariables()
        self.initChart()
        self.initThreads()

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.updateDisplay)
        self.update_timer.start(16)  # Approx 60Hz

        self.chart_timer = QTimer()
        self.chart_timer.timeout.connect(self.updateCharts)
        self.chart_timer.start(50)  # 20Hz

        self._last_update_time = time.time()
        self.last_process_time = time.perf_counter()
        self.process_interval = 0.001 # 1kHz target for data processing

    # def setupFonts(self): # Simplified, system default font will be used
    #     pass

    def initUI(self):
        self.setWindowTitle('Haptic Monitor')
        self.setGeometry(100, 100, 1000, 500) # Adjusted size

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #222428;
            }
            QLabel {
                color: #E8E8E8;
            }
            QComboBox {
                color: #E8E8E8;
                background-color: #323438;
                border: 1px solid #45474D;
                padding: 5px;
                border-radius: 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png); /* Placeholder, consider embedding or using a standard icon */
                width: 12px;
                height: 12px;
            }
            QPushButton { /* Style for material buttons */
                color: #E8E8E8;
                background-color: #323438;
                border: 1px solid #45474D;
                padding: 8px;
                border-radius: 4px;
                min-height: 25px; 
            }
            QPushButton:hover {
                background-color: #424448;
            }
            QPushButton:pressed {
                background-color: #222428;
            }
        """)

        # Apply a dark theme palette
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
        # self.sa_value_label = QLabel('SA Receptor Value: 0.000') # Removed
        # self.ra_value_label = QLabel('RA Receptor Value: 0.000') # Removed

        label_style = """
            QLabel {
                color: #E8E8E8;
                background-color: rgba(55, 57, 62, 0.9);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 10pt; /* Adjusted font size */
                font-weight: 500;
                border: 1px solid #45474D;
                qproperty-alignment: AlignLeft; /* Changed to AlignLeft */
            }
        """

        for label in [self.click_status_label, self.press_duration_label,
                     self.stationary_duration_label, self.avg_speed_label]: # SA/RA labels removed
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            label.setMinimumHeight(36)
            label.setStyleSheet(label_style)
            info_layout.addWidget(label)

        left_layout.addWidget(info_frame, stretch=1)

        graphs_widget = QWidget() # This will now only contain the speed chart
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
        self.speed_chart_view.setMinimumSize(300, 150) # Adjusted size
        speed_chart_layout.addWidget(self.speed_chart_view)
        graphs_layout.addWidget(speed_chart_frame)

        # Tactile chart removed
        # tactile_chart_frame = QFrame() ...
        # self.tactile_chart_view = ChartView() ...

        left_layout.addWidget(graphs_widget, stretch=2)
        main_layout.addWidget(left_widget, stretch=1) # Left panel takes less space

        # Right panel for TouchPad and Material Selection
        right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout(right_panel_widget)
        right_panel_layout.setSpacing(15)
        right_panel_layout.setContentsMargins(0,0,0,0)


        self.touch_pad = TouchPadWidget(self)
        self.touch_pad.setMinimumSize(400,300) # Ensure touch pad has a good size
        right_panel_layout.addWidget(self.touch_pad, stretch=3) # TouchPad takes more space

        # Material selection Buttons
        material_control_frame = QFrame()
        material_control_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        material_control_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(50, 52, 56, 0.9);
                border-radius: 10px;
                border: 1px solid #3C3E44;
                padding: 10px;
            }
        """)
        material_layout = QGridLayout(material_control_frame) # Use QGridLayout for buttons

        material_label = QLabel("Material:")
        material_label.setStyleSheet("background-color: transparent; border: none; font-size: 10pt; padding-right: 5px; qproperty-alignment: AlignCenter;")
        material_layout.addWidget(material_label, 0, 0, 1, 2) # Span label across two columns

        materials = ["metal", "glass", "wood", "fabric", "silk"]
        self.material_buttons = {}
        for i, material_name in enumerate(materials):
            button = QPushButton(material_name.capitalize())
            button.clicked.connect(lambda checked=False, name=material_name: self.change_material_selection(name))
            self.material_buttons[material_name] = button
            row, col = divmod(i, 2) # Arrange buttons in 2 columns
            material_layout.addWidget(button, row + 1, col)
        
        # Set initial button state (optional, if you want to show active material)
        # self.update_material_button_states(self.touch_pad.current_material)


        # self.material_combo = QComboBox() # Removed ComboBox
        # materials = ["metal", "glass", "wood", "fabric", "silk"]
        # self.material_combo.addItems(materials)
        # self.material_combo.setCurrentText(self.touch_pad.current_material)
        # self.material_combo.currentTextChanged.connect(self.change_material_selection)
        # self.material_combo.setMinimumWidth(100)
        # material_layout.addWidget(self.material_combo)
        # material_layout.addStretch()


        right_panel_layout.addWidget(material_control_frame, stretch=1)


        main_layout.addWidget(right_panel_widget, stretch=2) # Right panel takes more space


    def initChart(self):
        # Speed Chart Initialization
        chart = QChart()
        chart.setBackgroundBrush(QBrush(QColor(40, 42, 46))) # Darker background for chart
        chart.setPlotAreaBackgroundBrush(QBrush(QColor(34, 36, 40)))
        chart.setPlotAreaBackgroundVisible(True)
        chart.setMargins(QMargins(5,5,5,5)) # Reduced margins

        self.speed_series = QLineSeries()
        pen = QPen(QColor(0, 160, 255)) # Blue color for speed
        pen.setWidth(2)
        self.speed_series.setPen(pen)
        chart.addSeries(self.speed_series)

        self.avg_speed_series = QLineSeries()
        pen_avg = QPen(QColor(255, 100, 0)) # Orange color for average speed
        pen_avg.setWidth(2)
        pen_avg.setStyle(Qt.PenStyle.DashLine)
        self.avg_speed_series.setPen(pen_avg)
        chart.addSeries(self.avg_speed_series)

        axis_x = QValueAxis()
        axis_x.setRange(0, self.data_points -1)
        axis_x.setLabelFormat("%d")
        axis_x.setTickCount(min(self.data_points, 11)) # Max 11 ticks
        axis_x.setTitleText("Time (samples)")
        axis_x.setLabelsColor(QColor(200,200,200))
        axis_x.setTitleBrush(QBrush(QColor(200,200,200)))
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self.speed_series.attachAxis(axis_x)
        self.avg_speed_series.attachAxis(axis_x)

        axis_y_speed = QValueAxis()
        axis_y_speed.setRange(0, 10000) # Fixed Y-axis range to 0-10000
        axis_y_speed.setLabelFormat("%.0f") # Integer format for larger numbers
        axis_y_speed.setTickCount(11) # Adjust tick count for new range
        axis_y_speed.setTitleText("Speed (px/s)")
        axis_y_speed.setLabelsColor(QColor(200,200,200))
        axis_y_speed.setTitleBrush(QBrush(QColor(200,200,200)))
        chart.addAxis(axis_y_speed, Qt.AlignmentFlag.AlignLeft)
        self.speed_series.attachAxis(axis_y_speed)
        self.avg_speed_series.attachAxis(axis_y_speed)
        self.speed_chart_view.y_axis = axis_y_speed # Store for dynamic range update

        self.speed_chart_view.setChart(chart)
        self.speed_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Tactile Chart Initialization Removed

    def initThreads(self):
        self.data_processor = DataProcessor(window_size=30)
        self.data_processor.data_processed.connect(self.onDataProcessed)
        self.data_processor.start()

        # ChartUpdater is simplified/integrated into updateCharts
        # self.chart_updater = ChartUpdater(self.speed_chart_view, self.data_points) # Simplified
        # self.chart_updater.start() # Simplified

    def initVariables(self):
        self.is_pressed = False
        self.last_pos = QPointF(0, 0)
        self.press_start_time = 0
        self.stationary_start_time = 0
        self.last_move_time = 0
        self.current_speed = 0.0
        self.average_speed = 0.0
        self.was_moving = False # To track if previously moving for stationary calc

        self.max_speed_observed = 0.0 # For dynamic chart Y-axis scaling (though Y-axis is now fixed)

    def updateDisplay(self):
        now = time.time()
        # dt = now - self._last_update_time # Not directly used for fixed timer
        self._last_update_time = now

        # Process data at a fixed interval if enough time has passed
        current_perf_time = time.perf_counter()
        if current_perf_time - self.last_process_time >= self.process_interval:
            self.processData()
            self.last_process_time = current_perf_time

        self.updateInfoDisplay()
        # self.updateCharts() # Moved to its own timer

    def processData(self):
        if self.is_pressed:
            # This part would typically get (dx, dy, dt) from some input source.
            # For this stripped-down version, we'll rely on mouseMoveEvent providing data.
            # If direct processing is needed here, it requires a data source.
            pass # Data is added via add_data in handleMove

    # updateTactileResponse removed

    def updateInfoDisplay(self):
        status_text = 'Touching' if self.is_pressed else 'Not Touching'
        self.click_status_label.setText(f'Touch Status: {status_text}')

        duration_text = f'{time.time() - self.press_start_time:.3f} sec' if self.is_pressed else '0.000 sec'
        self.press_duration_label.setText(f'Touch Duration: {duration_text}')

        # Stationary duration is now calculated based on self.current_speed updated by onDataProcessed
        # and self.stationary_start_time updated in onDataProcessed when stopping.
        stat_dur = 0.0
        if self.is_pressed and self.current_speed < 1.0:
            stat_dur = time.time() - self.stationary_start_time
        stationary_text = f'{stat_dur:.3f} sec'
        self.stationary_duration_label.setText(f'Stationary Duration: {stationary_text}')

        self.avg_speed_label.setText(f'Average Speed: {self.average_speed:.1f} px/s')

    def updateCharts(self):
        # Direct update of chart series
        points_speed = []
        points_avg_speed = []
        for i in range(self.data_points):
            points_speed.append(QPointF(i, self.speed_data[i]))
            points_avg_speed.append(QPointF(i, self.avg_speed_data[i]))

        self.speed_series.replace(points_speed)
        self.avg_speed_series.replace(points_avg_speed)

        # Dynamically adjust Y-axis range for speed chart
        # current_max_on_chart = max(np.max(self.speed_data), np.max(self.avg_speed_data), 10) # Ensure at least 10 # Removed
        # if current_max_on_chart > self.max_speed_observed or current_max_on_chart < self.max_speed_observed * 0.5: # Removed
        #      self.max_speed_observed = current_max_on_chart * 1.2 # Add some headroom # Removed
        #      if hasattr(self.speed_chart_view, 'y_axis'): # Removed
        #          self.speed_chart_view.y_axis.setRange(0, self.max_speed_observed) # Removed
    
    def update_material_button_states(self, active_material):
        for material_name, button in self.material_buttons.items():
            if material_name == active_material:
                button.setStyleSheet("""
                    QPushButton { 
                        color: #E8E8E8; background-color: #007AFF; /* Highlight active */
                        border: 1px solid #0056b3; padding: 8px; border-radius: 4px; min-height: 25px;
                    }""")
            else:
                button.setStyleSheet("""
                    QPushButton {
                        color: #E8E8E8; background-color: #323438; 
                        border: 1px solid #45474D; padding: 8px; border-radius: 4px; min-height: 25px;
                    }
                    QPushButton:hover { background-color: #424448; }
                    QPushButton:pressed { background-color: #222428; }
                """)

    def onDataProcessed(self, current_speed, avg_speed):
        self.current_speed = current_speed
        self.average_speed = avg_speed # This should be 0.0 if not pressed, from DataProcessor

        if self.is_pressed:
            if current_speed < 1.0: # Currently stationary
                if self.was_moving: # Was moving, now stopped
                    self.stationary_start_time = time.time()
                    self.was_moving = False
                # else: still stationary, stationary_start_time is already set
            else: # Currently moving
                self.stationary_start_time = time.time() # Keep updating start_time while moving
                self.was_moving = True
        else: # Not pressed
            self.stationary_start_time = time.time() # Reset
            self.was_moving = False

        # Update data arrays for charts
        self.speed_data = np.roll(self.speed_data, -1)
        self.avg_speed_data = np.roll(self.avg_speed_data, -1)
        self.speed_data[-1] = self.current_speed
        self.avg_speed_data[-1] = self.average_speed # If avg_speed from processor is 0, this becomes 0

        # Chart update is handled by its own timer (self.chart_timer)

    def closeEvent(self, event):
        print("Closing application...")
        if hasattr(self, 'data_processor') and self.data_processor.isRunning():
            self.data_processor.stop()
            self.data_processor.wait() # Wait for thread to finish
        # if hasattr(self, 'audio_player'): # Removed
        #    self.audio_player.cleanup()
        event.accept()

    def change_material_selection(self, material_name):
        if self.touch_pad:
            self.touch_pad.set_material(material_name)
        if hasattr(self, 'update_material_button_states'): # Check if method exists (it should)
            self.update_material_button_states(material_name)
        # self.audio_player.set_material(material_name) # Removed


    def handlePress(self, position):
        if not self.is_pressed:
            self.is_pressed = True
            self.last_pos = position
            self.press_start_time = time.time()
            self.stationary_start_time = time.time() # Initialize stationary time on press
            self.last_move_time = time.time()
            self.was_moving = False # Assume not moving initially on new press
            if hasattr(self, 'data_processor'):
                self.data_processor.set_pressed(True)

    def handleRelease(self):
        if self.is_pressed:
            self.is_pressed = False
            if hasattr(self, 'data_processor'):
                self.data_processor.set_pressed(False) # Processor will emit (0,0)
            
            self.current_speed = 0.0
            self.average_speed = 0.0        # Explicitly set to 0
            self.speed_data.fill(0.0)       
            self.avg_speed_data.fill(0.0)   # Fill with 0
            self.was_moving = False
            self.stationary_start_time = time.time() # Reset stationary time

            self.updateInfoDisplay()      
            self.updateCharts()           


    def handleMove(self, position):
        if self.is_pressed:
            current_time = time.time()
            dt = current_time - self.last_move_time
            if dt > 0.0001: # Ensure dt is not too small or zero
                dx = position.x() - self.last_pos.x()
                dy = position.y() - self.last_pos.y()

                if hasattr(self, 'data_processor'):
                    self.data_processor.add_data(dx, dy, dt)
                
                # Stationary start time is now handled in onDataProcessed
                # if self.current_speed >= 1.0: 
                #     self.stationary_start_time = current_time

            self.last_pos = position
            self.last_move_time = current_time

    def handleExit(self, position):
        if self.is_pressed:
            self.is_pressed = False
            if hasattr(self, 'data_processor'):
                self.data_processor.set_pressed(False) # Processor will emit (0,0)

            self.current_speed = 0.0
            self.average_speed = 0.0        # Explicitly set to 0
            self.speed_data.fill(0.0)
            self.avg_speed_data.fill(0.0)   # Fill with 0
            self.was_moving = False
            self.stationary_start_time = time.time() # Reset stationary time

            self.updateInfoDisplay()
            self.updateCharts()
            print(f"Exited pad at {position.x()},{position.y()}") 