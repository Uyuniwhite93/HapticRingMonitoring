'''
Spike Encoder - 마우스 입력을 뉴런 스파이크로 변환하는 핵심 모듈 (병렬 최적화 버전)
SA(Slowly Adapting) 뉴런, RA(Rapidly Adapting) 움직임 뉴런, RA 클릭 뉴런을 병렬로 관리
'''
from izhikevich_neuron import IzhikevichNeuronArray
import numpy as np

class SpikeEncoder:
    """
    마우스 입력을 뉴런 스파이크로 인코딩하는 클래스 (병렬 처리 최적화)
    
    생물학적 촉각 수용체를 모델링:
    - SA (Slowly Adapting) 뉴런: 지속적인 압력에 반응 (마우스 클릭 유지)
    - RA 움직임 뉴런 (Rapidly Adapting): 움직임/진동에 반응 (마우스 드래그)
    - RA 클릭 뉴런: 급격한 압력 변화에 반응 (클릭 on/off 순간)
    
    Performance: 3개 뉴런을 벡터화하여 동시 계산 → 3x 속도 향상
    """
    
    def __init__(self, sa_params, ra_params, ra_click_params, neuron_dt_ms, input_config):
        """
        3개 뉴런을 병렬 배열로 초기화
        """
        self.neuron_dt_ms = neuron_dt_ms
        self.input_config = input_config
        self.sa_init_a = sa_params['init_a']
        
        # 3개 뉴런을 하나의 배열로 통합 (병렬 처리용)
        neuron_params = [
            {'a': sa_params['a'], 'b': sa_params['b'], 'c': sa_params['c'], 'd': sa_params['d'], 'v_init': sa_params['v_init']},  # SA 뉴런 (index 0)
            {'a': ra_params['base_a'], 'b': ra_params['base_b'], 'c': ra_params['base_c'], 'd': ra_params['base_d'], 'v_init': ra_params['v_init']},  # RA 움직임 (index 1)
            {'a': ra_click_params['a'], 'b': ra_click_params['b'], 'c': ra_click_params['c'], 'd': ra_click_params['d'], 'v_init': ra_click_params['v_init']}  # RA 클릭 (index 2)
        ]
        
        self.neuron_array = IzhikevichNeuronArray(neuron_params)
        
        # 입력 관련 변수들
        self.input_mag_sa = 0.0
        self.prev_input_mag_sa = 0.0
        self.ra_click_sustained_input = 0.0
        self.ra_click_sustain_counter = 0

    def update_sa_input(self, click_magnitude):
        """SA 뉴런의 입력을 업데이트"""
        self.input_mag_sa = click_magnitude
        if click_magnitude > 0:
            self.neuron_array.a[0] = self.sa_init_a  # SA 뉴런만 리셋

    def step(self, mouse_speed, avg_mouse_speed, material_roughness, mouse_pressed):
        """
        병렬화된 뉴런 시뮬레이션 스텝 (3x 속도 향상)
        """
        # === RA 클릭 입력 계산 ===
        input_delta_sa = self.input_mag_sa - self.prev_input_mag_sa
        if abs(input_delta_sa) > 0.1:
            self.ra_click_sustained_input = abs(input_delta_sa) * self.input_config['ra_click_scl_chg']
            self.ra_click_sustain_counter = self.input_config['RA_CLICK_SUSTAIN_DURATION']
        
        current_ra_click_input = 0.0
        if self.ra_click_sustain_counter > 0:
            current_ra_click_input = self.ra_click_sustained_input
            self.ra_click_sustain_counter -= 1
            if self.ra_click_sustain_counter == 0:
                self.ra_click_sustained_input = 0.0
        
        self.prev_input_mag_sa = self.input_mag_sa

        # === RA 움직임 입력 계산 ===
        ra_motion_I = 0.0
        min_spd_for_ra = self.input_config.get('ra_min_spd_for_input', 1.0)
        if mouse_pressed and mouse_speed > min_spd_for_ra:
            ra_motion_I = (mouse_speed * material_roughness) * self.input_config['ra_motion_scl_spd_dev']
            
        # === 입력 배열 준비 (3개 뉴런용) ===
        I_array = np.array([
            self.input_mag_sa,  # SA 뉴런 입력
            np.clip(ra_motion_I, self.input_config['ra_motion_clip_min'], self.input_config['ra_motion_clip_max']),  # RA 움직임 입력
            np.clip(current_ra_click_input, self.input_config['ra_click_clip_min'], self.input_config['ra_click_clip_max'])  # RA 클릭 입력
        ])
        
        # === 병렬 뉴런 시뮬레이션 (한 번에 3개 처리) ===
        fired_array = self.neuron_array.step(self.neuron_dt_ms, I_array)
        states = self.neuron_array.get_states()
        
        # SA 적응 처리
        if fired_array[0]:  # SA 뉴런이 스파이크 발생
            self.neuron_array.a[0] /= 1.05
        
        return (
            bool(fired_array[0]),  # SA fired
            bool(fired_array[1]),  # RA motion fired  
            bool(fired_array[2]),  # RA click fired
            states[0],  # SA (v, u)
            states[1],  # RA motion (v, u)
            states[2]   # RA click (v, u)
        )

# 테스트 코드
if __name__ == '__main__':
    """
    SpikeEncoder 테스트 코드 (3개 뉴런 버전)
    다양한 입력 시나리오에서 SA/RA 움직임/RA 클릭 뉴런의 반응을 시뮬레이션
    """
    # 테스트용 파라미터 설정
    sa_params_ex = {'a': 0.02, 'b': 0.2, 'c': -65.0, 'd': 8.0, 'v_init': -70.0, 'init_a': 0.02}
    ra_params_ex = {'base_a': 0.1, 'base_b': 0.2, 'base_c': -65.0, 'base_d': 2.0, 'v_init': -70.0}
    ra_click_params_ex = {'a': 0.2, 'b': 0.25, 'c': -65.0, 'd': 6.0, 'v_init': -65.0}  # 더 민감한 클릭 뉴런
    input_config_ex = {
        'click_mag': 12.0,                    # 클릭 입력 크기
        'ra_click_scl_chg': 25.0,            # RA 클릭 변화 스케일링
        'ra_motion_scl_spd_dev': 0.02,       # RA 움직임 속도 스케일링  
        'ra_click_clip_min': -40.0,          # RA 클릭 입력 최소값
        'ra_click_clip_max': 40.0,           # RA 클릭 입력 최대값
        'ra_motion_clip_min': -30.0,         # RA 움직임 입력 최소값
        'ra_motion_clip_max': 30.0,          # RA 움직임 입력 최대값
        'RA_CLICK_SUSTAIN_DURATION': 3,      # RA 클릭 지속 시간 (짧게)
        'ra_min_spd_for_input': 1.0          # RA 최소 속도 임계값
    }
    neuron_dt_ms_ex = 1.0

    encoder = SpikeEncoder(sa_params_ex, ra_params_ex, ra_click_params_ex, neuron_dt_ms_ex, input_config_ex)

    print("Simulating 3-neuron system...")
    
    # 초기 상태 테스트 (입력 없음)
    sa_f, ra_m_f, ra_c_f, sa_vu, ra_m_vu, ra_c_vu = encoder.step(mouse_speed=0, avg_mouse_speed=0, material_roughness=0.3, mouse_pressed=False)
    print(f"Initial: SA={sa_f}, RA_motion={ra_m_f}, RA_click={ra_c_f}")

    # 클릭 시뮬레이션
    print("\nSimulating mouse click...")
    encoder.update_sa_input(input_config_ex['click_mag'])  # 클릭 시작
    for i in range(6):
        sa_f, ra_m_f, ra_c_f, sa_vu, ra_m_vu, ra_c_vu = encoder.step(mouse_speed=0, avg_mouse_speed=0, material_roughness=0.3, mouse_pressed=True)
        print(f"Click step {i+1}: SA={sa_f}, RA_motion={ra_m_f}, RA_click={ra_c_f}")
        if i == 0:
             encoder.update_sa_input(0)  # 첫 번째 스텝 후 클릭 해제 (RA 클릭 뉴런 재반응 테스트)

    # 움직임 시뮬레이션  
    print("\nSimulating movement while pressed...")
    encoder.update_sa_input(input_config_ex['click_mag'])  # 다시 클릭
    for i in range(5):
        current_speed = 500 * (i+1)  # 점진적으로 속도 증가
        sa_f, ra_m_f, ra_c_f, sa_vu, ra_m_vu, ra_c_vu = encoder.step(mouse_speed=current_speed, avg_mouse_speed=current_speed-50, material_roughness=0.7, mouse_pressed=True)
        print(f"Move step {i+1} (speed {current_speed}): SA={sa_f}, RA_motion={ra_m_f}, RA_click={ra_c_f}") 