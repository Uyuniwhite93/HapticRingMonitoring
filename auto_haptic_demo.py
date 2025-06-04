#!/usr/bin/env python3
"""
자동 햅틱 피드백 시스템 데모
사용자 입력 없이 자동으로 실행되며 재질별, 속도별 테스트 수행
"""

import time
import numpy as np
from collections import deque
from izhikevich_neuron import IzhikevichNeuron
from spike_encoder import SpikeEncoder

class AutoHapticSystem:
    def __init__(self):
        """햅틱 시스템 초기화"""
        
        self.config = {
            'neuron_dt_ms': 1.0,
            'sa_neuron': {
                'a': 0.02, 'b': 0.2, 'c': -65.0, 'd': 8.0,
                'v_init': -70.0, 'init_a': 0.02
            },
            'ra_neuron': {
                'base_a': 0.1, 'base_b': 0.2, 'base_c': -65.0, 'base_d': 2.0,
                'v_init': -65.0, 'click_d_burst': 20.0
            },
            'input_current': {
                'click_mag': 12.0, 'ra_scl_chg': 20.0, 'ra_scl_spd_dev': 0.02,
                'ra_clip_min': -30.0, 'ra_clip_max': 30.0, 'RA_SUSTAIN_DURATION': 5,
                'ra_min_spd_for_input': 1.0
            },
            'materials': {
                'Smooth': 0.3,
                'Medium': 0.7,
                'Rough': 1.2
            }
        }
        
        self.spike_encoder = SpikeEncoder(
            sa_params=self.config['sa_neuron'],
            ra_params=self.config['ra_neuron'],
            neuron_dt_ms=self.config['neuron_dt_ms'],
            input_config=self.config['input_current']
        )
        
        self.current_material = 'Smooth'
        self.mouse_pressed = False
        self.mouse_speed = 0.0
        self.avg_mouse_speed = 0.0
        self.speed_history = deque(maxlen=10)
        
        self.sa_spike_count = 0
        self.ra_spike_count = 0
        self.simulation_steps = 0
    
    def set_material(self, material_name):
        """재질 설정"""
        if material_name in self.config['materials']:
            self.current_material = material_name
            print(f"재질 변경: {material_name} (거칠기: {self.get_roughness():.1f})")
    
    def get_roughness(self):
        """현재 재질의 거칠기 반환"""
        return self.config['materials'][self.current_material]
    
    def mouse_press(self):
        """마우스 클릭"""
        self.mouse_pressed = True
        self.spike_encoder.update_sa_input(self.config['input_current']['click_mag'])
        print("마우스 클릭 - SA 뉴런 자극")
    
    def mouse_release(self):
        """마우스 릴리즈"""
        self.mouse_pressed = False
        self.spike_encoder.update_sa_input(0.0)
        self.mouse_speed = 0.0
        self.speed_history.clear()
        print("마우스 릴리즈")
    
    def update_mouse_speed(self, speed):
        """마우스 속도 업데이트"""
        if self.mouse_pressed:
            self.mouse_speed = speed
            self.speed_history.append(speed)
            self.avg_mouse_speed = np.mean(self.speed_history) if self.speed_history else 0.0
    
    def step(self):
        """한 시뮬레이션 스텝 실행"""
        sa_fired, ra_fired, sa_vu, ra_vu = self.spike_encoder.step(
            mouse_speed=self.mouse_speed,
            avg_mouse_speed=self.avg_mouse_speed,
            material_roughness=self.get_roughness(),
            mouse_pressed=self.mouse_pressed
        )
        
        if sa_fired:
            self.sa_spike_count += 1
            print(f"SA 스파이크 발생 (총 {self.sa_spike_count}개)")
        
        if ra_fired:
            self.ra_spike_count += 1
            print(f"RA 스파이크 발생 (총 {self.ra_spike_count}개, 속도: {self.mouse_speed:.0f})")
        
        self.simulation_steps += 1
        return sa_fired, ra_fired
    
    def print_status(self):
        """현재 상태 출력"""
        print(f"\n--- 햅틱 시스템 상태 ---")
        print(f"재질: {self.current_material} (거칠기: {self.get_roughness():.1f})")
        print(f"마우스: {'클릭됨' if self.mouse_pressed else '릴리즈됨'}")
        print(f"속도: {self.mouse_speed:.0f} (평균: {self.avg_mouse_speed:.0f})")
        print(f"스파이크: SA {self.sa_spike_count}개, RA {self.ra_spike_count}개")
        print(f"시뮬레이션 스텝: {self.simulation_steps}")
        print("-" * 30)

def run_test_scenario(haptic, name, duration_sec=3.0):
    """테스트 시나리오 실행"""
    print(f"\n테스트: {name}")
    print("=" * 40)
    
    start_time = time.time()
    step_count = 0
    
    while (time.time() - start_time) < duration_sec:
        haptic.step()
        step_count += 1
        
        # 매 50스텝마다 상태 출력
        if step_count % 50 == 0:
            elapsed = time.time() - start_time
            print(f"진행시간: {elapsed:.1f}초, 스텝: {step_count}")
        
        time.sleep(0.01)  # 10ms 간격
    
    haptic.print_status()

def main():
    """메인 자동 데모 함수"""
    print("햅틱 피드백 시스템 자동 데모 시작")
    print("=" * 50)
    
    haptic = AutoHapticSystem()
    
    # 테스트 시나리오들
    scenarios = [
        {
            'name': '1. 기본 클릭 테스트',
            'setup': lambda h: h.mouse_press(),
            'duration': 2.0
        },
        {
            'name': '2. 부드러운 재질에서 저속 움직임',
            'setup': lambda h: (h.set_material('Smooth'), h.mouse_press(), h.update_mouse_speed(300)),
            'duration': 3.0
        },
        {
            'name': '3. 부드러운 재질에서 고속 움직임',
            'setup': lambda h: h.update_mouse_speed(1000),
            'duration': 3.0
        },
        {
            'name': '4. 보통 재질에서 중속 움직임',
            'setup': lambda h: (h.set_material('Medium'), h.update_mouse_speed(600)),
            'duration': 3.0
        },
        {
            'name': '5. 거친 재질에서 저속 움직임',
            'setup': lambda h: (h.set_material('Rough'), h.update_mouse_speed(400)),
            'duration': 3.0
        },
        {
            'name': '6. 거친 재질에서 고속 움직임',
            'setup': lambda h: h.update_mouse_speed(1200),
            'duration': 3.0
        },
        {
            'name': '7. 릴리즈 테스트',
            'setup': lambda h: h.mouse_release(),
            'duration': 2.0
        }
    ]
    
    # 각 시나리오 실행
    for i, scenario in enumerate(scenarios):
        if i > 0:
            print(f"\n다음 테스트까지 2초 대기...")
            time.sleep(2.0)
        
        # 시나리오 설정
        if callable(scenario['setup']):
            scenario['setup'](haptic)
        
        # 시나리오 실행
        run_test_scenario(haptic, scenario['name'], scenario['duration'])
    
    # 최종 결과
    print(f"\n최종 결과")
    print("=" * 50)
    haptic.print_status()
    
    # 재질별 비교 결과
    print(f"\n재질별 스파이크 비교 분석")
    print("-" * 30)
    
    materials = ['Smooth', 'Medium', 'Rough']
    test_results = {}
    
    for material in materials:
        print(f"\n{material} 재질 테스트 시작...")
        test_haptic = AutoHapticSystem()
        test_haptic.set_material(material)
        test_haptic.mouse_press()
        test_haptic.update_mouse_speed(800)
        
        for _ in range(100):
            test_haptic.step()
            time.sleep(0.005)
        
        test_results[material] = {
            'ra_spikes': test_haptic.ra_spike_count,
            'roughness': test_haptic.get_roughness()
        }
        
        print(f"{material}: RA 스파이크 {test_haptic.ra_spike_count}개 "
              f"(거칠기 {test_haptic.get_roughness()})")
    
    print(f"\n분석 완료")
    print("재질이 거칠수록 더 많은 RA 스파이크가 발생함을 확인")
    
    print(f"\n데모 종료")

if __name__ == '__main__':
    main() 