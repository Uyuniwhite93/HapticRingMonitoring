'''
Spike Encoder - 마우스 입력을 뉴런 스파이크로 변환하는 핵심 모듈
SA(Slowly Adapting) 뉴런과 RA(Rapidly Adapting) 뉴런을 관리하며
마우스 클릭, 움직임을 적절한 전류 입력으로 변환하여 뉴런에 전달
'''
from izhikevich_neuron import IzhikevichNeuron
import numpy as np

class SpikeEncoder:
    """
    마우스 입력을 뉴런 스파이크로 인코딩하는 클래스
    
    생물학적 촉각 수용체를 모델링:
    - SA (Slowly Adapting) 뉴런: 지속적인 압력에 반응 (마우스 클릭)
    - RA (Rapidly Adapting) 뉴런: 변화하는 자극에 반응 (마우스 움직임)
    
    Data Flow:
    마우스 입력 → SpikeEncoder → 뉴런 전류 → Izhikevich뉴런 → 스파이크 이벤트
    """
    
    def __init__(self, sa_params, ra_params, neuron_dt_ms, input_config):
        """
        SA와 RA 뉴런 초기화 및 입력 설정
        
        Parameters:
        - sa_params: SA 뉴런 파라미터 딕셔너리 (a, b, c, d, v_init, init_a)
        - ra_params: RA 뉴런 파라미터 딕셔너리 (base_a, base_b, base_c, base_d, v_init, click_d_burst)
        - neuron_dt_ms: 뉴런 시뮬레이션 시간 간격 (ms)
        - input_config: 입력 전류 설정 딕셔너리
        """
        # SA 뉴런 생성 - 지속적인 압력(클릭)을 감지
        self.sa_neuron = IzhikevichNeuron(sa_params['a'], sa_params['b'], sa_params['c'], sa_params['d'], v_init=sa_params['v_init'])
        self.sa_init_a = sa_params['init_a']  # SA 뉴런의 초기 a 파라미터 (적응 속도 제어)
        
        # RA 뉴런 생성 - 변화하는 자극(움직임)을 감지  
        self.ra_neuron = IzhikevichNeuron(ra_params['base_a'], ra_params['base_b'], ra_params['base_c'], ra_params['base_d'], v_init=ra_params['v_init'])
        self.ra_base_d = ra_params['base_d']              # RA 뉴런의 기본 d 파라미터
        self.ra_click_d_burst = ra_params['click_d_burst'] # 클릭 시 일시적으로 증가되는 d 값
        
        self.neuron_dt_ms = neuron_dt_ms      # 시뮬레이션 시간 간격
        self.input_config = input_config      # 입력 전류 설정
        
        # SA 뉴런 입력 관련 변수들
        self.input_mag_sa = 0.0                      # 현재 SA 뉴런 입력 크기
        self.prev_input_mag_sa_for_ra = 0.0         # 이전 프레임의 SA 입력 (RA 변화 감지용)
        
        # RA 뉴런 지속 입력 관련 변수들 (클릭 시 일정 시간 동안 지속되는 입력)
        self.ra_sustained_click_input = 0.0          # RA 뉴런에 지속적으로 가해지는 클릭 입력
        self.ra_sustain_counter = 0                  # 지속 입력 카운터

    def update_sa_input(self, click_magnitude):
        """
        SA 뉴런의 입력을 업데이트 (마우스 클릭/해제 시 호출)
        
        Parameters:
        - click_magnitude: 클릭 입력 크기 (클릭=12.0, 해제=0.0)
        
        SA 뉴런 특성:
        - 클릭 시 즉시 반응하여 스파이크 발생
        - 지속적인 클릭에는 점진적으로 적응 (a 파라미터 감소)
        """
        self.input_mag_sa = click_magnitude
        
        # 새로운 클릭이 시작되면 SA 뉴런의 적응 상태를 초기화
        if click_magnitude > 0:
            self.sa_neuron.a = self.sa_init_a  # 적응 속도를 초기값으로 리셋

    def step(self, mouse_speed, avg_mouse_speed, material_roughness, mouse_pressed):
        """
        한 시뮬레이션 스텝 실행 - 마우스 입력을 뉴런 스파이크로 변환
        
        Parameters:
        - mouse_speed: 현재 마우스 속도 (픽셀/초)
        - avg_mouse_speed: 평균 마우스 속도 (현재 사용되지 않음)
        - material_roughness: 재질 거칠기 (0.3~1.2, RA 뉴런 반응 강도에 영향)
        - mouse_pressed: 마우스 클릭 상태 (bool)
        
        Returns:
        - sa_fired: SA 뉴런 스파이크 발생 여부 (bool)
        - ra_fired: RA 뉴런 스파이크 발생 여부 (bool) 
        - sa_vu: SA 뉴런 상태 (v, u) 튜플
        - ra_vu: RA 뉴런 상태 (v, u) 튜플
        """
        
        # === SA 뉴런 처리 ===
        # SA 뉴런 시뮬레이션 스텝 실행
        sa_fired = self.sa_neuron.step(self.neuron_dt_ms, self.input_mag_sa)
        
        # SA 뉴런이 스파이크를 발생시키면 적응 효과 적용 (점점 덜 반응하게 됨)
        if sa_fired:
            self.sa_neuron.a /= 1.05  # a 파라미터를 5% 감소시켜 적응 속도 증가

        # === RA 뉴런 클릭 변화 감지 ===
        # SA 입력의 변화량을 계산하여 RA 뉴런의 클릭 반응 생성
        input_delta_sa = self.input_mag_sa - self.prev_input_mag_sa_for_ra
        
        # 클릭 상태 변화가 감지되면 RA 뉴런에 일시적인 강한 자극 적용
        if abs(input_delta_sa) > 0.1:  # 임계값 이상의 변화 감지
            # 변화량에 비례하는 지속 입력 설정
            self.ra_sustained_click_input = abs(input_delta_sa) * self.input_config['ra_scl_chg']
            # 지속 시간 카운터 설정 (보통 5 스텝)
            self.ra_sustain_counter = self.input_config['RA_SUSTAIN_DURATION']
            # RA 뉴런을 일시적으로 더 민감하게 만듦 (d 파라미터 증가)
            self.ra_neuron.d = self.ra_click_d_burst
        
        # === RA 뉴런 지속 입력 처리 ===
        current_ra_click_input = 0.0
        if self.ra_sustain_counter > 0:
            # 지속 입력 적용
            current_ra_click_input = self.ra_sustained_click_input
            self.ra_sustain_counter -= 1
            
            # 지속 시간 종료 시 RA 뉴런을 원래 상태로 복원
            if self.ra_sustain_counter == 0:
                self.ra_sustained_click_input = 0.0
                self.ra_neuron.d = self.ra_base_d  # d 파라미터를 기본값으로 복원
        
        # 다음 프레임을 위해 현재 SA 입력 저장
        self.prev_input_mag_sa_for_ra = self.input_mag_sa

        # === RA 뉴런 움직임 입력 처리 ===
        ra_I_mot = 0.0  # 움직임에 의한 RA 뉴런 입력
        min_spd_for_ra = self.input_config.get('ra_min_spd_for_input', 1.0)  # 최소 속도 임계값
        
        # 마우스가 클릭된 상태에서 최소 속도 이상으로 움직일 때만 RA 입력 생성
        if mouse_pressed and mouse_speed > min_spd_for_ra:
            # 입력 크기 = 마우스 속도 × 재질 거칠기 × 스케일링 팩터
            ra_I_mot = (mouse_speed * material_roughness) * self.input_config['ra_scl_spd_dev']
            
        # === 최종 RA 뉴런 입력 계산 ===
        # 클릭 입력과 움직임 입력을 합치고 범위 제한
        final_ra_I = np.clip(current_ra_click_input + ra_I_mot, 
                               self.input_config['ra_clip_min'],   # 최소값: -30.0
                               self.input_config['ra_clip_max'])   # 최대값: 30.0
        
        # RA 뉴런 시뮬레이션 스텝 실행
        ra_fired = self.ra_neuron.step(self.neuron_dt_ms, final_ra_I)
        
        # 결과 반환: 스파이크 발생 여부와 뉴런 상태
        return sa_fired, ra_fired, (self.sa_neuron.v, self.sa_neuron.u), (self.ra_neuron.v, self.ra_neuron.u)

# 테스트 코드
if __name__ == '__main__':
    """
    SpikeEncoder 테스트 코드
    다양한 입력 시나리오에서 SA/RA 뉴런의 반응을 시뮬레이션
    """
    # 테스트용 파라미터 설정
    sa_params_ex = {'a': 0.02, 'b': 0.2, 'c': -65.0, 'd': 8.0, 'v_init': -70.0, 'init_a': 0.02}
    ra_params_ex = {'base_a': 0.1, 'base_b': 0.2, 'base_c': -65.0, 'base_d': 2.0, 'v_init': -70.0, 'click_d_burst': 10.0}
    input_config_ex = {
        'click_mag': 12.0,           # 클릭 입력 크기
        'ra_scl_chg': 20.0,         # RA 변화 스케일링
        'ra_scl_spd_dev': 0.02,     # RA 속도 스케일링  
        'ra_clip_min': -30.0,       # RA 입력 최소값
        'ra_clip_max': 30.0,        # RA 입력 최대값
        'RA_SUSTAIN_DURATION': 5,   # RA 지속 시간
        'ra_min_spd_for_input': 1.0 # RA 최소 속도 임계값
    }
    neuron_dt_ms_ex = 1.0

    encoder = SpikeEncoder(sa_params_ex, ra_params_ex, neuron_dt_ms_ex, input_config_ex)

    print("Simulating spikes...")
    
    # 초기 상태 테스트 (입력 없음)
    sa_f, ra_f, sa_vu, ra_vu = encoder.step(mouse_speed=0, avg_mouse_speed=0, material_roughness=0.3, mouse_pressed=False)
    print(f"Initial: SA={sa_f}, RA={ra_f}, SA_V={sa_vu[0]:.2f}, RA_V={ra_vu[0]:.2f}")

    # 클릭 시뮬레이션
    print("\nSimulating mouse click...")
    encoder.update_sa_input(input_config_ex['click_mag'])  # 클릭 시작
    for i in range(input_config_ex['RA_SUSTAIN_DURATION'] + 2):
        sa_f, ra_f, sa_vu, ra_vu = encoder.step(mouse_speed=0, avg_mouse_speed=0, material_roughness=0.3, mouse_pressed=True)
        print(f"Click step {i+1}: SA={sa_f}, RA={ra_f}, SA_V={sa_vu[0]:.2f}, RA_V={ra_vu[0]:.2f}, RA_d={encoder.ra_neuron.d}")
        if i == 0:
             encoder.update_sa_input(0)  # 첫 번째 스텝 후 클릭 해제

    # 움직임 시뮬레이션  
    print("\nSimulating movement while pressed...")
    encoder.update_sa_input(0)  # 클릭 상태 확실히 해제
    for i in range(5):
        current_speed = 500 * (i+1)  # 점진적으로 속도 증가
        sa_f, ra_f, sa_vu, ra_vu = encoder.step(mouse_speed=current_speed, avg_mouse_speed=current_speed-50, material_roughness=0.7, mouse_pressed=True)
        print(f"Move step {i+1} (speed {current_speed}): SA={sa_f}, RA={ra_f}, SA_V={sa_vu[0]:.2f}, RA_V={ra_vu[0]:.2f}") 