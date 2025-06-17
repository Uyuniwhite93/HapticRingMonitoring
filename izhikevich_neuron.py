'''
Izhikevich Neuron Model
Izhikevich 뉴런 모델 구현 - 생물학적 뉴런의 스파이킹 행동을 시뮬레이션하는 수학적 모델
'''
import numpy as np

class IzhikevichNeuron:
    """
    Izhikevich 뉴런 모델 클래스
    
    이 모델은 두 개의 미분방정식으로 뉴런의 막전위(membrane potential)와 회복변수(recovery variable)를 시뮬레이션:
    dv/dt = 0.04*v^2 + 5*v + 140 - u + I  (막전위 변화)
    du/dt = a(bv - u)                      (회복변수 변화)
    
    스파이크 발생 시: v >= 30 mV일 때 v를 c로 리셋, u에 d를 더함
    """
    
    def __init__(self, a, b, c, d, v_init=-70.0):
        """
        뉴런 파라미터 초기화
        
        Parameters:
        - a: 회복변수 u의 시간상수 (작을수록 느린 회복)
        - b: 회복변수 u의 민감도 (막전위 v에 대한 반응성)
        - c: 스파이크 후 막전위 리셋값 (mV)
        - d: 스파이크 후 회복변수 증가량
        - v_init: 초기 막전위 (mV)
        """
        self.a = a          # 회복변수 시간상수
        self.b = b          # 회복변수 민감도  
        self.c = c          # 리셋 막전위
        self.d = d          # 회복변수 증가량
        self.v = v_init     # 현재 막전위 (mV)
        self.u = self.b * self.v  # 회복변수 초기값 (b*v로 설정)

    def step(self, dt, I):
        """
        한 시간 스텝만큼 뉴런 상태를 업데이트 (NumPy 벡터화 최적화)
        
        Parameters:
        - dt: 시간 간격 (ms)
        - I: 입력 전류 (pA)
        
        Returns:
        - fired: 이번 스텝에서 스파이크가 발생했는지 여부 (bool)
        """
        # Izhikevich 모델의 미분방정식을 오일러 방법으로 수치적분 (벡터화)
        # dv/dt = 0.04*v^2 + 5*v + 140 - u + I
        dv_dt = 0.04 * self.v**2 + 5 * self.v + 140 - self.u + I
        self.v += dt * dv_dt
        
        # du/dt = a(bv - u)  
        du_dt = self.a * (self.b * self.v - self.u)
        self.u += dt * du_dt
        
        # 스파이크 검출 및 리셋
        fired = False
        if self.v >= 30:  # 스파이크 임계치 30mV 도달
            self.v = self.c           # 막전위를 c로 리셋
            self.u += self.d          # 회복변수에 d 추가 (후과분극 효과)
            fired = True              # 스파이크 발생 플래그
        
        return fired  # 스파이크 발생 여부 반환


class IzhikevichNeuronArray:
    """
    여러 Izhikevich 뉴런을 동시에 병렬 처리하는 클래스 (벡터화 최적화)
    3개 뉴런을 한 번에 계산하여 성능 향상
    """
    
    def __init__(self, params_list):
        """
        여러 뉴런을 배열로 초기화
        
        Parameters:
        - params_list: 각 뉴런의 파라미터 딕셔너리 리스트
                      [{'a': 0.03, 'b': 0.25, 'c': -65, 'd': 6, 'v_init': -70}, ...]
        """
        self.n_neurons = len(params_list)
        
        # 모든 파라미터를 NumPy 배열로 저장 (벡터화를 위해)
        self.a = np.array([p['a'] for p in params_list])
        self.b = np.array([p['b'] for p in params_list]) 
        self.c = np.array([p['c'] for p in params_list])
        self.d = np.array([p['d'] for p in params_list])
        
        # 뉴런 상태 변수들
        self.v = np.array([p.get('v_init', -70.0) for p in params_list])
        self.u = self.b * self.v  # 초기 회복변수
        
    def step(self, dt, I_array):
        """
        모든 뉴런을 동시에 업데이트 (완전 병렬화)
        
        Parameters:
        - dt: 시간 간격 (ms)
        - I_array: 각 뉴런의 입력 전류 배열 [I_sa, I_ra_motion, I_ra_click]
        
        Returns:
        - fired_array: 각 뉴런의 스파이크 발생 여부 배열 [bool, bool, bool]
        """
        # 모든 뉴런의 미분방정식을 동시에 계산 (벡터화)
        dv_dt = 0.04 * self.v**2 + 5 * self.v + 140 - self.u + I_array
        self.v += dt * dv_dt
        
        du_dt = self.a * (self.b * self.v - self.u)
        self.u += dt * du_dt
        
        # 스파이크 검출 (벡터화)
        fired_mask = self.v >= 30
        
        # 스파이크 발생한 뉴런들만 리셋 (조건부 업데이트)
        self.v[fired_mask] = self.c[fired_mask]
        self.u[fired_mask] += self.d[fired_mask]
        
        return fired_mask  # [True/False, True/False, True/False]
    
    def get_states(self):
        """현재 모든 뉴런의 상태 반환"""
        return [(self.v[i], self.u[i]) for i in range(self.n_neurons)] 