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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

import matplotlib
matplotlib.use('QtAgg')

matplotlib.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Helvetica Neue', 'Arial', 'DejaVu Sans'],
    'axes.titlesize': 14,
    'axes.labelsize': 11,
    'xtick.labelsize': 9, 
    'ytick.labelsize': 9,
    'legend.fontsize': 10,
    'figure.dpi': 100,
    'figure.facecolor': '#1c1c1e',
    'axes.facecolor': '#1c1c1e',
    'axes.edgecolor': '#a0a0a0',
    'axes.labelcolor': '#e0e0e0',
    'text.color': '#f0f0f0',
    'xtick.color': '#c0c0c0',
    'ytick.color': '#c0c0c0',
    'grid.color': '#505050',
    'grid.linestyle': '--',
    'grid.alpha': 0.7,
    'lines.linewidth': 1.8
})

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from izhikevich_neuron import IzhikevichNeuron
from audio_player import AudioPlayer
from haptic_renderer import HapticRenderer
from spike_encoder import SpikeEncoder

class Constants:
    DEFAULT_WINDOW_WIDTH = 1200
    DEFAULT_WINDOW_HEIGHT = 1200
    SPIKE_THRESHOLD = 30.0
    MIN_MOUSE_DELTA_TIME = 0.001
    SPIKE_LINE_COLOR = '#e60026'
    SA_LINE_COLOR = '#007aff'
    RA_LINE_COLOR = '#ff9500'
    FADE_OUT_MS = 10
    PLOT_Y_MIN = -90
    PLOT_Y_MAX = 40

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Izhikevich Haptic Test")
        self.setGeometry(50,50,Constants.DEFAULT_WINDOW_WIDTH,Constants.DEFAULT_WINDOW_HEIGHT)

        self.config = self._get_validated_config()
        self.neuron_dt_ms = self.config['neuron_dt_ms']

        main_w=QWidget(); layout=QVBoxLayout(main_w)
        main_w.setStyleSheet("background-color: #48484a;")
        
        self.info_lbl=QLabel("Click/SA, Move/RA (1-3 Mat)",self)
        fnt=self.info_lbl.font();fnt.setPointSize(16);self.info_lbl.setFont(fnt)
        self.info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_lbl)
        self.stat_lbl=QLabel("Mat:S(R:0.3)|Spd:0",self)
        fnt=self.stat_lbl.font();fnt.setPointSize(14);self.stat_lbl.setFont(fnt)
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
        self.sa_v_line,=self.ax_sa.plot(self.x_data,list(self.sa_v_hist),lw=1.8,label='SA_v', color='#007aff')
        self.sa_u_line,=self.ax_sa.plot(self.x_data,list(self.sa_u_hist),lw=1.8,label='SA_u', color='#ff9500')
        self.ax_sa.set_title('SA Neuron')
        self.ax_sa.set_ylabel('V (mV), U', fontsize=12)
        self.ax_sa.set_ylim(-90,40)
        self.ax_sa.set_xlim(0,self.plot_hist_sz-1);self.ax_sa.legend(loc='upper right', frameon=False);self.ax_sa.grid(True)
        self.ax_sa.spines['top'].set_visible(False); self.ax_sa.spines['right'].set_visible(False)

        tick_locs = np.linspace(0, self.plot_hist_sz - 1, 6)
        tick_labels = np.linspace(2500, 0, 6).astype(int)
        self.ax_sa.set_xticks(tick_locs)
        self.ax_sa.set_xticklabels(tick_labels)

        self.ra_v_line,=self.ax_ra.plot(self.x_data,list(self.ra_v_hist),lw=1.8,label='RA_v', color='#007aff')
        self.ra_u_line,=self.ax_ra.plot(self.x_data,list(self.ra_u_hist),lw=1.8,label='RA_u', color='#ff9500')
        self.ax_ra.set_title('RA Neuron')
        self.ax_ra.set_ylabel('V (mV), U', fontsize=12)
        self.ax_ra.set_ylim(-90,40)
        self.ax_ra.set_xlabel('Time (ms)', fontsize=12)

        self.ax_ra.set_xticks(tick_locs)
        self.ax_ra.set_xticklabels(tick_labels)
        self.ax_ra.set_xlim(0,self.plot_hist_sz-1);self.ax_ra.legend(loc='upper right', frameon=False);self.ax_ra.grid(True)
        self.ax_ra.spines['top'].set_visible(False); self.ax_ra.spines['right'].set_visible(False)

        self.fig.tight_layout(pad=3.0);self.plot_canvas=FigureCanvas(self.fig)
        layout.addWidget(self.plot_canvas);self.setCentralWidget(main_w)

        self.audio_player = AudioPlayer()
        self.haptic_renderer = HapticRenderer()

        self.spike_encoder = SpikeEncoder(
            sa_params=self.config['sa_neuron'],
            ra_params=self.config['ra_neuron'],
            neuron_dt_ms=self.config['neuron_dt_ms'],
            input_config=self.config['input_current']
        )

        self.materials = self.config['materials']
        self.mat_keys=list(self.materials.keys())
        self.curr_mat_key=self.mat_keys[0] 
        self.mat_roughness=self.materials[self.curr_mat_key]['r']

        self.sound_cache = {}
        self._init_sounds()

        sa_cfg = self.config['sa_neuron']
        self.sa_init_a = sa_cfg['init_a']
        self.sa_neuron=IzhikevichNeuron(sa_cfg['a'],sa_cfg['b'],sa_cfg['c'],sa_cfg['d'], v_init=sa_cfg['v_init'])
        
        ra_cfg = self.config['ra_neuron']
        self.ra_base_d = ra_cfg['base_d']
        self.ra_click_d_burst = ra_cfg['click_d_burst']
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
        self.plot_upd_interval=self.config['plot']['update_interval']
        self.sa_spike_idxs=deque(maxlen=self.plot_hist_sz)
        self.ra_spike_idxs=deque(maxlen=self.plot_hist_sz)
        self.drawn_spike_lines=[]

        self.update_stat_lbl()
        self.timer=QTimer(self);self.timer.timeout.connect(self.update_neuron);self.timer.start(int(self.neuron_dt_ms))

        self.last_neuron_update_time = time.perf_counter()

    def _init_sounds(self):
        snd_cfg = self.config['sound']
        self.sa_snd = self.haptic_renderer.create_sound_object(
            snd_cfg['sa_hz'], snd_cfg['sa_ms'], snd_cfg['sa_amp'], fade_out_ms=10
        )
        
        for mat_key, mat_props in self.materials.items():
            new_hz = int(snd_cfg['ra_base_hz'] * mat_props['f'])
            cache_key = f"ra_{mat_key}_{new_hz}"
            self.sound_cache[cache_key] = self.haptic_renderer.create_sound_object(
                new_hz, snd_cfg['ra_ms'], snd_cfg['ra_base_amp'], fade_out_ms=10
            )
        
        self.ra_snd = self.sound_cache[f"ra_{self.curr_mat_key}_{int(snd_cfg['ra_base_hz'] * self.materials[self.curr_mat_key]['f'])}"]

    def _update_ra_sound(self): 
        mat_props=self.materials[self.curr_mat_key]
        snd_cfg = self.config['sound']
        new_hz=int(snd_cfg['ra_base_hz']*mat_props['f'])
        self.ra_snd = self.haptic_renderer.create_sound_object(new_hz, snd_cfg['ra_ms'], snd_cfg['ra_base_amp'], fade_out_ms=10); self.update_stat_lbl()

    def keyPressEvent(self,e:QKeyEvent):
        k=e.key()
        if Qt.Key.Key_1<=k<=Qt.Key.Key_3:
            self.curr_mat_key=self.mat_keys[k-Qt.Key.Key_1]
            self.mat_roughness=self.materials[self.curr_mat_key]['r']; self._update_ra_sound()
        elif k == Qt.Key.Key_Space:
            if self.timer.isActive():
                self.timer.stop()
                self.info_lbl.setText("PAUSED - Press SPACE to resume")
            else:
                self.timer.start(int(self.neuron_dt_ms))
                self.info_lbl.setText("Click/SA, Move/RA (1-3 Mat)")
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
            neuron_dt_ms=self.config['neuron_dt_ms'],
            input_config=self.config['input_current']
        )
        
        v_init_sa = self.config['sa_neuron']['v_init']
        v_init_ra = self.config['ra_neuron']['v_init']
        
        self.sa_v_hist.clear()
        self.sa_u_hist.clear()
        self.ra_v_hist.clear()
        self.ra_u_hist.clear()
        
        for _ in range(self.plot_hist_sz):
            self.sa_v_hist.append(v_init_sa)
            self.sa_u_hist.append(0.0)
            self.ra_v_hist.append(v_init_ra)
            self.ra_u_hist.append(0.0)
        
        self.sa_spike_idxs.clear()
        self.ra_spike_idxs.clear()
        
        self.m_pressed = False
        self.m_spd = 0.0
        self.spd_hist.clear()
        self.avg_m_spd = 0.0
        
        self.update_stat_lbl()
        print("Simulation reset!")

    def _adjust_volume(self, delta):
        self.config['sound']['sa_sound_volume'] = max(0.0, min(1.0, 
            self.config['sound']['sa_sound_volume'] + delta))
        
        self.config['sound']['ra_max_vol_scl'] = max(0.0, min(1.0,
            self.config['sound']['ra_max_vol_scl'] + delta))
        
        vol = self.config['sound']['sa_sound_volume']
        print(f"Volume adjusted: {vol:.1f}")
        
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
            if dt>0.001:
                dist=np.sqrt((p_now.x()-self.last_m_pos.x())**2+(p_now.y()-self.last_m_pos.y())**2)
                self.m_spd=min(dist/dt,self.max_spd_clamp); self.spd_hist.append(self.m_spd)
                self.avg_m_spd=np.mean(self.spd_hist) if self.spd_hist else 0.0
                self.last_m_pos=p_now; self.last_m_t=t_now; self.update_stat_lbl()

    def update_plots(self):
        for line in self.drawn_spike_lines: line.remove()
        self.drawn_spike_lines.clear()

        self.sa_v_line.set_ydata(list(self.sa_v_hist)); self.sa_u_line.set_ydata(list(self.sa_u_hist))
        new_sa_spike_idxs=deque(maxlen=self.sa_spike_idxs.maxlen)
        for x_idx in self.sa_spike_idxs:
            if x_idx >= 0:
                self.drawn_spike_lines.append(self.ax_sa.axvline(x_idx,color='#e60026',ls='--',lw=1.5))
                shifted_idx = x_idx - self.plot_upd_interval
                if shifted_idx >= 0: 
                    new_sa_spike_idxs.append(shifted_idx)
        self.sa_spike_idxs = new_sa_spike_idxs

        self.ra_v_line.set_ydata(list(self.ra_v_hist)); self.ra_u_line.set_ydata(list(self.ra_u_hist))
        new_ra_spike_idxs=deque(maxlen=self.ra_spike_idxs.maxlen)
        for x_idx in self.ra_spike_idxs:
            if x_idx >= 0:
                self.drawn_spike_lines.append(self.ax_ra.axvline(x_idx,color='#e60026',ls='--',lw=1.5))
                shifted_idx = x_idx - self.plot_upd_interval
                if shifted_idx >= 0:
                    new_ra_spike_idxs.append(shifted_idx)
        self.ra_spike_idxs = new_ra_spike_idxs
        self.plot_canvas.draw()

    def update_neuron(self):
        current_time = time.perf_counter()
        elapsed_time = (current_time - self.last_neuron_update_time) * 1000
        self.last_neuron_update_time = current_time

        if (time.perf_counter()-self.last_m_t)>self.config['mouse']['m_stop_thresh'] and self.m_pressed:
            self.m_spd=0.0;
            self.update_stat_lbl()
        
        sa_f, ra_f, sa_vu, ra_vu = self.spike_encoder.step(
            mouse_speed=self.m_spd, 
            avg_mouse_speed=self.avg_m_spd, 
            material_roughness=self.mat_roughness, 
            mouse_pressed=self.m_pressed
        )

        self.sa_v_hist.append(sa_vu[0]); self.sa_u_hist.append(sa_vu[1])
        self.ra_v_hist.append(ra_vu[0]); self.ra_u_hist.append(ra_vu[1])

        if sa_f: 
            self.sa_spike_idxs.append(self.plot_hist_sz-1)
            self.audio_player.play_sound(self.sa_snd, channel_id=0, volume=self.config['sound'].get('sa_sound_volume', 1.0))

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

        self.plot_upd_cnt+=1
        if self.plot_upd_cnt>=self.plot_upd_interval:
            self.update_plots()
            self.plot_upd_cnt=0

    def closeEvent(self,e): 
        self.audio_player.quit()
        super().closeEvent(e)

    def _get_validated_config(self):
        config = {
            'neuron_dt_ms': 1.0,
            'plot_hist_sz': 500,
            'sa_neuron': {
                'a': 0.02, 'b': 0.2, 'c': -65.0, 'd': 8.0,
                'v_init': -70.0, 'init_a': 0.02,
            },
            'ra_neuron': {
                'base_a': 0.1, 'base_b': 0.2, 'base_c': -65.0, 'base_d': 2.0,
                'v_init': -65.0, 'click_d_burst': 20.0,
            },
            'input_current': {
                'click_mag': 12.0, 'ra_scl_chg': 20.0, 'ra_scl_spd_dev': 0.02,
                'ra_clip_min': -30.0, 'ra_clip_max': 30.0,
                'RA_SUSTAIN_DURATION': 5, 'ra_min_spd_for_input': 1.0,
            },
            'sound': {
                'sa_hz': 50, 'sa_ms': 120, 'sa_amp': 0.15, 'sa_sound_volume': 1.0,
                'ra_base_hz': 80, 'ra_ms': 100, 'ra_base_amp': 0.6,
                'ra_vol_min_spd': 100.0, 'ra_vol_max_spd': 5000.0,
                'ra_min_vol_scl': 0.6, 'ra_max_vol_scl': 1,
            },
            'mouse': {
                'max_spd_clamp': 100000.0, 'm_stop_thresh': 0.05,
            },
            'plot': {'update_interval': 5,},
            'materials': {
                'S': {'r': 0.3, 'f': 1.0},
                'M': {'r': 0.7, 'f': 1.1},
                'R': {'r': 1.2, 'f': 1.2}
            }
        }
        
        self._validate_config(config)
        return config

    def _validate_config(self, config):
        assert config['neuron_dt_ms'] > 0, "neuron_dt_ms must be positive"
        assert config['plot_hist_sz'] > 0, "plot_hist_sz must be positive"
        
        sound_cfg = config['sound']
        assert 0 < sound_cfg['sa_hz'] < 22050, "sa_hz must be in valid audio range"
        assert 0 < sound_cfg['ra_base_hz'] < 22050, "ra_base_hz must be in valid audio range"
        assert 0 <= sound_cfg['sa_sound_volume'] <= 1.0, "sa_sound_volume must be 0-1"
        
        for mat_name, mat_props in config['materials'].items():
            assert 'r' in mat_props and 'f' in mat_props, f"Material {mat_name} missing properties"
            assert mat_props['r'] > 0, f"Material {mat_name} roughness must be positive"
            assert mat_props['f'] > 0, f"Material {mat_name} frequency factor must be positive"
        
        print("Configuration validated successfully!")

if __name__=='__main__': app=QApplication(sys.argv);w=TestWindow();w.show();sys.exit(app.exec()) 