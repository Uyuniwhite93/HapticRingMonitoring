#!/usr/bin/env python3
"""
Simple Haptic Demo - 최소한의 햅틱 피드백 시스템
Pygame이나 GUI 없이 순수하게 Izhikevich 뉴런 모델의 핵심 기능만 구현

핵심 기능:
1. SA/RA 뉴런 시뮬레이션
2. 마우스 입력 시뮬레이션
3. 재질별 스파이크 패턴 차이 확인
"""

import time
import numpy as np
from collections import deque

# 간단한 Izhikevich 뉴런 구현 (독립적)
class SimpleNeuron:
    def __init__(self, a, b, c, d, v_init=-70.0):
        self.a, self.b, self.c, self.d = a, b, c, d
        self.v = v_init
        self.u = self.b * self.v
    
    def step(self, dt, I):
        """뉴런 업데이트 및 스파이크 발생 여부 반환"""
        self.v += dt * (0.04 * self.v**2 + 5 * self.v + 140 - self.u + I)
        self.u += dt * self.a * (self.b * self.v - self.u)
        
        if self.v >= 30:  # 스파이크 발생
            self.v = self.c
            self.u += self.d
            return True
        return False

class SimpleHapticSystem:
    def __init__(self):
        """간단한 햅틱 시스템 초기화"""
        
        # SA 뉴런 (Slowly Adapting - 지속적 압력 감지)
        self.sa_neuron = SimpleNeuron(a=0.02, b=0.2, c=-65.0, d=8.0, v_init=-70.0)
        self.sa_init_a = 0.02  # 적응 초기화용
        
        # RA 뉴런 (Rapidly Adapting - 변화 감지)
        self.ra_neuron = SimpleNeuron(a=0.1, b=0.2, c=-65.0, d=2.0, v_init=-65.0)
        self.ra_base_d = 2.0
        self.ra_burst_d = 20.0
        
        # 시뮬레이션 파라미터
        self.dt = 1.0  # 시간 스텝 (ms)
        self.click_magnitude = 12.0
        self.ra_speed_scale = 0.02
        
        # 재질 정보
        self.materials = {
            'Smooth': 0.3,   # 거칠기
            'Medium': 0.7,
            'Rough': 1.2
        }
        
        # 현재 상태
        self.current_material = 'Smooth'
        self.mouse_pressed = False
        self.mouse_speed = 0.0
        self.sa_input = 0.0
        
        # 통계
        self.sa_spikes = 0
        self.ra_spikes = 0
        self.step_count = 0
    
    def mouse_press(self):
        """마우스 클릭"""
        self.mouse_pressed = True
        self.sa_input = self.click_magnitude
        self.sa_neuron.a = self.sa_init_a  # 적응 초기화
        print("마우스 클릭 - SA 뉴런 자극")
    
    def mouse_release(self):
        """마우스 릴리즈"""
        self.mouse_pressed = False
        self.sa_input = 0.0
        self.mouse_speed = 0.0
        print("마우스 릴리즈")
    
    def set_mouse_speed(self, speed):
        """마우스 속도 설정"""
        self.mouse_speed = speed if self.mouse_pressed else 0.0
    
    def set_material(self, material):
        """재질 변경"""
        if material in self.materials:
            self.current_material = material
            roughness = self.materials[material]
            print(f"재질 변경: {material} (거칠기: {roughness})")
    
    def step(self):
        """한 시뮬레이션 스텝 실행"""
        self.step_count += 1
        
        # SA 뉴런 업데이트
        sa_fired = self.sa_neuron.step(self.dt, self.sa_input)
        if sa_fired:
            self.sa_spikes += 1
            self.sa_neuron.a /= 1.05  # 장기 적응
            print(f"SA 스파이크 발생 (총 {self.sa_spikes}개) - 압력 감지")
        
        # RA 뉴런 업데이트 (속도와 재질에 따른 입력)
        roughness = self.materials[self.current_material]
        ra_input = 0.0
        
        if self.mouse_pressed and self.mouse_speed > 1.0:
            ra_input = (self.mouse_speed * roughness) * self.ra_speed_scale
            ra_input = np.clip(ra_input, -30.0, 30.0)
        
        ra_fired = self.ra_neuron.step(self.dt, ra_input)
        if ra_fired:
            self.ra_spikes += 1
            print(f"RA 스파이크 발생 (총 {self.ra_spikes}개) - 속도:{self.mouse_speed:.0f}, 재질:{self.current_material}")
        
        return sa_fired, ra_fired
    
    def get_neuron_states(self):
        """뉴런 상태 반환"""
        return {
            'sa_v': self.sa_neuron.v,
            'sa_u': self.sa_neuron.u,
            'ra_v': self.ra_neuron.v,
            'ra_u': self.ra_neuron.u
        }
    
    def print_status(self):
        """현재 상태 출력"""
        states = self.get_neuron_states()
        print(f"\n--- 햅틱 시스템 상태 (스텝 {self.step_count}) ---")
        print(f"재질: {self.current_material} (거칠기: {self.materials[self.current_material]})")
        print(f"마우스: {'클릭됨' if self.mouse_pressed else '릴리즈됨'}, 속도: {self.mouse_speed:.0f}")
        print(f"SA 뉴런: V={states['sa_v']:.1f}mV, U={states['sa_u']:.1f} (스파이크: {self.sa_spikes}개)")
        print(f"RA 뉴런: V={states['ra_v']:.1f}mV, U={states['ra_u']:.1f} (스파이크: {self.ra_spikes}개)")
        print("-" * 50)


def run_scenario(haptic, name, steps):
    """시나리오 실행"""
    print(f"\n시나리오: {name}")
    print("-" * 30)
    
    for step_func in steps:
        step_func(haptic)
        
        # 몇 스텝 실행
        for _ in range(10):
            haptic.step()
            time.sleep(0.01)  # 실시간 느낌
    
    haptic.print_status()


def main():
    """메인 데모 함수"""
    print("간단한 햅틱 피드백 시스템 데모\n")
    
    haptic = SimpleHapticSystem()
    haptic.print_status()
    
    print("\n시스템 설명:")
    print("- SA 뉴런: 지속적인 압력(클릭)을 감지, 시간이 지나면서 적응")
    print("- RA 뉴런: 변화(움직임)를 감지, 속도와 재질 거칠기에 반응")
    print("- 재질: Smooth(0.3) < Medium(0.7) < Rough(1.2)")
    
    # 시나리오 1: 기본 클릭
    run_scenario(haptic, "기본 클릭 테스트", [
        lambda h: h.mouse_press(),
        lambda h: time.sleep(0.1),
        lambda h: h.mouse_release()
    ])
    
    # 시나리오 2: 클릭 + 움직임 (부드러운 재질)
    run_scenario(haptic, "부드러운 재질에서 움직임", [
        lambda h: h.set_material('Smooth'),
        lambda h: h.mouse_press(),
        lambda h: h.set_mouse_speed(500),
        lambda h: time.sleep(0.1),
        lambda h: h.set_mouse_speed(1000),
        lambda h: time.sleep(0.1),
        lambda h: h.mouse_release()
    ])
    
    # 시나리오 3: 거친 재질에서 움직임
    run_scenario(haptic, "거친 재질에서 움직임", [
        lambda h: h.set_material('Rough'),
        lambda h: h.mouse_press(),
        lambda h: h.set_mouse_speed(500),
        lambda h: time.sleep(0.1),
        lambda h: h.set_mouse_speed(1000),
        lambda h: time.sleep(0.1),
        lambda h: h.mouse_release()
    ])
    
    # 시나리오 4: 재질별 비교
    print(f"\n재질별 스파이크 비교 테스트")
    print("-" * 30)
    
    for material in ['Smooth', 'Medium', 'Rough']:
        haptic_test = SimpleHapticSystem()
        haptic_test.set_material(material)
        haptic_test.mouse_press()
        haptic_test.set_mouse_speed(800)
        
        # 동일한 조건으로 50스텝 실행
        for _ in range(50):
            haptic_test.step()
        
        haptic_test.mouse_release()
        print(f"{material:6s}: RA 스파이크 {haptic_test.ra_spikes}개 (거칠기 {haptic_test.materials[material]})")
    
    # 시나리오 5: SA 적응 테스트
    print(f"\nSA 뉴런 적응(Adaptation) 테스트")
    print("-" * 30)
    
    adapt_test = SimpleHapticSystem()
    adapt_test.mouse_press()
    
    spike_intervals = []
    last_spike_step = 0
    
    for step in range(200):
        sa_fired, _ = adapt_test.step()
        if sa_fired:
            interval = step - last_spike_step if last_spike_step > 0 else 0
            if interval > 0:
                spike_intervals.append(interval)
                print(f"SA 스파이크 #{adapt_test.sa_spikes}: 간격 {interval}스텝 (a={adapt_test.sa_neuron.a:.4f})")
            last_spike_step = step
    
    if len(spike_intervals) > 1:
        print(f"적응 효과: 첫 간격 {spike_intervals[0]}스텝 → 마지막 간격 {spike_intervals[-1]}스텝")
        print("(간격이 늘어날수록 뉴런이 적응하여 발화 빈도가 감소함)")
    
    print(f"\n데모 완료")
    print(f"총 실행 스텝: {haptic.step_count}")
    print(f"SA 스파이크: {haptic.sa_spikes}개, RA 스파이크: {haptic.ra_spikes}개")


if __name__ == '__main__':
    main() 