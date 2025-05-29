import sys
import numpy as np
import pygame # Pygame 임포트
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton # QVBoxLayout, QWidget, QPushButton 추가
from PyQt6.QtCore import QTimer, Qt, QPointF # QPointF 추가
from PyQt6.QtGui import QKeyEvent # QKeyEvent 추가
import time # time 모듈 추가 for 속도 계산
from collections import deque # deque 추가

# Matplotlib 백엔드 설정 및 임포트 순서 조정
import matplotlib
matplotlib.use('QtAgg') # PyQt6 또는 PyQt5와 호환되는 일반 Qt 백엔드 사용 명시

# macOS 스타일과 유사하게 Matplotlib 스타일 업데이트 (다크 모드 테마로 변경)
matplotlib.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Helvetica Neue', 'Arial', 'DejaVu Sans'],
    'axes.titlesize': 14,
    'axes.labelsize': 11,
    'xtick.labelsize': 9, 
    'ytick.labelsize': 9,
    'legend.fontsize': 10,
    'figure.dpi': 100,
    'figure.facecolor': '#1c1c1e',  # 전체 그림 배경색 (다크)
    'axes.facecolor': '#1c1c1e',    # 축 배경색 (다크)
    'axes.edgecolor': '#a0a0a0',    # 축 테두리 색 (밝게)
    'axes.labelcolor': '#e0e0e0',   # 축 레이블 색 (밝게)
    'text.color': '#f0f0f0',        # 기본 텍스트 색 (밝게)
    'xtick.color': '#c0c0c0',       # x축 눈금 색 (밝게)
    'ytick.color': '#c0c0c0',       # y축 눈금 색 (밝게)
    'grid.color': '#505050',        # 그리드 색 (어두운 배경에 맞게)
    'grid.linestyle': '--',
    'grid.alpha': 0.7,
    'lines.linewidth': 1.8
})

# Matplotlib FigureCanvas 임포트 (QtAgg 백엔드에 맞는 FigureCanvas 사용 시도)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from matplotlib.figure import Figure
from izhikevich_neuron import IzhikevichNeuron # 분리된 파일에서 클래스 임포트
from audio_player import AudioPlayer # AudioPlayer 클래스 임포트
from haptic_renderer import HapticRenderer # HapticRenderer 임포트
from spike_encoder import SpikeEncoder # SpikeEncoder 임포트

# Izhikevich 뉴런 모델: 2차원 미분 방정식으로 뉴런의 발화 패턴을 효율적으로 모델링합니다.
# class IzhikevichNeuron: (이하 클래스 정의 전체 삭제)
#     def __init__(self, a, b, c, d, v_init=-70.0):
# ... (클래스 내용 모두 삭제)
#         return fired

# --- Test Window ---
class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Izhikevich Haptic Test") # 간결한 제목
        self.setGeometry(50,50,1200,1200)

        self.config = {
            'neuron_dt_ms': 1.0, # 뉴런 시뮬레이션 시간 스텝 (ms)
            'plot_hist_sz': 500, # 그래프에 표시할 시간 히스토리 크기 (스텝 수)
            'sa_neuron': { # SA 뉴런 파라미터
                'a': 0.02, # 회복 변수 u의 시간 스케일 (작을수록 느린 회복/적응)
                'b': 0.2,  # 회복 변수 u가 막 전위 v에 미치는 영향 (클수록 v에 강하게 연결)
                'c': -65.0,# 발화 후 막 전위 재설정 값 (mV)
                'd': 8.0,  # 발화 후 회복 변수 u 재설정 증가 값 (클수록 적응 심화)
                'v_init': -70.0, # 초기 막 전위 (mV)
                'init_a': 0.02, # 장기 적응을 위한 초기 a값 (현재 코드에서 사용되지 않을 수 있음)
            },
            'ra_neuron': { # RA 뉴런 파라미터 (기본)
                'base_a': 0.1, # RA 뉴런의 기본 a값 (SA보다 빠름)
                'base_b': 0.2, # RA 뉴런의 기본 b값
                'base_c': -65.0, # RA 뉴런 발화 후 c값
                'base_d': 2.0,  # RA 뉴런 기본 d값 (SA보다 적응 덜 심함)
                'v_init': -65.0, # RA 뉴런 초기 v값 (mV)
                'click_d_burst': 20.0, # 클릭/해제 시 RA d값 증가량 (순간적 발화 유도)
            },
            'input_current': { # 입력 전류 설정
                'click_mag': 12.0, # 마우스 클릭/홀드 시 SA 뉴런에 가해지는 입력 전류 크기
                'ra_scl_chg': 20.0, # 마우스 속도 변화가 RA 입력에 미치는 배율
                'ra_scl_spd_dev': 0.02, # 평균 속도 편차가 RA 입력에 미치는 배율 (현재 코드에서 직접 사용되지 않을 수 있음)
                'ra_clip_min': -30.0, # RA 입력 전류 최소 클리핑 값
                'ra_clip_max': 30.0,  # RA 입력 전류 최대 클리핑 값
                'RA_SUSTAIN_DURATION': 5, # RA 지속 입력 스텝 수 (현재 코드에서 사용되지 않음)
                'ra_min_spd_for_input': 1.0, # RA 입력이 활성화되는 최소 속도 (현재 코드에서 사용되지 않음)
            },
            'sound': { # 사운드 설정
                'sa_hz': 50, # SA 사운드 주파수 (Hz)
                'sa_ms': 120, # SA 사운드 길이 (ms)
                'sa_amp': 0.15, # SA 사운드 기본 진폭
                'sa_sound_volume': 1.0, # SA 사운드 재생 볼륨 (0.0 ~ 1.0)
                'ra_base_hz': 80, # RA 사운드 기본 주파수 (Hz) - 재질에 따라 스케일됨
                'ra_ms': 100,  # RA 사운드 길이 (ms)
                'ra_base_amp': 0.6, # RA 사운드 기본 진폭 - 속도에 따라 스케일됨
                'ra_vol_min_spd': 100.0, # RA 볼륨 조절 최소 속도 임계값
                'ra_vol_max_spd': 5000.0,# RA 볼륨 조절 최대 속도
                'ra_min_vol_scl': 0.6, # RA 최소 볼륨 스케일 (최소 속도 이하)
                'ra_max_vol_scl': 1, # RA 최대 볼륨 스케일 (최대 속도 이상)
            },
            'mouse': { # 마우스 입력 설정
                'max_spd_clamp': 100000.0, # 계산된 속도의 최대값 제한
                'm_stop_thresh': 0.05, # 마우스 정지 판단 시간 임계값 (s)
            },
            'plot': { # 그래프 설정
                'update_interval': 5, # 그래프 업데이트 주기 (스텝 수)
            },
            'materials': { # 재질 설정 (거칠기 및 주파수 배율)
                'S': {'r': 0.3, 'f': 1.0}, # Smooth (부드러움): 거칠기 0.3, 주파수 배율 1.0
                'M': {'r': 0.7, 'f': 1.1}, # Medium (중간): 거칠기 0.7, 주파수 배율 1.1
                'R': {'r': 1.2, 'f': 1.2}  # Rough (거침): 거칠기 1.2, 주파수 배율 1.2
            }
        }
        
        self.neuron_dt_ms = self.config['neuron_dt_ms'] # 타이머 등에서 직접 사용 (밀리초 단위)

        main_w=QWidget(); layout=QVBoxLayout(main_w)
        # main_w 배경색 설정 (스페이스그레이/실버 느낌)
        main_w.setStyleSheet("background-color: #48484a;") # 어두운 회색 (스페이스그레이 느낌)
        
        self.info_lbl=QLabel("Click/SA, Move/RA (1-3 Mat)",self) # 축약된 라벨
        fnt=self.info_lbl.font();fnt.setPointSize(16);self.info_lbl.setFont(fnt)
        # 라벨 중앙 정렬
        self.info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_lbl)
        self.stat_lbl=QLabel("Mat:S(R:0.3)|Spd:0",self) # 축약된 상태 라벨
        fnt=self.stat_lbl.font();fnt.setPointSize(14);self.stat_lbl.setFont(fnt)
        # 라벨 중앙 정렬
        self.stat_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stat_lbl)

        self.plot_hist_sz=self.config['plot_hist_sz']
        v_init_val_sa = self.config['sa_neuron']['v_init']
        sa_params = self.config['sa_neuron']
        u_init_sa = IzhikevichNeuron(sa_params['a'], sa_params['b'], sa_params['c'], sa_params['d'], v_init=v_init_val_sa).u
        self.sa_v_hist=deque([v_init_val_sa]*self.plot_hist_sz, maxlen=self.plot_hist_sz)
        self.sa_u_hist=deque([u_init_sa]*self.plot_hist_sz, maxlen=self.plot_hist_sz)
        
        v_init_val_ra = self.config['ra_neuron']['v_init']
        ra_params_base = self.config['ra_neuron']
        u_init_ra = IzhikevichNeuron(ra_params_base['base_a'], ra_params_base['base_b'], ra_params_base['base_c'], ra_params_base['base_d'], v_init=v_init_val_ra).u
        self.ra_v_hist=deque([v_init_val_ra]*self.plot_hist_sz, maxlen=self.plot_hist_sz)
        self.ra_u_hist=deque([u_init_ra]*self.plot_hist_sz, maxlen=self.plot_hist_sz)
        self.x_data=np.arange(self.plot_hist_sz)

        self.fig=Figure(figsize=(7,5)); self.ax_sa,self.ax_ra=self.fig.subplots(2,1)
        self.sa_v_line,=self.ax_sa.plot(self.x_data,list(self.sa_v_hist),lw=1.8,label='SA_v', color='#007aff') # iOS Blue
        self.sa_u_line,=self.ax_sa.plot(self.x_data,list(self.sa_u_hist),lw=1.8,label='SA_u', color='#ff9500') # iOS Orange
        self.ax_sa.set_title('SA Neuron');

        # SA 그래프 y축 라벨을 'V (mV), U'로 변경 및 글자 크기 설정
        self.ax_sa.set_ylabel('V (mV), U', fontsize=12) # V는 mV, U는 단위 없음
        self.ax_sa.set_ylim(-90,40)

        self.ax_sa.set_xlim(0,self.plot_hist_sz-1);self.ax_sa.legend(loc='upper right', frameon=False);self.ax_sa.grid(True)
        self.ax_sa.spines['top'].set_visible(False); self.ax_sa.spines['right'].set_visible(False)

        # x축 눈금 위치 (원본 0-499 범위에 해당) 및 라벨 설정 (2500-0)
        tick_locs = np.linspace(0, self.plot_hist_sz - 1, 6) # 6개 눈금 위치 (0, 100, 200, 300, 400, 499)
        tick_labels = np.linspace(2500, 0, 6).astype(int) # 6개 라벨 (2500, 2000, 1500, 1000, 500, 0)

        self.ax_sa.set_xticks(tick_locs)
        self.ax_sa.set_xticklabels(tick_labels) # SA 그래프에도 동일한 눈금 라벨 적용

        self.ra_v_line,=self.ax_ra.plot(self.x_data,list(self.ra_v_hist),lw=1.8,label='RA_v', color='#007aff')
        self.ra_u_line,=self.ax_ra.plot(self.x_data,list(self.ra_u_hist),lw=1.8,label='RA_u', color='#ff9500')
        self.ax_ra.set_title('RA Neuron');

        # RA 그래프 y축 라벨을 'V (mV), U'로 변경 및 글자 크기 설정
        self.ax_ra.set_ylabel('V (mV), U', fontsize=12) # V는 mV, U는 단위 없음
        self.ax_ra.set_ylim(-90,40)

        # x축 라벨 및 글자 크기 설정
        self.ax_ra.set_xlabel('Time (ms)', fontsize=12) # 라벨을 Time (ms)으로 변경 및 글자 크기 키우기

        # x축 눈금 위치 (원본 0-499 범위에 해당) 및 라벨 설정 (2500-0)
        tick_locs = np.linspace(0, self.plot_hist_sz - 1, 6) # 6개 눈금 위치 (0, 100, 200, 300, 400, 499)
        tick_labels = np.linspace(2500, 0, 6).astype(int) # 6개 라벨 (2500, 2000, 1500, 1000, 500, 0)

        self.ax_sa.set_xticks(tick_locs)
        self.ax_sa.set_xticklabels(tick_labels) # SA 그래프에도 동일한 눈금 라벨 적용
        self.ax_ra.set_xticks(tick_locs)
        self.ax_ra.set_xticklabels(tick_labels)

        self.ax_ra.set_xlim(0,self.plot_hist_sz-1);self.ax_ra.legend(loc='upper right', frameon=False);self.ax_ra.grid(True)
        self.ax_ra.spines['top'].set_visible(False); self.ax_ra.spines['right'].set_visible(False)

        self.fig.tight_layout(pad=3.0);self.plot_canvas=FigureCanvas(self.fig)
        layout.addWidget(self.plot_canvas);self.setCentralWidget(main_w)

        # pygame.mixer.init(44100,-16,2,1024) # AudioPlayer가 처리
        self.audio_player = AudioPlayer() # AudioPlayer 객체 생성
        self.haptic_renderer = HapticRenderer() # HapticRenderer 객체 생성

        # SpikeEncoder 초기화
        self.spike_encoder = SpikeEncoder(
            sa_params=self.config['sa_neuron'],
            ra_params=self.config['ra_neuron'],
            neuron_dt_ms=self.config['neuron_dt_ms'],
            input_config=self.config['input_current']
        )

        snd_cfg = self.config['sound']
        # fade_out_ms 계산: 기존 로직은 sr * 0.01 (시간). ms 단위로 변환하면 snd_cfg['sa_ms'] * 0.01 아님. 샘플 수 기준.
        # self.haptic_renderer.sample_rate * 0.01 로 fade_out_samples를 계산했었음. 이를 ms로 바꾸려면 ( (sr*0.01) / sr ) * 1000 = 10ms
        # 좀 더 정확하게는, _create_sound의 fade_out 구간은 n_s의 1%가 아니라 고정된 0.01초 (10ms) 였던 것으로 보임.
        # (f_o=int(sr*0.01) 이므로). 따라서 fade_out_ms=10 으로 고정값 사용.
        self.sa_snd = self.haptic_renderer.create_sound_object(snd_cfg['sa_hz'], snd_cfg['sa_ms'], snd_cfg['sa_amp'], fade_out_ms=10)
        
        self.ra_base_hz=snd_cfg['ra_base_hz'] 
        self.ra_base_amp=snd_cfg['ra_base_amp'] 
        self.ra_snd = self.haptic_renderer.create_sound_object(self.ra_base_hz, snd_cfg['ra_ms'], self.ra_base_amp, fade_out_ms=10) # 초기화 시점
        
        self.ra_vol_min_spd=snd_cfg['ra_vol_min_spd']
        self.ra_vol_max_spd=snd_cfg['ra_vol_max_spd']
        self.ra_min_vol_scl=snd_cfg['ra_min_vol_scl']
        self.ra_max_vol_scl=snd_cfg['ra_max_vol_scl']

        sa_cfg = self.config['sa_neuron']
        self.sa_init_a = sa_cfg['init_a']
        self.sa_neuron=IzhikevichNeuron(sa_cfg['a'],sa_cfg['b'],sa_cfg['c'],sa_cfg['d'], v_init=sa_cfg['v_init'])
        
        ra_cfg = self.config['ra_neuron']
        self.ra_base_d = ra_cfg['base_d'] # for dynamic change
        self.ra_click_d_burst = ra_cfg['click_d_burst'] # for dynamic change
        self.ra_neuron=IzhikevichNeuron(ra_cfg['base_a'], ra_cfg['base_b'], ra_cfg['base_c'], ra_cfg['base_d'], v_init=ra_cfg['v_init'])

        curr_cfg = self.config['input_current']
        self.input_mag=0.0;self.prev_input_mag=0.0
        self.click_mag=curr_cfg['click_mag']
        self.ra_scl_chg=curr_cfg['ra_scl_chg']
        self.ra_scl_spd_dev=curr_cfg['ra_scl_spd_dev'] 
        self.ra_clip_min=curr_cfg['ra_clip_min']
        self.ra_clip_max=curr_cfg['ra_clip_max']

        self.RA_SUSTAIN_DURATION = curr_cfg['RA_SUSTAIN_DURATION']
        self.ra_sustained_click_input = 0.0
        self.ra_sustain_counter = 0

        self.m_pressed=False;self.last_m_pos=QPointF(0,0)
        self.last_m_t=time.perf_counter();self.m_spd=0.0
        mouse_cfg = self.config['mouse']
        self.max_spd_clamp=mouse_cfg['max_spd_clamp']
        self.m_stop_thresh=mouse_cfg['m_stop_thresh']
        self.spd_hist=deque(maxlen=10);self.avg_m_spd=0.0

        self.plot_upd_cnt=0
        # 그래프 업데이트 주기를 1 스텝으로 변경 (매 스텝 업데이트) -> 원래대로 (5 스텝) 복구
        self.plot_upd_interval=self.config['plot']['update_interval'] #1 #self.config['plot']['update_interval']
        self.sa_spike_idxs=deque(maxlen=self.plot_hist_sz)
        self.ra_spike_idxs=deque(maxlen=self.plot_hist_sz)
        self.drawn_spike_lines=[]

        self.materials = self.config['materials']
        self.mat_keys=list(self.materials.keys())
        self.curr_mat_key=self.mat_keys[0] 
        self.mat_roughness=self.materials[self.curr_mat_key]['r']
        self._update_ra_sound(); self.update_stat_lbl()
        self.timer=QTimer(self);self.timer.timeout.connect(self.update_neuron);self.timer.start(int(self.neuron_dt_ms))

        # update_neuron 호출 간격 측정을 위한 변수 초기화
        self.last_neuron_update_time = time.perf_counter()

    def _update_ra_sound(self): 
        mat_props=self.materials[self.curr_mat_key]
        snd_cfg = self.config['sound']
        new_hz=int(snd_cfg['ra_base_hz']*mat_props['f'])
        # self.ra_snd=self._create_sound(new_hz, snd_cfg['ra_ms'], snd_cfg['ra_base_amp']); self.update_stat_lbl()
        self.ra_snd = self.haptic_renderer.create_sound_object(new_hz, snd_cfg['ra_ms'], snd_cfg['ra_base_amp'], fade_out_ms=10); self.update_stat_lbl()

    def keyPressEvent(self,e:QKeyEvent):
        k=e.key()
        if Qt.Key.Key_1<=k<=Qt.Key.Key_3:
            self.curr_mat_key=self.mat_keys[k-Qt.Key.Key_1]
            self.mat_roughness=self.materials[self.curr_mat_key]['r']; self._update_ra_sound()
        else: super().keyPressEvent(e)

    def update_stat_lbl(self): # 상태 라벨 업데이트
        self.stat_lbl.setText(f"Mat:{self.curr_mat_key}(R:{self.mat_roughness:.1f})|Spd:{self.m_spd:.0f}")

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
            if dt>0.001:
                dist=np.sqrt((p_now.x()-self.last_m_pos.x())**2+(p_now.y()-self.last_m_pos.y())**2)
                self.m_spd=min(dist/dt,self.max_spd_clamp); self.spd_hist.append(self.m_spd)
                self.avg_m_spd=np.mean(self.spd_hist) if self.spd_hist else 0.0
                self.last_m_pos=p_now; self.last_m_t=t_now; self.update_stat_lbl()

    def update_plots(self):
        for line in self.drawn_spike_lines: line.remove() # 이전 스파이크 라인 제거
        self.drawn_spike_lines.clear()

        self.sa_v_line.set_ydata(list(self.sa_v_hist)); self.sa_u_line.set_ydata(list(self.sa_u_hist))
        new_sa_spike_idxs=deque(maxlen=self.sa_spike_idxs.maxlen)
        for x_idx in self.sa_spike_idxs:
            if x_idx >= 0:
                self.drawn_spike_lines.append(self.ax_sa.axvline(x_idx,color='#e60026',ls='--',lw=1.5)) # 스파이크 선 색상 변경 (더 선명한 빨강)
                shifted_idx = x_idx - self.plot_upd_interval # 스파이크 선 이동량 동기화
                if shifted_idx >= 0: 
                    new_sa_spike_idxs.append(shifted_idx)
        self.sa_spike_idxs = new_sa_spike_idxs

        self.ra_v_line.set_ydata(list(self.ra_v_hist)); self.ra_u_line.set_ydata(list(self.ra_u_hist))
        new_ra_spike_idxs=deque(maxlen=self.ra_spike_idxs.maxlen)
        for x_idx in self.ra_spike_idxs:
            if x_idx >= 0:
                self.drawn_spike_lines.append(self.ax_ra.axvline(x_idx,color='#e60026',ls='--',lw=1.5))
                shifted_idx = x_idx - self.plot_upd_interval # 스파이크 선 이동량 동기화
                if shifted_idx >= 0:
                    new_ra_spike_idxs.append(shifted_idx)
        self.ra_spike_idxs = new_ra_spike_idxs
        self.plot_canvas.draw()

    def update_neuron(self):
        # 실제 호출 간격 측정 및 출력
        current_time = time.perf_counter()
        elapsed_time = (current_time - self.last_neuron_update_time) * 1000 # 밀리초 단위
        # print(f"Neuron update interval: {elapsed_time:.2f} ms") # 필요시 주석 해제하여 확인
        self.last_neuron_update_time = current_time

        # 마우스 정지 시 속도 0으로 (UI 업데이트용)
        if (time.perf_counter()-self.last_m_t)>self.config['mouse']['m_stop_thresh'] and self.m_pressed:
            self.m_spd=0.0;
            self.update_stat_lbl()
        
        # SpikeEncoder를 사용하여 스파이크 및 뉴런 상태 업데이트
        sa_f, ra_f, sa_vu, ra_vu = self.spike_encoder.step(
            mouse_speed=self.m_spd, 
            avg_mouse_speed=self.avg_m_spd, 
            material_roughness=self.mat_roughness, 
            mouse_pressed=self.m_pressed
        )

        # 뉴런 히스토리 업데이트
        self.sa_v_hist.append(sa_vu[0]); self.sa_u_hist.append(sa_vu[1])
        self.ra_v_hist.append(ra_vu[0]); self.ra_u_hist.append(ra_vu[1])

        if sa_f: 
            # print("SA Spike!") 
            self.sa_spike_idxs.append(self.plot_hist_sz-1)
            self.audio_player.play_sound(self.sa_snd, channel_id=0, volume=self.config['sound'].get('sa_sound_volume', 1.0))
            # SA 뉴런 적응은 SpikeEncoder 내부에서 처리

        if ra_f:
            self.ra_spike_idxs.append(self.plot_hist_sz-1) 
            if self.ra_snd:
                s=self.m_spd
                snd_cfg = self.config['sound']
                vol_scl=snd_cfg['ra_min_vol_scl']
                if s<=snd_cfg['ra_vol_min_spd']: vol_scl=snd_cfg['ra_min_vol_scl']
                elif s>=snd_cfg['ra_vol_max_spd']: vol_scl=snd_cfg['ra_max_vol_scl']
                else:
                    den=snd_cfg['ra_vol_max_spd']-snd_cfg['ra_vol_min_spd']
                    if den>0: vol_scl=snd_cfg['ra_min_vol_scl']+((s-snd_cfg['ra_vol_min_spd'])/den)*(snd_cfg['ra_max_vol_scl']-snd_cfg['ra_min_vol_scl'])
                self.audio_player.play_sound(self.ra_snd, channel_id=1, volume=np.clip(vol_scl,0.0,1.0))

        # 그래프 업데이트 주기 관리 -> 매 스텝 업데이트로 변경 -> 원래대로 복구
        self.plot_upd_cnt+=1
        if self.plot_upd_cnt>=self.plot_upd_interval:
        # self.update_plots()
            self.update_plots()
            self.plot_upd_cnt=0

    def closeEvent(self,e): 
        # pygame.mixer.quit() -> AudioPlayer가 처리
        self.audio_player.quit()
        super().closeEvent(e)

if __name__=='__main__': app=QApplication(sys.argv);w=TestWindow();w.show();sys.exit(app.exec()) 