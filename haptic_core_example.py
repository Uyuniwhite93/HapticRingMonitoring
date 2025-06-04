#!/usr/bin/env python3
"""
Haptic Ring Monitoring - 핵심 기능 예제
GUI와 그래프를 제외한 핵심 햅틱 피드백 시스템만 구현

핵심 기능:
1. Izhikevich 뉴런 모델 (SA/RA)
2. 마우스 입력 시뮬레이션
3. 스파이크 패턴 생성
4. 재질별 햅틱 피드백
5. 기본 사운드 출력 (선택적)
"""

import time
import numpy as np
import pygame
from collections import deque
from izhikevich_neuron import IzhikevichNeuron
from spike_encoder import SpikeEncoder
from audio_player import AudioPlayer
from haptic_renderer import HapticRenderer

class HapticCore:
    def __init__(self, enable_sound=True):
        """햅틱 피드백 시스템의 핵심 설정 및 초기화"""
        
        # 설정 파라미터
        self.config = {
            'neuron_dt_ms': 1.0,  # 뉴런 시뮬레이션 시간 스텝
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
                'Smooth': {'roughness': 0.3, 'freq_scale': 1.0},
                'Medium': {'roughness': 0.7, 'freq_scale': 1.1},
                'Rough': {'roughness': 1.2, 'freq_scale': 1.2}
            },
            'sound': {
                'sa_hz': 50, 'sa_ms': 120, 'sa_amp': 0.15,
                'ra_base_hz': 80, 'ra_ms': 100, 'ra_base_amp': 0.6
            }
        }
        
        # 스파이크 엔코더 초기화
        self.spike_encoder = SpikeEncoder(
            sa_params=self.config['sa_neuron'],
            ra_params=self.config['ra_neuron'],
            neuron_dt_ms=self.config['neuron_dt_ms'],
            input_config=self.config['input_current']
        )
        
        # 현재 상태
        self.current_material = 'Smooth'
        self.mouse_pressed = False
        self.mouse_speed = 0.0
        self.avg_mouse_speed = 0.0
        self.speed_history = deque(maxlen=10)
        
        # 통계 정보
        self.sa_spike_count = 0
        self.ra_spike_count = 0
        self.simulation_steps = 0
        
        # 사운드 시스템 (선택적)
        self.enable_sound = enable_sound
        if self.enable_sound:
            pygame.init()
            self.audio_player = AudioPlayer()
            self.haptic_renderer = HapticRenderer()
            self._create_sounds()
    
    def _create_sounds(self):
        """사운드 객체 생성"""
        sound_cfg = self.config['sound']
        self.sa_sound = self.haptic_renderer.create_sound_object(
            sound_cfg['sa_hz'], sound_cfg['sa_ms'], sound_cfg['sa_amp'], fade_out_ms=10
        )
        self.ra_sound = self.haptic_renderer.create_sound_object(
            sound_cfg['ra_base_hz'], sound_cfg['ra_ms'], sound_cfg['ra_base_amp'], fade_out_ms=10
        )
    
    def set_material(self, material_name):
        """재질 설정"""
        if material_name in self.config['materials']:
            self.current_material = material_name
            print(f"재질 변경: {material_name} (거칠기: {self.get_roughness():.1f})")
        else:
            print(f"알 수 없는 재질: {material_name}")
    
    def get_roughness(self):
        """현재 재질의 거칠기 반환"""
        return self.config['materials'][self.current_material]['roughness']
    
    def mouse_press(self):
        """마우스 클릭 이벤트"""
        self.mouse_pressed = True
        self.spike_encoder.update_sa_input(self.config['input_current']['click_mag'])
        print(f"마우스 클릭 - SA 뉴런 자극")
    
    def mouse_release(self):
        """마우스 릴리즈 이벤트"""
        self.mouse_pressed = False
        self.spike_encoder.update_sa_input(0.0)
        self.mouse_speed = 0.0
        self.speed_history.clear()
        print(f"마우스 릴리즈")
    
    def update_mouse_speed(self, speed):
        """마우스 속도 업데이트"""
        if self.mouse_pressed:
            self.mouse_speed = speed
            self.speed_history.append(speed)
            self.avg_mouse_speed = np.mean(self.speed_history) if self.speed_history else 0.0
    
    def step(self):
        """한 시뮬레이션 스텝 실행"""
        # 스파이크 엔코더 업데이트
        sa_fired, ra_fired, sa_vu, ra_vu = self.spike_encoder.step(
            mouse_speed=self.mouse_speed,
            avg_mouse_speed=self.avg_mouse_speed,
            material_roughness=self.get_roughness(),
            mouse_pressed=self.mouse_pressed
        )
        
        # 스파이크 발생 처리
        if sa_fired:
            self.sa_spike_count += 1
            print(f"SA 스파이크! (총 {self.sa_spike_count}개)")
            if self.enable_sound:
                self.audio_player.play_sound(self.sa_sound, channel_id=0, volume=1.0)
        
        if ra_fired:
            self.ra_spike_count += 1
            print(f"RA 스파이크! (총 {self.ra_spike_count}개, 속도: {self.mouse_speed:.0f})")
            if self.enable_sound:
                # 속도에 따른 볼륨 조절
                volume = min(1.0, max(0.3, self.mouse_speed / 1000.0))
                self.audio_player.play_sound(self.ra_sound, channel_id=1, volume=volume)
        
        self.simulation_steps += 1
        
        return sa_fired, ra_fired, sa_vu, ra_vu
    
    def get_status(self):
        """현재 상태 정보 반환"""
        return {
            'material': self.current_material,
            'roughness': self.get_roughness(),
            'mouse_pressed': self.mouse_pressed,
            'mouse_speed': self.mouse_speed,
            'avg_speed': self.avg_mouse_speed,
            'sa_spikes': self.sa_spike_count,
            'ra_spikes': self.ra_spike_count,
            'simulation_steps': self.simulation_steps
        }
    
    def print_status(self):
        """현재 상태 출력"""
        status = self.get_status()
        print(f"\n=== 햅틱 시스템 상태 ===")
        print(f"재질: {status['material']} (거칠기: {status['roughness']:.1f})")
        print(f"마우스: {'클릭됨' if status['mouse_pressed'] else '릴리즈됨'}")
        print(f"속도: {status['mouse_speed']:.0f} (평균: {status['avg_speed']:.0f})")
        print(f"스파이크: SA {status['sa_spikes']}개, RA {status['ra_spikes']}개")
        print(f"시뮬레이션 스텝: {status['simulation_steps']}")
        print("========================\n")
    
    def cleanup(self):
        """정리 작업"""
        if self.enable_sound:
            self.audio_player.quit()
            pygame.quit()


def simulate_mouse_interaction(haptic_core, duration_ms=5000):
    """마우스 상호작용 시뮬레이션"""
    print(f"마우스 상호작용 시뮬레이션 시작 ({duration_ms}ms)")
    
    start_time = time.time()
    step_count = 0
    
    # 시뮬레이션 시나리오
    scenarios = [
        # (시작시간(ms), 액션, 파라미터)
        (0, 'press', None),           # 즉시 클릭
        (100, 'move', 100),           # 천천히 움직임
        (500, 'move', 500),           # 빠르게 움직임
        (1000, 'move', 1500),         # 매우 빠르게 움직임
        (1500, 'material', 'Medium'), # 재질 변경
        (2000, 'move', 800),          # 중간 속도
        (2500, 'material', 'Rough'),  # 거친 재질
        (3000, 'move', 300),          # 천천히 움직임
        (4000, 'release', None),      # 릴리즈
        (4500, 'press', None),        # 다시 클릭
        (4800, 'move', 200),          # 천천히 움직임
    ]
    
    scenario_index = 0
    
    while (time.time() - start_time) * 1000 < duration_ms:
        current_time_ms = (time.time() - start_time) * 1000
        
        # 시나리오 실행
        if scenario_index < len(scenarios):
            trigger_time, action, param = scenarios[scenario_index]
            if current_time_ms >= trigger_time:
                if action == 'press':
                    haptic_core.mouse_press()
                elif action == 'release':
                    haptic_core.mouse_release()
                elif action == 'move':
                    haptic_core.update_mouse_speed(param)
                elif action == 'material':
                    haptic_core.set_material(param)
                scenario_index += 1
        
        # 뉴런 업데이트
        haptic_core.step()
        
        # 상태 출력 (매 100 스텝마다)
        step_count += 1
        if step_count % 100 == 0:
            haptic_core.print_status()
        
        # 시뮬레이션 속도 조절 (실제 1ms 간격으로)
        time.sleep(0.001)


def main():
    """메인 함수 - 햅틱 피드백 시스템 데모"""
    print("=== 햅틱 피드백 시스템 핵심 기능 데모 ===\n")
    
    # 사운드 사용 여부 선택
    use_sound = input("사운드를 사용하시겠습니까? (y/n): ").lower().startswith('y')
    
    # 햅틱 시스템 초기화
    haptic_core = HapticCore(enable_sound=use_sound)
    
    try:
        print("\n1. 기본 상태 확인")
        haptic_core.print_status()
        
        print("2. 수동 테스트 (각 단계별로 Enter 키를 누르세요)")
        input("- 마우스 클릭 시뮬레이션을 시작하려면 Enter...")
        
        # 수동 단계별 테스트
        haptic_core.mouse_press()
        for i in range(10):
            haptic_core.step()
            time.sleep(0.01)
        
        input("- 마우스 움직임을 시뮬레이션하려면 Enter...")
        for speed in [100, 300, 800, 1500, 500]:
            haptic_core.update_mouse_speed(speed)
            for i in range(20):
                haptic_core.step()
                time.sleep(0.01)
        
        input("- 재질을 변경하려면 Enter...")
        for material in ['Medium', 'Rough', 'Smooth']:
            haptic_core.set_material(material)
            haptic_core.update_mouse_speed(600)
            for i in range(15):
                haptic_core.step()
                time.sleep(0.01)
        
        input("- 마우스 릴리즈를 시뮬레이션하려면 Enter...")
        haptic_core.mouse_release()
        for i in range(5):
            haptic_core.step()
            time.sleep(0.01)
        
        haptic_core.print_status()
        
        # 자동 시뮬레이션 옵션
        auto_sim = input("\n자동 시뮬레이션을 실행하시겠습니까? (y/n): ").lower().startswith('y')
        if auto_sim:
            print("\n3. 자동 마우스 상호작용 시뮬레이션")
            simulate_mouse_interaction(haptic_core, duration_ms=5000)
            haptic_core.print_status()
        
        print("\n=== 데모 완료 ===")
        
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨")
    
    finally:
        haptic_core.cleanup()
        print("시스템 정리 완료")


if __name__ == '__main__':
    main() 