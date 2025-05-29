'''Izhikevich Neuron Model'''
import time

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