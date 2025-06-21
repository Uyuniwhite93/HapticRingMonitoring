'''
Haptic Ring Monitoring - 햅틱 피드백 시뮬레이션 메인 프로그램
Izhikevich 뉴런 모델을 사용하여 촉각 수용체(SA, RA)의 반응을 시뮬레이션하고
마우스 입력을 실시간 오디오 피드백으로 변환하는 햅틱 렌더링 시스템

전체 시스템 구조:
마우스 입력 → SpikeEncoder → 뉴런 시뮬레이션 → HapticRenderer → AudioPlayer → 소리 출력
                                    ↓
                           실시간 그래프 시각화
'''

import sys
import numpy as np
import pygame
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import QTimer, Qt, QPointF
from PyQt6.QtGui import QKeyEvent
import time
from collections import deque
import logging
import os

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Matplotlib 설정 - 실시간 뉴런 상태 시각화용
import matplotlib
matplotlib.use('QtAgg')  # PyQt6과 호환되는 백엔드 사용

# 다크 테마 시각화 설정
matplotlib.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Helvetica Neue', 'Arial', 'DejaVu Sans'],
    'axes.titlesize': 14,
    'axes.labelsize': 11,
    'xtick.labelsize': 9, 
    'ytick.labelsize': 9,
    'legend.fontsize': 10,
    'figure.dpi': 100,
    'figure.facecolor': '#1c1c1e',    # 다크 배경
    'axes.facecolor': '#1c1c1e',      # 축 배경
    'axes.edgecolor': '#a0a0a0',      # 축 테두리
    'axes.labelcolor': '#e0e0e0',     # 축 라벨 색상
    'text.color': '#f0f0f0',          # 텍스트 색상
    'xtick.color': '#c0c0c0',         # X축 눈금 색상
    'ytick.color': '#c0c0c0',         # Y축 눈금 색상
    'grid.color': '#505050',          # 격자 색상
    'grid.linestyle': '--',           # 격자 스타일
    'grid.alpha': 0.7,                # 격자 투명도
    'lines.linewidth': 1.8            # 라인 두께
})

# 모듈 임포트 - 각 모듈의 역할
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from izhikevich_neuron import IzhikevichNeuron  # 뉴런 시뮬레이션
from audio_player import AudioPlayer              # 오디오 재생
from haptic_renderer import HapticRenderer        # 사운드 생성
from spike_encoder import SpikeEncoder            # 마우스→뉴런 변환
from ClassCommunication import CommunicationModule # 통신 모듈

class Constants:
    """애플리케이션 전역 상수 정의"""
    DEFAULT_WINDOW_WIDTH = 1200        # 기본 윈도우 너비
    DEFAULT_WINDOW_HEIGHT = 1200       # 기본 윈도우 높이
    SPIKE_THRESHOLD = 30.0             # 스파이크 감지 임계값 (mV)
    MIN_MOUSE_DELTA_TIME = 0.0001      # 마우스 이벤트 최소 간격
    SPIKE_LINE_COLOR = '#e60026'       # 스파이크 표시 색상 (빨간색)
    SA_LINE_COLOR = '#007aff'          # SA 뉴런 표시 색상 (파란색)
    RA_LINE_COLOR = '#ff9500'          # RA 뉴런 표시 색상 (주황색)
    FADE_OUT_MS = 10                   # 사운드 페이드아웃 시간
    PLOT_Y_MIN = -90                   # 그래프 Y축 최소값
    PLOT_Y_MAX = 40                    # 그래프 Y축 최대값

class TestWindow(QMainWindow):
    """
    햅틱 피드백 시뮬레이션 메인 윈도우 클래스
    
    기능:
    1. SA/RA 뉴런의 실시간 상태 시각화 (막전위, 회복변수)
    2. 마우스 입력을 뉴런 자극으로 변환
    3. 뉴런 스파이크를 실시간 오디오로 출력
    4. 다양한 재질(S, M, R) 시뮬레이션
    5. 키보드 단축키로 시뮬레이션 제어
    
    데이터 흐름:
    마우스 입력 → SpikeEncoder → 뉴런 시뮬레이션 → 그래프 업데이트 + 오디오 출력
    """
    
    def __init__(self):
        """메인 윈도우 초기화 및 모든 컴포넌트 설정"""
        super().__init__()
        self.setWindowTitle("Izhikevich Haptic Test")
        self.setGeometry(50,50,Constants.DEFAULT_WINDOW_WIDTH,Constants.DEFAULT_WINDOW_HEIGHT)

        # 설정 로드 및 검증
        self.config = self._get_validated_config()
        self.neuron_dt_ms = self.config['neuron_dt_ms']  # 뉴런 시뮬레이션 시간 간격

        # === UI 구성 요소 초기화 ===
        main_w=QWidget(); layout=QVBoxLayout(main_w)
        main_w.setStyleSheet("background-color: #48484a;")  # 다크 테마 배경
        
        # 사용법 안내 라벨
        self.info_lbl=QLabel("Click/SA+RA_Click, Move/RA_Motion (1-7 Materials)",self)
        fnt=self.info_lbl.font();fnt.setPointSize(16);self.info_lbl.setFont(fnt)
        self.info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_lbl)
        
        # 상태 정보 라벨 (현재 재질, 마우스 속도, 볼륨 등)
        self.stat_lbl=QLabel("Mat:Glass(R:0.5)|Spd:0",self)
        fnt=self.stat_lbl.font();fnt.setPointSize(14);self.stat_lbl.setFont(fnt)
        self.stat_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stat_lbl)

        # === 데이터 히스토리 초기화 (실시간 그래프용) ===
        self.plot_hist_sz=self.config['plot_hist_sz']  # 그래프에 표시할 데이터 포인트 수 (500개)
        
        # SA 뉴런 히스토리 초기화
        v_init_val_sa = self.config['sa_neuron']['v_init']  # SA 뉴런 초기 막전위
        sa_params = self.config['sa_neuron']
        u_init_sa = IzhikevichNeuron(sa_params['a'], sa_params['b'], sa_params['c'], sa_params['d'], v_init=v_init_val_sa).u
        self.sa_v_hist=deque([v_init_val_sa]*self.plot_hist_sz, maxlen=self.plot_hist_sz)  # SA 막전위 히스토리
        self.sa_u_hist=deque([u_init_sa]*self.plot_hist_sz, maxlen=self.plot_hist_sz)      # SA 회복변수 히스토리
        
        # RA 움직임 뉴런 히스토리 초기화
        v_init_val_ra_motion = self.config['ra_neuron']['v_init']  # RA 움직임 뉴런 초기 막전위
        ra_params_base = self.config['ra_neuron']
        u_init_ra_motion = IzhikevichNeuron(ra_params_base['base_a'], ra_params_base['base_b'], ra_params_base['base_c'], ra_params_base['base_d'], v_init=v_init_val_ra_motion).u
        self.ra_motion_v_hist=deque([v_init_val_ra_motion]*self.plot_hist_sz, maxlen=self.plot_hist_sz)  # RA 움직임 막전위 히스토리
        self.ra_motion_u_hist=deque([u_init_ra_motion]*self.plot_hist_sz, maxlen=self.plot_hist_sz)      # RA 움직임 회복변수 히스토리
        
        # RA 클릭 뉴런 히스토리 초기화
        v_init_val_ra_click = self.config['ra_click_neuron']['v_init']  # RA 클릭 뉴런 초기 막전위
        ra_click_params = self.config['ra_click_neuron']
        u_init_ra_click = IzhikevichNeuron(ra_click_params['a'], ra_click_params['b'], ra_click_params['c'], ra_click_params['d'], v_init=v_init_val_ra_click).u
        self.ra_click_v_hist=deque([v_init_val_ra_click]*self.plot_hist_sz, maxlen=self.plot_hist_sz)  # RA 클릭 막전위 히스토리
        self.ra_click_u_hist=deque([u_init_ra_click]*self.plot_hist_sz, maxlen=self.plot_hist_sz)      # RA 클릭 회복변수 히스토리
        
        self.x_data=np.arange(self.plot_hist_sz)  # X축 데이터 (시간축)

        # === 그래프 설정 (3개 뉴런용) ===
        self.fig=Figure(figsize=(7,8)); self.ax_sa,self.ax_ra_motion,self.ax_ra_click=self.fig.subplots(3,1)
        # SA 뉴런 그래프 설정
        self.sa_v_line,=self.ax_sa.plot(self.x_data,list(self.sa_v_hist),lw=1.8,label='SA_v', color='#007aff')
        self.sa_u_line,=self.ax_sa.plot(self.x_data,list(self.sa_u_hist),lw=1.8,label='SA_u', color='#ff9500')
        self.ax_sa.set_title('SA Neuron (Pressure)')
        self.ax_sa.set_ylabel('V (mV), U', fontsize=11)
        self.ax_sa.set_ylim(-90,40)
        self.ax_sa.set_xlim(0,self.plot_hist_sz-1);self.ax_sa.legend(loc='upper right', frameon=False);self.ax_sa.grid(True)
        self.ax_sa.spines['top'].set_visible(False); self.ax_sa.spines['right'].set_visible(False)

        tick_locs = np.linspace(0, self.plot_hist_sz - 1, 6)
        tick_labels = np.linspace(2500, 0, 6).astype(int)
        self.ax_sa.set_xticks(tick_locs)
        self.ax_sa.set_xticklabels(tick_labels)

        # RA 움직임 뉴런 그래프 설정
        self.ra_motion_v_line,=self.ax_ra_motion.plot(self.x_data,list(self.ra_motion_v_hist),lw=1.8,label='RA_Motion_v', color='#007aff')
        self.ra_motion_u_line,=self.ax_ra_motion.plot(self.x_data,list(self.ra_motion_u_hist),lw=1.8,label='RA_Motion_u', color='#ff9500')
        self.ax_ra_motion.set_title('RA Motion Neuron (Movement)')
        self.ax_ra_motion.set_ylabel('V (mV), U', fontsize=11)
        self.ax_ra_motion.set_ylim(-90,40)
        self.ax_ra_motion.set_xlim(0,self.plot_hist_sz-1);self.ax_ra_motion.legend(loc='upper right', frameon=False);self.ax_ra_motion.grid(True)
        self.ax_ra_motion.spines['top'].set_visible(False); self.ax_ra_motion.spines['right'].set_visible(False)
        self.ax_ra_motion.set_xticks(tick_locs)
        self.ax_ra_motion.set_xticklabels(tick_labels)

        # RA 클릭 뉴런 그래프 설정
        self.ra_click_v_line,=self.ax_ra_click.plot(self.x_data,list(self.ra_click_v_hist),lw=1.8,label='RA_Click_v', color='#007aff')
        self.ra_click_u_line,=self.ax_ra_click.plot(self.x_data,list(self.ra_click_u_hist),lw=1.8,label='RA_Click_u', color='#ff9500')
        self.ax_ra_click.set_title('RA Click Neuron (Click On/Off)')
        self.ax_ra_click.set_ylabel('V (mV), U', fontsize=11)
        self.ax_ra_click.set_ylim(-90,40)
        self.ax_ra_click.set_xlabel('Time (ms)', fontsize=12)
        self.ax_ra_click.set_xlim(0,self.plot_hist_sz-1);self.ax_ra_click.legend(loc='upper right', frameon=False);self.ax_ra_click.grid(True)
        self.ax_ra_click.spines['top'].set_visible(False); self.ax_ra_click.spines['right'].set_visible(False)
        self.ax_ra_click.set_xticks(tick_locs)
        self.ax_ra_click.set_xticklabels(tick_labels)

        self.fig.tight_layout(pad=3.0);self.plot_canvas=FigureCanvas(self.fig)
        layout.addWidget(self.plot_canvas);self.setCentralWidget(main_w)

        self.audio_player = AudioPlayer()
        self.haptic_renderer = HapticRenderer()

        self.spike_encoder = SpikeEncoder(
            sa_params=self.config['sa_neuron'],
            ra_params=self.config['ra_neuron'],
            ra_click_params=self.config['ra_click_neuron'],
            neuron_dt_ms=self.config['neuron_dt_ms'],
            input_config=self.config['input_current']
        )
        self.commModule = CommunicationModule() # 통신 인스턴스 생성

        self.materials = self.config['materials']
        self.mat_keys=list(self.materials.keys())
        self.curr_mat_key=self.mat_keys[0] 
        self.mat_roughness=self.materials[self.curr_mat_key]['r']

        self.sound_cache = {}
        self._init_sounds()

        # === 기존 개별 뉴런 변수들은 이제 SpikeEncoder에서 관리됨 ===
        # 모든 뉴런 시뮬레이션은 self.spike_encoder.step()을 통해 처리

        self.m_pressed=False;self.last_m_pos=QPointF(0,0)
        self.last_m_t=time.perf_counter();self.m_spd=0.0
        mouse_cfg = self.config['mouse']
        self.max_spd_clamp=mouse_cfg['max_spd_clamp']
        self.m_stop_thresh=mouse_cfg['m_stop_thresh']
        self.spd_hist=deque(maxlen=10);self.avg_m_spd=0.0

        self.plot_upd_cnt=0
        self.plot_upd_interval=self.config['plot']['update_interval']
        self.sa_spike_idxs=deque(maxlen=self.plot_hist_sz)
        self.ra_motion_spike_idxs=deque(maxlen=self.plot_hist_sz)
        self.ra_click_spike_idxs=deque(maxlen=self.plot_hist_sz)
        self.drawn_spike_lines=[]

        self.update_stat_lbl()
        self.timer=QTimer(self);self.timer.timeout.connect(self.update_neuron);self.timer.start(int(self.neuron_dt_ms))

        self.last_neuron_update_time = time.perf_counter()

    def _init_sounds(self):
        """사운드 객체들 초기화 - SA, RA 움직임, RA 클릭 각각 다른 주파수"""
        snd_cfg = self.config['sound']
        
        # SA 뉴런 사운드 (낮은 주파수, 긴 지속시간)
        self.sa_snd = self.haptic_renderer.create_sound_object(
            snd_cfg['sa_hz'], snd_cfg['sa_ms'], snd_cfg['sa_amp'], fade_out_ms=10
        )
        
        # 재질별로 RA 움직임과 RA 클릭 사운드 생성
        for mat_key, mat_props in self.materials.items():
            # RA 움직임 뉴런 사운드 (재질별 특화 파형)
            ra_motion_hz = int(snd_cfg['ra_motion_base_hz'] * mat_props['f'])
            ra_motion_cache_key = f"ra_motion_{mat_key}_{ra_motion_hz}"
            
            if 'type' in mat_props:
                # 재질별 특성 파라미터 추출
                material_params = {k: v for k, v in mat_props.items() if k not in ['r', 'f', 'type']}
                self.sound_cache[ra_motion_cache_key] = self.haptic_renderer.create_material_sound(
                    mat_props['type'], ra_motion_hz, snd_cfg['ra_motion_ms'], snd_cfg['ra_motion_base_amp'], 
                    fade_out_ms=10, **material_params
                )
                print(f"Created {mat_props['type']} RA_Motion sound for {mat_key}: {ra_motion_hz}Hz with params {material_params}")
            else:
                # 기본 사인파 사용
                self.sound_cache[ra_motion_cache_key] = self.haptic_renderer.create_sound_object(
                    ra_motion_hz, snd_cfg['ra_motion_ms'], snd_cfg['ra_motion_base_amp'], fade_out_ms=10
                )
            
            # RA 클릭 뉴런 사운드도 재질별로 생성 (NEW!)
            ra_click_hz = int(snd_cfg['ra_click_hz'] * mat_props['f'])  # 재질별 주파수 계수 적용
            ra_click_cache_key = f"ra_click_{mat_key}_{ra_click_hz}"
            
            if 'type' in mat_props:
                # 클릭은 짧고 강하게 - 진폭을 1.2배로 증가, 지속시간은 그대로
                click_amp = snd_cfg['ra_click_amp'] * 1.2
                material_params = {k: v for k, v in mat_props.items() if k not in ['r', 'f', 'type']}
                self.sound_cache[ra_click_cache_key] = self.haptic_renderer.create_material_sound(
                    mat_props['type'], ra_click_hz, snd_cfg['ra_click_ms'], click_amp, 
                    fade_out_ms=5, **material_params  # 클릭은 더 빠른 페이드아웃
                )
                print(f"Created {mat_props['type']} RA_Click sound for {mat_key}: {ra_click_hz}Hz")
            else:
                # 기본 사인파 사용
                self.sound_cache[ra_click_cache_key] = self.haptic_renderer.create_sound_object(
                    ra_click_hz, snd_cfg['ra_click_ms'], snd_cfg['ra_click_amp'], fade_out_ms=5
                )
        
        # 현재 재질의 사운드들 설정
        self.ra_motion_snd = self.sound_cache[f"ra_motion_{self.curr_mat_key}_{int(snd_cfg['ra_motion_base_hz'] * self.materials[self.curr_mat_key]['f'])}"]
        self.ra_click_snd = self.sound_cache[f"ra_click_{self.curr_mat_key}_{int(snd_cfg['ra_click_hz'] * self.materials[self.curr_mat_key]['f'])}"]

    def _update_ra_motion_sound(self): 
        """재질 변경 시 RA 움직임 뉴런과 RA 클릭 뉴런 사운드 모두 업데이트"""
        mat_props=self.materials[self.curr_mat_key]
        snd_cfg = self.config['sound']
        
        # RA 움직임 사운드 업데이트
        ra_motion_hz=int(snd_cfg['ra_motion_base_hz']*mat_props['f'])
        ra_motion_cache_key = f"ra_motion_{self.curr_mat_key}_{ra_motion_hz}"
        
        if ra_motion_cache_key in self.sound_cache:
            self.ra_motion_snd = self.sound_cache[ra_motion_cache_key]
        else:
            # 재질별 특화 파형 사용
            if 'type' in mat_props:
                material_params = {k: v for k, v in mat_props.items() if k not in ['r', 'f', 'type']}
                self.ra_motion_snd = self.haptic_renderer.create_material_sound(
                    mat_props['type'], ra_motion_hz, snd_cfg['ra_motion_ms'], snd_cfg['ra_motion_base_amp'], 
                    fade_out_ms=10, **material_params
                )
                print(f"Updated to {mat_props['type']} RA_Motion sound: {ra_motion_hz}Hz")
            else:
                self.ra_motion_snd = self.haptic_renderer.create_sound_object(ra_motion_hz, snd_cfg['ra_motion_ms'], snd_cfg['ra_motion_base_amp'], fade_out_ms=10)
        
        # RA 클릭 사운드 업데이트 (NEW!)
        ra_click_hz=int(snd_cfg['ra_click_hz']*mat_props['f'])
        ra_click_cache_key = f"ra_click_{self.curr_mat_key}_{ra_click_hz}"
        
        if ra_click_cache_key in self.sound_cache:
            self.ra_click_snd = self.sound_cache[ra_click_cache_key]
        else:
            # 재질별 특화 파형 사용
            if 'type' in mat_props:
                click_amp = snd_cfg['ra_click_amp'] * 1.2
                material_params = {k: v for k, v in mat_props.items() if k not in ['r', 'f', 'type']}
                self.ra_click_snd = self.haptic_renderer.create_material_sound(
                    mat_props['type'], ra_click_hz, snd_cfg['ra_click_ms'], click_amp, 
                    fade_out_ms=5, **material_params
                )
                print(f"Updated to {mat_props['type']} RA_Click sound: {ra_click_hz}Hz")
            else:
                self.ra_click_snd = self.haptic_renderer.create_sound_object(ra_click_hz, snd_cfg['ra_click_ms'], snd_cfg['ra_click_amp'], fade_out_ms=5)
        
        self.update_stat_lbl()

    def keyPressEvent(self,e:QKeyEvent):
        k=e.key()
        if Qt.Key.Key_1<=k<=Qt.Key.Key_7:
            if k-Qt.Key.Key_1 < len(self.mat_keys):
                self.curr_mat_key=self.mat_keys[k-Qt.Key.Key_1]
                self.mat_roughness=self.materials[self.curr_mat_key]['r']; self._update_ra_motion_sound()
        elif k == Qt.Key.Key_Space:
            if self.timer.isActive():
                self.timer.stop()
                self.info_lbl.setText("PAUSED - Press SPACE to resume")
            else:
                self.timer.start(int(self.neuron_dt_ms))
                self.info_lbl.setText("Click/SA+RA_Click, Move/RA_Motion (1-7 Materials)")
        elif k == Qt.Key.Key_R:
            self._reset_simulation()
        elif k == Qt.Key.Key_Plus or k == Qt.Key.Key_Equal:
            self._adjust_volume(0.1)
        elif k == Qt.Key.Key_Minus:
            self._adjust_volume(-0.1)
        elif k == Qt.Key.Key_Escape:
            self.close()
        else: 
            super().keyPressEvent(e)

    def _reset_simulation(self):
        self.spike_encoder = SpikeEncoder(
            sa_params=self.config['sa_neuron'],
            ra_params=self.config['ra_neuron'],
            ra_click_params=self.config['ra_click_neuron'],
            neuron_dt_ms=self.config['neuron_dt_ms'],
            input_config=self.config['input_current']
        )
        
        v_init_sa = self.config['sa_neuron']['v_init']
        v_init_ra_motion = self.config['ra_neuron']['v_init']
        v_init_ra_click = self.config['ra_click_neuron']['v_init']
        
        self.sa_v_hist.clear()
        self.sa_u_hist.clear()
        self.ra_motion_v_hist.clear()
        self.ra_motion_u_hist.clear()
        self.ra_click_v_hist.clear()
        self.ra_click_u_hist.clear()
        
        for _ in range(self.plot_hist_sz):
            self.sa_v_hist.append(v_init_sa)
            self.sa_u_hist.append(0.0)
            self.ra_motion_v_hist.append(v_init_ra_motion)
            self.ra_motion_u_hist.append(0.0)
            self.ra_click_v_hist.append(v_init_ra_click)
            self.ra_click_u_hist.append(0.0)
        
        self.sa_spike_idxs.clear()
        self.ra_motion_spike_idxs.clear()
        self.ra_click_spike_idxs.clear()
        
        self.m_pressed = False
        self.m_spd = 0.0
        self.spd_hist.clear()
        self.avg_m_spd = 0.0
        
        self.update_stat_lbl()
        print("Simulation reset!")

    def _adjust_volume(self, delta):
        """모든 뉴런 사운드의 볼륨을 동시에 조절"""
        self.config['sound']['sa_sound_volume'] = max(0.0, min(1.0, 
            self.config['sound']['sa_sound_volume'] + delta))
        
        self.config['sound']['ra_motion_max_vol_scl'] = max(0.0, min(1.0,
            self.config['sound']['ra_motion_max_vol_scl'] + delta))
            
        self.config['sound']['ra_click_volume'] = max(0.0, min(1.0,
            self.config['sound']['ra_click_volume'] + delta))
        
        vol = self.config['sound']['sa_sound_volume']
        print(f"Volume adjusted: SA={vol:.1f}, RA_Motion={self.config['sound']['ra_motion_max_vol_scl']:.1f}, RA_Click={self.config['sound']['ra_click_volume']:.1f}")
        
        self.update_stat_lbl()

    def update_stat_lbl(self):
        vol = self.config['sound']['sa_sound_volume']
        self.stat_lbl.setText(f"Mat:{self.curr_mat_key}(R:{self.mat_roughness:.1f})|Spd:{self.m_spd:.0f}|Vol:{vol:.1f}")

    def mousePressEvent(self,e:QPointF):
        self.m_pressed=True
        self.spike_encoder.update_sa_input(self.config['input_current']['click_mag'])
        p=e.position() if hasattr(e,'position') else QPointF(e.x(),e.y())
        self.last_m_pos=p; self.last_m_t=time.perf_counter(); self.m_spd=0.0; self.spd_hist.clear(); self.avg_m_spd=0.0
        self.update_stat_lbl()

    def mouseReleaseEvent(self,e:QPointF):
        self.m_pressed=False
        self.spike_encoder.update_sa_input(0.0)
        self.m_spd=0.0; self.update_stat_lbl()

    def mouseMoveEvent(self,e:QPointF):
        if self.m_pressed:
            t_now=time.perf_counter(); dt=t_now-self.last_m_t; p_now=e.position() if hasattr(e,'position') else QPointF(e.x(),e.y())
            if dt>Constants.MIN_MOUSE_DELTA_TIME:
                dist=np.sqrt((p_now.x()-self.last_m_pos.x())**2+(p_now.y()-self.last_m_pos.y())**2)
                self.m_spd=min(dist/dt,self.max_spd_clamp); self.spd_hist.append(self.m_spd)
                self.avg_m_spd=np.mean(self.spd_hist) if self.spd_hist else 0.0
                self.last_m_pos=p_now; self.last_m_t=t_now; self.update_stat_lbl()

    def update_plots(self):
        """3개 뉴런 그래프 업데이트 (SA, RA Motion, RA Click)"""
        # 기존 스파이크 라인들 제거
        for line in self.drawn_spike_lines: line.remove()
        self.drawn_spike_lines.clear()

        # === SA 뉴런 그래프 업데이트 ===
        self.sa_v_line.set_ydata(list(self.sa_v_hist)); self.sa_u_line.set_ydata(list(self.sa_u_hist))
        new_sa_spike_idxs=deque(maxlen=self.sa_spike_idxs.maxlen)
        for x_idx in self.sa_spike_idxs:
            if x_idx >= 0:
                self.drawn_spike_lines.append(self.ax_sa.axvline(x_idx,color='#e60026',ls='--',lw=1.5))
                shifted_idx = x_idx - self.plot_upd_interval
                if shifted_idx >= 0: 
                    new_sa_spike_idxs.append(shifted_idx)
        self.sa_spike_idxs = new_sa_spike_idxs

        # === RA 움직임 뉴런 그래프 업데이트 ===
        self.ra_motion_v_line.set_ydata(list(self.ra_motion_v_hist)); self.ra_motion_u_line.set_ydata(list(self.ra_motion_u_hist))
        new_ra_motion_spike_idxs=deque(maxlen=self.ra_motion_spike_idxs.maxlen)
        for x_idx in self.ra_motion_spike_idxs:
            if x_idx >= 0:
                self.drawn_spike_lines.append(self.ax_ra_motion.axvline(x_idx,color='#e60026',ls='--',lw=1.5))
                shifted_idx = x_idx - self.plot_upd_interval
                if shifted_idx >= 0:
                    new_ra_motion_spike_idxs.append(shifted_idx)
        self.ra_motion_spike_idxs = new_ra_motion_spike_idxs
        
        # === RA 클릭 뉴런 그래프 업데이트 ===
        self.ra_click_v_line.set_ydata(list(self.ra_click_v_hist)); self.ra_click_u_line.set_ydata(list(self.ra_click_u_hist))
        new_ra_click_spike_idxs=deque(maxlen=self.ra_click_spike_idxs.maxlen)
        for x_idx in self.ra_click_spike_idxs:
            if x_idx >= 0:
                self.drawn_spike_lines.append(self.ax_ra_click.axvline(x_idx,color='#e60026',ls='--',lw=1.5))
                shifted_idx = x_idx - self.plot_upd_interval
                if shifted_idx >= 0:
                    new_ra_click_spike_idxs.append(shifted_idx)
        self.ra_click_spike_idxs = new_ra_click_spike_idxs
        
        self.plot_canvas.draw()

    def update_neuron(self):
        """
        뉴런 시뮬레이션의 핵심 업데이트 함수 (1ms마다 호출)
        
        처리 과정:
        1. 마우스 속도 상태 확인 및 업데이트
        2. SpikeEncoder를 통한 뉴런 시뮬레이션 실행
        3. 뉴런 상태 데이터 히스토리에 추가
        4. 스파이크 발생 시 오디오 피드백 재생
        5. 주기적으로 그래프 업데이트
        
        데이터 흐름:
        마우스 상태 → SpikeEncoder → 뉴런 상태 → 그래프 히스토리 + 오디오 출력
        """
        current_time = time.perf_counter()
        elapsed_time = (current_time - self.last_neuron_update_time) * 1000
        self.last_neuron_update_time = current_time

        # 마우스 정지 감지 (일정 시간 이상 움직임이 없으면 속도를 0으로 설정)
        if (time.perf_counter()-self.last_m_t)>self.config['mouse']['m_stop_thresh'] and self.m_pressed:
            self.m_spd=0.0;
            self.update_stat_lbl()
        
        # === 3개 뉴런 시뮬레이션 실행 ===
        # SpikeEncoder를 통해 마우스 입력을 뉴런 자극으로 변환하고 시뮬레이션 실행
        sa_f, ra_motion_f, ra_click_f, sa_vu, ra_motion_vu, ra_click_vu = self.spike_encoder.step(
            mouse_speed=self.m_spd,              # 현재 마우스 속도
            avg_mouse_speed=self.avg_m_spd,      # 평균 마우스 속도
            material_roughness=self.mat_roughness, # 현재 선택된 재질의 거칠기
            mouse_pressed=self.m_pressed         # 마우스 클릭 상태
        )

        # === 뉴런 상태 데이터 히스토리 업데이트 ===
        # 실시간 그래프 표시를 위해 최신 뉴런 상태를 히스토리에 추가
        self.sa_v_hist.append(sa_vu[0]); self.sa_u_hist.append(sa_vu[1])  # SA 뉴런 (v, u)
        self.ra_motion_v_hist.append(ra_motion_vu[0]); self.ra_motion_u_hist.append(ra_motion_vu[1])  # RA 움직임 뉴런 (v, u)
        self.ra_click_v_hist.append(ra_click_vu[0]); self.ra_click_u_hist.append(ra_click_vu[1])  # RA 클릭 뉴런 (v, u)

        # === SA 뉴런 스파이크 처리 ===
        if sa_f:  # SA 뉴런이 스파이크를 발생시킨 경우
            # 그래프에 스파이크 마커 추가 (맨 오른쪽 위치)
            self.sa_spike_idxs.append(self.plot_hist_sz-1)
            # SA 뉴런 전용 사운드 재생 (채널 0, 설정된 볼륨)
            self.audio_player.play_sound(self.sa_snd, channel_id=0, volume=self.config['sound'].get('sa_sound_volume', 1.0))

        # === RA 움직임 뉴런 스파이크 처리 ===
        if ra_motion_f:  # RA 움직임 뉴런이 스파이크를 발생시킨 경우
            # 그래프에 스파이크 마커 추가
            self.ra_motion_spike_idxs.append(self.plot_hist_sz-1) 
            if self.ra_motion_snd:
                # 마우스 속도에 따른 동적 볼륨 계산
                s=self.m_spd  # 현재 마우스 속도
                snd_cfg = self.config['sound']
                vol_scl=snd_cfg['ra_motion_min_vol_scl']  # 기본 최소 볼륨
                
                # 속도 구간에 따른 볼륨 스케일링
                if s<=snd_cfg['ra_motion_vol_min_spd']: 
                    vol_scl=snd_cfg['ra_motion_min_vol_scl']  # 낮은 속도: 최소 볼륨
                elif s>=snd_cfg['ra_motion_vol_max_spd']: 
                    vol_scl=snd_cfg['ra_motion_max_vol_scl']  # 높은 속도: 최대 볼륨
                else:
                    # 중간 속도: 선형 보간으로 볼륨 계산
                    den=snd_cfg['ra_motion_vol_max_spd']-snd_cfg['ra_motion_vol_min_spd']
                    if den>0: 
                        vol_scl=snd_cfg['ra_motion_min_vol_scl']+((s-snd_cfg['ra_motion_vol_min_spd'])/den)*(snd_cfg['ra_motion_max_vol_scl']-snd_cfg['ra_motion_min_vol_scl'])
                
                # RA 움직임 뉴런 전용 사운드 재생 (채널 1, 계산된 볼륨)
                self.audio_player.play_sound(self.ra_motion_snd, channel_id=1, volume=np.clip(vol_scl,0.0,1.0))

        # === RA 클릭 뉴런 스파이크 처리 ===
        if ra_click_f:  # RA 클릭 뉴런이 스파이크를 발생시킨 경우
            # 그래프에 스파이크 마커 추가
            self.ra_click_spike_idxs.append(self.plot_hist_sz-1)
            # RA 클릭 뉴런 전용 사운드 재생 (채널 2, 고정 볼륨)
            self.audio_player.play_sound(self.ra_click_snd, channel_id=2, volume=self.config['sound'].get('ra_click_volume', 1.0))

        # === 그래프 업데이트 ===
        # 매 프레임마다 그래프를 업데이트하면 성능 저하가 발생하므로 주기적으로만 업데이트
        self.plot_upd_cnt+=1
        if self.plot_upd_cnt>=self.plot_upd_interval:  # 설정된 간격마다 업데이트 (기본: 5프레임)
            self.update_plots()  # 실제 그래프 화면 갱신
            self.plot_upd_cnt=0

    def closeEvent(self,e): 
        self.audio_player.quit()
        super().closeEvent(e)

    def _get_validated_config(self):
        """
        햅틱 피드백 시스템의 모든 설정값을 정의하는 함수
        뉴런 모델, 사운드, 재질 등 시스템 전체 파라미터를 포함
        """
        config = {
            # === 시뮬레이션 기본 설정 ===
            'neuron_dt_ms': 1.0,        # 뉴런 시뮬레이션 시간 간격 (밀리초) - 1ms마다 뉴런 상태 업데이트
            'plot_hist_sz': 500,        # 그래프에 표시할 데이터 포인트 수 - 500개 = 2.5초 분량 (500ms * 5업데이트간격)
            
            # === SA 뉴런 (압력 감지) 파라미터 ===
            # Izhikevich 뉴런 모델의 수학적 파라미터들
            'sa_neuron': {
                'a': 0.05,              # 회복변수(u)의 회복 속도 - 반응속도 향상을 위해 0.03->0.05로 증가
                'b': 0.25,              # 막전위(v)와 회복변수(u) 간의 결합 강도 - 뉴런의 민감도 조절
                'c': -65.0,             # 스파이크 후 리셋 전압 (mV) - 스파이크 후 막전위가 이 값으로 리셋
                'd': 6.0,               # 스파이크 후 회복변수(u) 증가량 - 스파이크 후 일시적 비활성화 정도
                'v_init': -70.0,        # 초기 막전위 (mV) - 뉴런의 휴지 전위
                'init_a': 0.05,         # SA 뉴런의 초기 a값 (적응을 위해 동적으로 변경됨)
            },
            
            # === RA 움직임 뉴런 (움직임/진동 감지) 파라미터 ===
            'ra_neuron': {
                'base_a': 0.4,         # 기본 a값 - 반응속도 향상을 위해 0.3->0.4로 증가
                'base_b': 0.25,         # 기본 b값 - 막전위 민감도
                'base_c': -65.0,        # 스파이크 후 리셋 전압 (mV)
                'base_d': 1.5,          # 스파이크 후 회복변수 증가량 - SA보다 작아서 빠른 반복 스파이크 가능
                'v_init': -65.0,        # 초기 막전위 (mV) - SA보다 높아서 더 민감
            },
            
            # === RA 클릭 뉴런 (클릭 순간 감지) 파라미터 ===
            'ra_click_neuron': {
                'a': 0.3,               # 매우 빠른 회복 - 반응속도 향상을 위해 0.2->0.3으로 증가
                'b': 0.25,              # 막전위 민감도
                'c': -65.0,             # 스파이크 후 리셋 전압 (mV)
                'd': 6.0,               # 스파이크 후 회복변수 증가량
                'v_init': -65.0,        # 초기 막전위 (mV)
            },
            
            # === 입력 전류 설정 (마우스 → 뉴런 변환) ===
            'input_current': {
                'click_mag': 12.0,              # 마우스 클릭 시 SA 뉴런에 가해지는 기본 전류 강도
                'ra_click_scl_chg': 25.0,       # RA 클릭 뉴런 전류 스케일링 - 클릭 변화량에 곱해지는 계수
                'RA_CLICK_SUSTAIN_DURATION': 3, # RA 클릭 뉴런 자극 지속 프레임 수 (3프레임 = 3ms)
                'ra_motion_scl_spd_dev': 0.02,  # RA 움직임 뉴런 전류 스케일링 - 마우스 속도*거칠기에 곱해지는 계수
                'ra_min_spd_for_input': 1.0,    # RA 움직임 뉴런 활성화 최소 마우스 속도 (픽셀/ms)
                'ra_click_clip_min': -40.0,     # RA 클릭 뉴런 입력 전류 최소값 (클리핑)
                'ra_click_clip_max': 40.0,      # RA 클릭 뉴런 입력 전류 최대값 (클리핑)
                'ra_motion_clip_min': -30.0,    # RA 움직임 뉴런 입력 전류 최소값 (클리핑)
                'ra_motion_clip_max': 30.0,     # RA 움직임 뉴런 입력 전류 최대값 (클리핑)
            },
            
            # === 사운드 설정 (뉴런 → 오디오 변환) ===
            'sound': {
                # SA 뉴런 사운드 (압력 피드백)
                'sa_hz': 25,                    # SA 뉴런 기본 주파수 (Hz) - 더 낮은 주파수로 부드러운 압력감
                'sa_ms': 120,                   # SA 뉴런 사운드 지속시간 (ms) - 길게 지속되는 압력감
                'sa_amp': 0.25,                 # SA 뉴런 사운드 진폭 (0.15->0.25로 증가)
                'sa_sound_volume': 0.9,         # SA 뉴런 최종 볼륨 (1.0->0.9로 약간 줄여서 균형)
                
                # RA 움직임 뉴런 사운드 (움직임 피드백)
                'ra_motion_base_hz': 35,        # RA 움직임 뉴런 기본 주파수 (45->35Hz로 낮춤)
                'ra_motion_ms': 90,             # RA 움직임 뉴런 사운드 지속시간 (100->90ms로 약간 단축)
                'ra_motion_base_amp': 0.6,      # RA 움직임 뉴런 기본 진폭 (0.4->0.6로 증가)
                'ra_motion_vol_min_spd': 100.0, # RA 움직임 뉴런 최소 볼륨 적용 마우스 속도
                'ra_motion_vol_max_spd': 5000.0,# RA 움직임 뉴런 최대 볼륨 적용 마우스 속도
                'ra_motion_min_vol_scl': 0.5,   # RA 움직임 뉴런 최소 볼륨 스케일 (0.4->0.5로 증가)
                'ra_motion_max_vol_scl': 1.0,   # RA 움직임 뉴런 최대 볼륨 스케일 (0.8->1.0로 증가)
                
                # RA 클릭 뉴런 사운드 (클릭 순간 피드백)
                'ra_click_hz': 50,              # RA 클릭 뉴런 주파수 (60->50Hz로 낮춤)
                'ra_click_ms': 70,              # RA 클릭 뉴런 사운드 지속시간 (80->70ms로 단축)
                'ra_click_amp': 0.7,            # RA 클릭 뉴런 진폭 (0.6->0.7로 증가)
                'ra_click_volume': 0.9,         # RA 클릭 뉴런 최종 볼륨 (1.0->0.9)
            },
            
            # === 마우스 입력 설정 ===
            'mouse': {
                'max_spd_clamp': 100000.0,      # 마우스 속도 최대 제한값 (픽셀/초) - 너무 빠른 움직임 제한
                'm_stop_thresh': 0.02,          # 마우스 정지 감지 임계값 (초) - 이 시간 이상 움직임 없으면 정지로 판단
            },
            
            # === 그래프 표시 설정 ===
            'plot': {
                'update_interval': 5,           # 그래프 업데이트 간격 (프레임) - 원래대로 5프레임마다 그래프 갱신
            },
            
            # === 재질별 설정 (키보드 1-7로 선택) ===
            'materials': {
                # 각 재질마다 r(거칠기), f(주파수계수), type(파형타입), 특성파라미터를 정의
                'Glass': {          # 유리 (키보드 1)
                    'r': 0.5,           # 거칠기 - RA 움직임 뉴런 민감도 (낮음: 부드러운 표면)
                    'f': 1.3,           # 주파수 계수 - 기본 주파수(45Hz)에 곱해져서 58.5Hz
                    'type': 'glass',    # 파형 타입 - 유리 특화 파형 사용
                    'brightness': 2.5   # 유리 특성 - 배음 밝기 조절 (높을수록 날카로운 소리)
                },
                'Metal': {          # 메탈 (키보드 2)
                    'r': 1.0,           # 거칠기 - 중간 정도의 표면 거칠기
                    'f': 1.1,           # 주파수 계수 - 49.5Hz
                    'type': 'metal',    # 파형 타입 - 메탈 특화 파형 사용
                    'resonance': 1.8    # 메탈 특성 - 공명 강도 (높을수록 울림이 강함)
                },
                'Wood': {           # 나무 (키보드 3)
                    'r': 0.8,           # 거칠기 - 적당한 표면 거칠기
                    'f': 0.9,           # 주파수 계수 - 40.5Hz (낮은 주파수로 따뜻한 느낌)
                    'type': 'wood',     # 파형 타입 - 나무 특화 파형 사용
                    'warmth': 1.2       # 나무 특성 - 따뜻함 정도 (저주파 성분 강화)
                },
                'Plastic': {        # 플라스틱 (키보드 4)
                    'r': 0.4,           # 거칠기 - 매끄러운 표면
                    'f': 1.0,           # 주파수 계수 - 45Hz (기본값)
                    'type': 'plastic',  # 파형 타입 - 플라스틱 특화 파형 사용
                    'hardness': 1.1     # 플라스틱 특성 - 경도 (인공적 느낌 조절)
                },
                'Fabric': {         # 직물 (키보드 5)
                    'r': 0.2,           # 거칠기 - 매우 부드러운 표면
                    'f': 0.7,           # 주파수 계수 - 31.5Hz (낮은 주파수)
                    'type': 'fabric',   # 파형 타입 - 직물 특화 파형 사용
                    'softness': 1.5     # 직물 특성 - 부드러움 정도 (노이즈 성분 조절)
                },
                'Ceramic': {        # 세라믹 (키보드 6)
                    'r': 0.6,           # 거칠기 - 중간 정도의 표면 거칠기
                    'f': 1.2,           # 주파수 계수 - 54Hz
                    'type': 'ceramic',  # 파형 타입 - 세라믹 특화 파형 사용
                    'brittleness': 1.4  # 세라믹 특성 - 취성 정도 (깨지기 쉬운 재질감)
                },
                'Rubber': {         # 고무 (키보드 7)
                    'r': 0.3,           # 거칠기 - 부드러운 표면
                    'f': 0.8,           # 주파수 계수 - 36Hz (낮은 주파수)
                    'type': 'rubber',   # 파형 타입 - 고무 특화 파형 사용
                    'elasticity': 1.3   # 고무 특성 - 탄성 정도 (탄성적 변조 효과)
                }
            }
        }
        
        self._validate_config(config)
        return config

    def _validate_config(self, config):
        """새로운 3개 뉴런 설정 구조 검증"""
        assert config['neuron_dt_ms'] > 0, "neuron_dt_ms must be positive"
        assert config['plot_hist_sz'] > 0, "plot_hist_sz must be positive"
        
        # SA 뉴런 파라미터 검증
        sa_cfg = config['sa_neuron']
        assert 'a' in sa_cfg and 'b' in sa_cfg and 'c' in sa_cfg and 'd' in sa_cfg, "SA neuron missing parameters"
        
        # RA 움직임 뉴런 파라미터 검증
        ra_cfg = config['ra_neuron']
        assert 'base_a' in ra_cfg and 'base_b' in ra_cfg and 'base_c' in ra_cfg and 'base_d' in ra_cfg, "RA motion neuron missing parameters"
        
        # RA 클릭 뉴런 파라미터 검증  
        ra_click_cfg = config['ra_click_neuron']
        assert 'a' in ra_click_cfg and 'b' in ra_click_cfg and 'c' in ra_click_cfg and 'd' in ra_click_cfg, "RA click neuron missing parameters"
        
        # 사운드 설정 검증
        sound_cfg = config['sound']
        assert 0 < sound_cfg['sa_hz'] < 22050, "sa_hz must be in valid audio range"
        assert 0 < sound_cfg['ra_motion_base_hz'] < 22050, "ra_motion_base_hz must be in valid audio range"
        assert 0 < sound_cfg['ra_click_hz'] < 22050, "ra_click_hz must be in valid audio range"
        assert 0 <= sound_cfg['sa_sound_volume'] <= 1.0, "sa_sound_volume must be 0-1"
        assert 0 <= sound_cfg['ra_click_volume'] <= 1.0, "ra_click_volume must be 0-1"
        
        # 재질 설정 검증
        for mat_name, mat_props in config['materials'].items():
            assert 'r' in mat_props and 'f' in mat_props, f"Material {mat_name} missing properties"
            assert mat_props['r'] > 0, f"Material {mat_name} roughness must be positive"
            assert mat_props['f'] > 0, f"Material {mat_name} frequency factor must be positive"
            
            # 재질 타입이 있는 경우 유효성 검증
            if 'type' in mat_props:
                valid_types = ['glass', 'metal', 'wood', 'plastic', 'fabric', 'ceramic', 'rubber']
                assert mat_props['type'] in valid_types, f"Material {mat_name} has invalid type: {mat_props['type']}"
        
        print("Configuration validated successfully!")

if __name__=='__main__': 
    app=QApplication(sys.argv);w=TestWindow();w.show();sys.exit(app.exec()) 