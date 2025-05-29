'''Spike Encoder for Izhikevich Neurons'''
from izhikevich_neuron import IzhikevichNeuron
import numpy as np

class SpikeEncoder:
    def __init__(self, sa_params, ra_params, neuron_dt_ms, input_config):
        """SA 및 RA 뉴런을 초기화하고 관련 설정을 저장합니다."""
        self.sa_neuron = IzhikevichNeuron(sa_params['a'], sa_params['b'], sa_params['c'], sa_params['d'], v_init=sa_params['v_init'])
        self.sa_init_a = sa_params['init_a'] # SA 뉴런의 초기 a 값 (적응용)
        
        self.ra_neuron = IzhikevichNeuron(ra_params['base_a'], ra_params['base_b'], ra_params['base_c'], ra_params['base_d'], v_init=ra_params['v_init'])
        self.ra_base_d = ra_params['base_d']
        self.ra_click_d_burst = ra_params['click_d_burst']
        
        self.neuron_dt_ms = neuron_dt_ms
        self.input_config = input_config # click_mag, ra_scl_chg 등 포함
        
        self.input_mag_sa = 0.0 # SA 뉴런에 가해지는 현재 클릭 입력
        self.prev_input_mag_sa_for_ra = 0.0 # RA 뉴런의 클릭 반응 계산을 위한 이전 SA 입력 크기
        self.ra_sustained_click_input = 0.0
        self.ra_sustain_counter = 0

    def update_sa_input(self, click_magnitude):
        """SA 뉴런에 가해지는 클릭 입력을 업데이트합니다."""
        self.input_mag_sa = click_magnitude
        if click_magnitude > 0: # 클릭 시 SA 뉴런 a 파라미터 리셋 (적응 초기화)
            self.sa_neuron.a = self.sa_init_a 

    def step(self, mouse_speed, avg_mouse_speed, material_roughness, mouse_pressed):
        """뉴런 상태를 업데이트하고 SA, RA 스파이크 발생 여부를 반환합니다."""
        # SA 뉴런 업데이트
        sa_fired = self.sa_neuron.step(self.neuron_dt_ms, self.input_mag_sa)
        if sa_fired:
            self.sa_neuron.a /= 1.05 # 장기 주파수 적응

        # RA 뉴런 전류 계산
        # 1. 클릭/해제에 따른 변화분
        input_delta_sa = self.input_mag_sa - self.prev_input_mag_sa_for_ra
        if abs(input_delta_sa) > 0.1: # SA 입력 변경(클릭 또는 해제) 시
            self.ra_sustained_click_input = abs(input_delta_sa) * self.input_config['ra_scl_chg']
            self.ra_sustain_counter = self.input_config['RA_SUSTAIN_DURATION']
            self.ra_neuron.d = self.ra_click_d_burst # 버스트 모드
        
        current_ra_click_input = 0.0
        if self.ra_sustain_counter > 0:
            current_ra_click_input = self.ra_sustained_click_input
            self.ra_sustain_counter -= 1
            if self.ra_sustain_counter == 0:
                self.ra_sustained_click_input = 0.0
                self.ra_neuron.d = self.ra_base_d # 기본 d 값으로 복원
        
        self.prev_input_mag_sa_for_ra = self.input_mag_sa

        # 2. 움직임에 따른 전류 (이전 로직과 동일)
        ra_I_mot = 0.0
        min_spd_for_ra = self.input_config.get('ra_min_spd_for_input', 1.0)
        if mouse_pressed and mouse_speed > min_spd_for_ra:
            ra_I_mot = (mouse_speed * material_roughness) * self.input_config['ra_scl_spd_dev']
            
        final_ra_I = np.clip(current_ra_click_input + ra_I_mot, 
                               self.input_config['ra_clip_min'], 
                               self.input_config['ra_clip_max'])
        
        ra_fired = self.ra_neuron.step(self.neuron_dt_ms, final_ra_I)
        
        # 반환: SA 스파이크 여부, RA 스파이크 여부, SA 뉴런 (v,u), RA 뉴런 (v,u)
        return sa_fired, ra_fired, (self.sa_neuron.v, self.sa_neuron.u), (self.ra_neuron.v, self.ra_neuron.u)

# 사용 예시 (테스트용)
if __name__ == '__main__':
    # TestWindow의 config에서 가져올 법한 예시 값들
    sa_params_ex = {'a': 0.02, 'b': 0.2, 'c': -65.0, 'd': 8.0, 'v_init': -70.0, 'init_a': 0.02}
    ra_params_ex = {'base_a': 0.1, 'base_b': 0.2, 'base_c': -65.0, 'base_d': 2.0, 'v_init': -70.0, 'click_d_burst': 10.0}
    input_config_ex = {
        'click_mag': 12.0, 'ra_scl_chg': 20.0, 'ra_scl_spd_dev': 0.02,
        'ra_clip_min': -30.0, 'ra_clip_max': 30.0, 'RA_SUSTAIN_DURATION': 5,
        'ra_min_spd_for_input': 1.0
    }
    neuron_dt_ms_ex = 1.0

    encoder = SpikeEncoder(sa_params_ex, ra_params_ex, neuron_dt_ms_ex, input_config_ex)

    # 시뮬레이션 루프 (간단히)
    print("Simulating spikes...")
    # 1. 초기 상태 (클릭 없음, 움직임 없음)
    sa_f, ra_f, sa_vu, ra_vu = encoder.step(mouse_speed=0, avg_mouse_speed=0, material_roughness=0.3, mouse_pressed=False)
    print(f"Initial: SA={sa_f}, RA={ra_f}, SA_V={sa_vu[0]:.2f}, RA_V={ra_vu[0]:.2f}")

    # 2. 마우스 클릭 (SA 입력 발생)
    encoder.update_sa_input(input_config_ex['click_mag']) 
    for i in range(input_config_ex['RA_SUSTAIN_DURATION'] + 2):
        sa_f, ra_f, sa_vu, ra_vu = encoder.step(mouse_speed=0, avg_mouse_speed=0, material_roughness=0.3, mouse_pressed=True) # pressed True 가정
        print(f"Click step {i+1}: SA={sa_f}, RA={ra_f}, SA_V={sa_vu[0]:.2f}, RA_V={ra_vu[0]:.2f}, RA_d={encoder.ra_neuron.d}")
        if i == 0: # 클릭 후 바로 SA 입력 제거 (단발성 클릭처럼)
             encoder.update_sa_input(0)

    # 3. 마우스 움직임 (클릭 유지 상태에서)
    print("\nSimulating movement while pressed...")
    encoder.update_sa_input(0) # 클릭으로 인한 SA 입력은 없다고 가정 (이미 위에서 처리)
    for i in range(5):
        current_speed = 500 * (i+1)
        sa_f, ra_f, sa_vu, ra_vu = encoder.step(mouse_speed=current_speed, avg_mouse_speed=current_speed-50, material_roughness=0.7, mouse_pressed=True)
        print(f"Move step {i+1} (speed {current_speed}): SA={sa_f}, RA={ra_f}, SA_V={sa_vu[0]:.2f}, RA_V={ra_vu[0]:.2f}") 