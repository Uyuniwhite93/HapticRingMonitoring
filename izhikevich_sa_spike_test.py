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

# macOS 스타일과 유사하게 Matplotlib 스타일 업데이트
matplotlib.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Helvetica Neue', 'Arial', 'DejaVu Sans'], # macOS 느낌을 위한 폰트 우선순위
    'axes.titlesize': 14, # 제목 크기 약간 키움
    'axes.labelsize': 11, # 축 레이블 크기 약간 키움
    'xtick.labelsize': 9, 
    'ytick.labelsize': 9,
    'legend.fontsize': 10,
    'figure.dpi': 100,
    'axes.facecolor': '#f8f8f8',  # 연한 배경색
    'axes.edgecolor': '#bcbcbc',    # 축 테두리 색
    'axes.labelcolor': '#333333',   # 축 레이블 색
    'xtick.color': '#555555',       # x축 눈금 색
    'ytick.color': '#555555',       # y축 눈금 색
    'grid.color': '#d0d0d0',        # 그리드 색 (더 연하게)
    'grid.linestyle': '--',
    'grid.alpha': 0.7,             # 그리드 투명도
    'lines.linewidth': 1.8          # 기본 선 두께 약간 증가
})

# Matplotlib FigureCanvas 임포트 (QtAgg 백엔드에 맞는 FigureCanvas 사용 시도)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from matplotlib.figure import Figure

# Izhikevich 뉴런 모델: 2차원 미분 방정식으로 뉴런의 발화 패턴을 효율적으로 모델링합니다.
class IzhikevichNeuron:
    def __init__(self, a, b, c, d, v_init=-70.0):
        """Izhikevich 뉴런 모델의 파라미터 및 초기 상태를 설정합니다."""
        self.a = a # u (회복 변수)의 시간 스케일
        self.b = b # u가 v(막 전위)에 얼마나 민감한지 결정
        self.c = c # 스파이크 후 v의 리셋 값
        self.d = d # 스파이크 후 u의 리셋 값
        self.v = v_init
        self.u = self.b * self.v
        self.fired_time_internal = -1 # 짧은 시간 내 연속 스파이크 방지용

    def step(self, dt, I):
        """외부 입력(I)으로 뉴런 상태를 업데이트하고 스파이크 발생 여부를 반환합니다."""
        if self.fired_time_internal > 0 and (time.perf_counter() - self.fired_time_internal) < (2 * dt):
             pass # 짧은 시간 내 재발화 방지 (선택적)
        # Izhikevich 모델 미분 방정식
        self.v += dt * (0.04 * self.v**2 + 5 * self.v + 140 - self.u + I)
        self.u += dt * self.a * (self.b * self.v - self.u)
        fired = False
        if self.v >= 30: # 발화 임계값 도달
            self.v = self.c
            self.u += self.d
            fired = True
            self.fired_time_internal = time.perf_counter()
        return fired

# --- Test Window ---
class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Izhikevich Haptic Test") # 간결한 제목
        self.setGeometry(50,50,1200,1200)
        self.neuron_dt_ms=1.0

        main_w=QWidget(); layout=QVBoxLayout(main_w)
        self.info_lbl=QLabel("Click/SA, Move/RA (1-3 Mat)",self) # 축약된 라벨
        fnt=self.info_lbl.font();fnt.setPointSize(16);self.info_lbl.setFont(fnt)
        layout.addWidget(self.info_lbl)
        self.stat_lbl=QLabel("Mat:S(R:0.3)|Spd:0",self) # 축약된 상태 라벨
        fnt=self.stat_lbl.font();fnt.setPointSize(14);self.stat_lbl.setFont(fnt)
        layout.addWidget(self.stat_lbl)

        self.plot_hist_sz=500
        v_init_val, u_init_sa = -70.0, IzhikevichNeuron(0.02,0.2,-65.0,8.0,v_init=-70.0).u # SA 뉴런 기준 초기 u값
        self.sa_v_hist=deque([v_init_val]*self.plot_hist_sz, maxlen=self.plot_hist_sz)
        self.sa_u_hist=deque([u_init_sa]*self.plot_hist_sz, maxlen=self.plot_hist_sz)
        # RA 뉴런도 유사한 초기 u값을 가질 수 있으나, 파라미터가 다를 수 있으므로 같은 v_init에 대한 b*v로 계산
        u_init_ra = IzhikevichNeuron(0.02,0.2,-65.0,6.0,v_init=-70.0).u
        self.ra_v_hist=deque([v_init_val]*self.plot_hist_sz, maxlen=self.plot_hist_sz)
        self.ra_u_hist=deque([u_init_ra]*self.plot_hist_sz, maxlen=self.plot_hist_sz)
        self.x_data=np.arange(self.plot_hist_sz)

        self.fig=Figure(figsize=(8,6)); self.ax_sa,self.ax_ra=self.fig.subplots(2,1)
        self.sa_v_line,=self.ax_sa.plot(self.x_data,list(self.sa_v_hist),lw=1.8,label='SA_v', color='#007aff') # iOS Blue
        self.sa_u_line,=self.ax_sa.plot(self.x_data,list(self.sa_u_hist),lw=1.8,label='SA_u', color='#ff9500') # iOS Orange
        self.ax_sa.set_title('SA Neuron');self.ax_sa.set_ylabel('V,U');self.ax_sa.set_ylim(-90,40)
        self.ax_sa.set_xlim(0,self.plot_hist_sz-1);self.ax_sa.legend(loc='upper right', frameon=False);self.ax_sa.grid(True)
        self.ax_sa.spines['top'].set_visible(False); self.ax_sa.spines['right'].set_visible(False)

        self.ra_v_line,=self.ax_ra.plot(self.x_data,list(self.ra_v_hist),lw=1.8,label='RA_v', color='#007aff')
        self.ra_u_line,=self.ax_ra.plot(self.x_data,list(self.ra_u_hist),lw=1.8,label='RA_u', color='#ff9500')
        self.ax_ra.set_title('RA Neuron');self.ax_ra.set_ylabel('V,U');self.ax_ra.set_ylim(-90,40)
        self.ax_ra.set_xlabel(f'Time (last {self.plot_hist_sz*self.neuron_dt_ms:.0f} ms)')
        self.ax_ra.set_xlim(0,self.plot_hist_sz-1);self.ax_ra.legend(loc='upper right', frameon=False);self.ax_ra.grid(True)
        self.ax_ra.spines['top'].set_visible(False); self.ax_ra.spines['right'].set_visible(False)

        self.fig.tight_layout(pad=3.0);self.plot_canvas=FigureCanvas(self.fig)
        layout.addWidget(self.plot_canvas);self.setCentralWidget(main_w)

        pygame.mixer.init(44100,-16,2,1024);self.sa_snd=self._create_sound(120,120,0.15)
        self.ra_base_hz=220;self.ra_base_amp=0.25 # ra_sound_original_amp -> ra_base_amp
        self.ra_snd=self._create_sound(self.ra_base_hz,60,self.ra_base_amp)
        self.ra_vol_min_spd=100.0;self.ra_vol_max_spd=1500.0
        self.ra_min_vol_scl=0.4;self.ra_max_vol_scl=1.0

        self.sa_init_a=0.02;self.sa_neuron=IzhikevichNeuron(self.sa_init_a,0.2,-65.0,8.0)
        self.ra_neuron=IzhikevichNeuron(0.02,0.2,-65.0,6.0)
        self.input_mag=0.0;self.prev_input_mag=0.0;self.click_mag=8.0 # 전류 증가 (5.0 -> 8.0)
        self.ra_scl_chg=15.0 # RA 클릭/뗄 때 반응 증폭 (12.0 -> 15.0)
        self.ra_scl_spd_dev=0.05 
        self.ra_clip_min=-30.0 # RA 전류 클리핑 범위 확장 (-20.0 -> -30.0)
        self.ra_clip_max=30.0  # RA 전류 클리핑 범위 확장 (20.0 -> 30.0)

        self.m_pressed=False;self.last_m_pos=QPointF(0,0)
        self.last_m_t=time.perf_counter();self.m_spd=0.0
        self.max_spd_clamp=3000.0;self.m_stop_thresh=0.05 # mouse_stop_threshold_s -> m_stop_thresh
        self.spd_hist=deque(maxlen=10);self.avg_m_spd=0.0

        self.plot_upd_cnt=0;self.plot_upd_interval=5 # 속도 동기화와 시스템 부하 사이의 타협점으로 5로 변경
        self.sa_spike_idxs=deque(maxlen=20)
        self.ra_spike_idxs=deque(maxlen=20) # ra_spike_indices -> ra_spike_idxs
        self.drawn_spike_lines=[]

        self.materials={'S':{'r':0.3,'f':1.0},'M':{'r':0.7,'f':1.1},'R':{'r':1.2,'f':1.2}} # 재질 키 축약
        self.mat_keys=list(self.materials.keys());self.curr_mat_key=self.mat_keys[0] # current_material_name -> curr_mat_key
        self.mat_roughness=self.materials[self.curr_mat_key]['r']
        self._update_ra_sound(); self.update_stat_lbl() # update_status_label -> update_stat_lbl
        self.timer=QTimer(self);self.timer.timeout.connect(self.update_neuron);self.timer.start(int(self.neuron_dt_ms))

    def _create_sound(self,hz,ms,amp):
        sr=pygame.mixer.get_init()[0];n_s=int(sr*(ms/1000.0)); t=np.linspace(0,ms/1000.0,n_s,False)
        w=amp*np.sin(2*np.pi*hz*t); f_o=int(sr*0.01); w[n_s-f_o:]*=np.linspace(1,0,f_o) if n_s>f_o else 1
        return pygame.mixer.Sound(buffer=(w*32767).astype(np.int16))

    def _update_ra_sound(self): # _update_ra_sound_for_material -> _update_ra_sound
        mat_props=self.materials[self.curr_mat_key]
        new_hz=int(self.ra_base_hz*mat_props['f'])
        self.ra_snd=self._create_sound(new_hz,60,self.ra_base_amp); self.update_stat_lbl()

    def keyPressEvent(self,e:QKeyEvent):
        k=e.key()
        if Qt.Key.Key_1<=k<=Qt.Key.Key_3:
            self.curr_mat_key=self.mat_keys[k-Qt.Key.Key_1]
            self.mat_roughness=self.materials[self.curr_mat_key]['r']; self._update_ra_sound()
        else: super().keyPressEvent(e)

    def update_stat_lbl(self): # update_status_label -> update_stat_lbl
        self.stat_lbl.setText(f"Mat:{self.curr_mat_key}(R:{self.mat_roughness:.1f})|Spd:{self.m_spd:.0f}")

    def mousePressEvent(self,e:QPointF):
        self.m_pressed=True; self.input_mag=self.click_mag; p=e.position() if hasattr(e,'position') else QPointF(e.x(),e.y())
        self.last_m_pos=p; self.last_m_t=time.perf_counter(); self.m_spd=0.0; self.spd_hist.clear(); self.avg_m_spd=0.0
        self.sa_neuron.a=self.sa_init_a; self.update_stat_lbl()

    def mouseReleaseEvent(self,e:QPointF):
        self.m_pressed=False; self.input_mag=0.0; self.m_spd=0.0; self.update_stat_lbl()

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
        # SA 뉴런
        sa_f = self.sa_neuron.step(self.neuron_dt_ms, self.input_mag)
        self.sa_v_hist.append(self.sa_neuron.v); self.sa_u_hist.append(self.sa_neuron.u)
        if sa_f: self.sa_spike_idxs.append(self.plot_hist_sz-1); pygame.mixer.Channel(0).play(self.sa_snd); self.sa_neuron.a/=1.05

        # 마우스 정지 시 속도 0으로 (UI 업데이트용)
        if (time.perf_counter()-self.last_m_t)>self.m_stop_thresh and self.m_pressed: self.m_spd=0.0; self.update_stat_lbl()
        
        # RA 뉴런 전류 계산
        input_delta = self.input_mag - self.prev_input_mag
        ra_I_chg = abs(input_delta) * self.ra_scl_chg if abs(input_delta) > 0.1 else 0.0 # 뗄 때도 반응하도록 abs 사용
        self.prev_input_mag = self.input_mag
        
        ra_I_mot = 0.0
        if self.m_pressed and self.m_spd > 10:
            spd_dev = self.m_spd - self.avg_m_spd
            if spd_dev > 5: ra_I_mot = (spd_dev * self.mat_roughness) * self.ra_scl_spd_dev
        
        final_ra_I = np.clip(ra_I_chg + ra_I_mot, self.ra_clip_min, self.ra_clip_max)
        ra_f = self.ra_neuron.step(self.neuron_dt_ms, final_ra_I)
        self.ra_v_hist.append(self.ra_neuron.v); self.ra_u_hist.append(self.ra_neuron.u)
        if ra_f:
            self.ra_spike_idxs.append(self.plot_hist_sz-1) # 스파이크 발생 시 가장 오른쪽에 인덱스 추가
            if self.ra_snd:
                s=self.m_spd; vol_scl=self.ra_min_vol_scl
                if s<=self.ra_vol_min_spd: vol_scl=self.ra_min_vol_scl
                elif s>=self.ra_vol_max_spd: vol_scl=self.ra_max_vol_scl
                else:
                    den=self.ra_vol_max_spd-self.ra_vol_min_spd
                    if den>0: vol_scl=self.ra_min_vol_scl+((s-self.ra_vol_min_spd)/den)*(self.ra_max_vol_scl-self.ra_min_vol_scl)
                self.ra_snd.set_volume(np.clip(vol_scl,0.0,1.0));pygame.mixer.Channel(1).play(self.ra_snd)

        # 그래프 업데이트 주기 관리
        self.plot_upd_cnt+=1
        if self.plot_upd_cnt>=self.plot_upd_interval:
            self.update_plots() # 여기서 스파이크 인덱스가 업데이트(감소)됨
            self.plot_upd_cnt=0

    def closeEvent(self,e): pygame.mixer.quit();super().closeEvent(e)

if __name__=='__main__': app=QApplication(sys.argv);w=TestWindow();w.show();sys.exit(app.exec()) 