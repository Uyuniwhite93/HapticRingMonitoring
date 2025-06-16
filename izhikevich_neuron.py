'''
Izhikevich Neuron Model
Izhikevich 뉴런 모델 구현 - 생물학적 뉴런의 스파이킹 행동을 시뮬레이션하는 수학적 모델
'''
import time

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
        self.fired_time_internal = -1  # 마지막 스파이크 시간 (불응기 처리용)

    def step(self, dt, I):
        """
        한 시간 스텝만큼 뉴런 상태를 업데이트
        
        Parameters:
        - dt: 시간 간격 (ms)
        - I: 입력 전류 (pA)
        
        Returns:
        - fired: 이번 스텝에서 스파이크가 발생했는지 여부 (bool)
        """
        # 불응기 처리: 최근에 스파이크가 발생했으면 업데이트 건너뛰기
        if self.fired_time_internal > 0 and (time.perf_counter() - self.fired_time_internal) < (2 * dt):
             pass
        
        # Izhikevich 모델의 미분방정식을 오일러 방법으로 수치적분
        # dv/dt = 0.04*v^2 + 5*v + 140 - u + I
        self.v += dt * (0.04 * self.v**2 + 5 * self.v + 140 - self.u + I)
        
        # du/dt = a(bv - u)  
        self.u += dt * self.a * (self.b * self.v - self.u)
        
        # 스파이크 검출 및 리셋
        fired = False
        if self.v >= 30:  # 스파이크 임계치 30mV 도달
            self.v = self.c           # 막전위를 c로 리셋
            self.u += self.d          # 회복변수에 d 추가 (후과분극 효과)
            fired = True              # 스파이크 발생 플래그
            self.fired_time_internal = time.perf_counter()  # 스파이크 발생 시간 기록
        
        return fired  # 스파이크 발생 여부 반환 