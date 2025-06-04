#!/usr/bin/env python3
"""
간단한 Fade Out 데모 - 왜 필요한지 보여주는 예제
"""

import numpy as np

def show_fade_out_necessity():
    """Fade out이 필요한 이유를 간단한 숫자로 설명"""
    
    print("=== Fade Out이 필요한 이유 ===\n")
    
    # 1. 간단한 사인파 생성 (100ms, 440Hz)
    sample_rate = 44100
    duration_ms = 100
    frequency = 440
    amplitude = 0.5
    
    n_samples = int(sample_rate * duration_ms / 1000)
    t = np.linspace(0, duration_ms/1000, n_samples, False)
    wave = amplitude * np.sin(2 * np.pi * frequency * t)
    
    print(f"사운드 정보:")
    print(f"- 주파수: {frequency}Hz")
    print(f"- 길이: {duration_ms}ms")
    print(f"- 샘플 수: {n_samples}개")
    print(f"- 진폭: {amplitude}")
    
    # 2. Fade out 없는 경우 (갑작스러운 끝)
    print(f"\nFade out 없는 경우:")
    print(f"- 마지막 샘플 값: {wave[-1]:.4f}")
    print(f"- 마지막 변화량: {abs(wave[-1] - 0):.4f}")
    print(f"- 문제: 0이 아닌 값에서 갑자기 0으로 -> '딱' 소리!")
    
    # 3. Fade out 있는 경우 (부드러운 끝)
    fade_out_ms = 10  # 마지막 10ms
    fade_out_samples = int(sample_rate * fade_out_ms / 1000)
    
    wave_with_fade = wave.copy()
    fade_curve = np.linspace(1, 0, fade_out_samples)
    wave_with_fade[-fade_out_samples:] *= fade_curve
    
    print(f"\nFade out 있는 경우:")
    print(f"- 마지막 샘플 값: {wave_with_fade[-1]:.4f}")
    print(f"- 마지막 변화량: {abs(wave_with_fade[-1] - 0):.4f}")
    print(f"- 해결: 점진적으로 0에 도달 -> 부드러운 종료!")
    
    # 4. 실제 예시: 마지막 몇 샘플 비교
    print(f"\n마지막 5개 샘플 비교:")
    print(f"Fade out 없음: {[f'{x:.3f}' for x in wave[-5:]]}")
    print(f"Fade out 있음: {[f'{x:.3f}' for x in wave_with_fade[-5:]]}")
    
    # 5. 클릭 노이즈 정도 계산
    click_intensity_no_fade = abs(wave[-1])
    click_intensity_with_fade = abs(wave_with_fade[-1])
    improvement = (click_intensity_no_fade - click_intensity_with_fade) / click_intensity_no_fade * 100
    
    print(f"\n클릭 노이즈 개선 효과:")
    print(f"- 개선율: {improvement:.1f}%")
    print(f"- 클릭 강도 감소: {click_intensity_no_fade:.4f} -> {click_intensity_with_fade:.4f}")

def show_haptic_analogy():
    """햅틱 피드백 관점에서의 설명"""
    
    print(f"\n=== 햅틱 피드백 관점에서의 중요성 ===")
    
    print(f"\n실제 물체를 만질 때:")
    print(f"손가락을 표면에서 떼기 -> 점진적으로 압력 감소")
    print(f"이것이 자연스러운 촉감!")
    
    print(f"\n오디오 햅틱에서:")
    print(f"Fade out 없음 -> 갑자기 '딱' 끊어짐 -> 부자연스러움")
    print(f"Fade out 있음 -> 부드럽게 사라짐 -> 자연스러운 촉감")
    
    print(f"\n특히 햅틱 링에서:")
    print(f"진동/사운드가 갑자기 멈추면 -> 어색한 감각")
    print(f"점진적으로 사라지면 -> 실제 촉감과 유사한 경험")

def show_technical_details():
    """기술적 세부사항"""
    
    print(f"\n=== 기술적 세부사항 ===")
    
    print(f"\n디지털 오디오에서:")
    print(f"모든 사운드는 숫자 배열 (샘플)")
    print(f"DAC가 이 숫자들을 연속적인 전압으로 변환")
    print(f"스피커가 전압을 공기 진동으로 변환")
    
    print(f"\n문제 발생:")
    print(f"마지막 샘플이 0이 아님 -> 갑작스러운 전압 변화")
    print(f"갑작스러운 전압 변화 -> 스피커 막에 충격")
    print(f"스피커 막 충격 -> '딱' 하는 클릭 소음")
    
    print(f"\nFade out 해결책:")
    print(f"마지막 부분을 점진적으로 0에 수렴")
    print(f"부드러운 전압 변화")
    print(f"클릭 소음 제거")

if __name__ == '__main__':
    show_fade_out_necessity()
    show_haptic_analogy()
    show_technical_details()
    
    print(f"\n=== 결론 ===")
    print(f"Fade out은 단순한 '효과'가 아니라")
    print(f"오디오 기반 햅틱 피드백의 '필수 요소'입니다!")
    print(f"\n목적:")
    print(f"1. 클릭 노이즈 방지 (기술적)")
    print(f"2. 자연스러운 촉감 구현 (사용자 경험)")
    print(f"3. 오디오 품질 향상 (전반적 품질)") 