#!/usr/bin/env python3
"""
오디오 Fade Out 효과 비교 데모
Fade out이 있는 사운드와 없는 사운드의 차이를 시연
"""

import numpy as np
import matplotlib.pyplot as plt

def create_sound_wave(hz=440, ms=100, sample_rate=44100, amp=0.5):
    """기본 사인파 생성"""
    n_samples = int(sample_rate * (ms / 1000.0))
    t = np.linspace(0, ms / 1000.0, n_samples, False)
    wave = amp * np.sin(2 * np.pi * hz * t)
    return wave, t

def apply_fade_out(wave, fade_out_ms=10, sample_rate=44100):
    """Fade out 효과 적용"""
    fade_out_samples = int(sample_rate * (fade_out_ms / 1000.0))
    wave_with_fade = wave.copy()
    
    if len(wave) > fade_out_samples and fade_out_ms > 0:
        fade_curve = np.linspace(1, 0, fade_out_samples)
        wave_with_fade[-fade_out_samples:] *= fade_curve
    
    return wave_with_fade

def demonstrate_click_problem():
    """클릭 노이즈 문제 시연"""
    print("🔊 === 오디오 Fade Out 효과 비교 ===\n")
    
    # 사운드 파라미터
    frequency = 440  # A4 음
    duration_ms = 200
    sample_rate = 44100
    
    # 1. Fade out 없는 사운드 (갑작스러운 끝)
    wave_no_fade, time_axis = create_sound_wave(frequency, duration_ms, sample_rate)
    
    # 2. Fade out 있는 사운드 (부드러운 끝)
    wave_with_fade = apply_fade_out(wave_no_fade, fade_out_ms=20, sample_rate=sample_rate)
    
    # 시각화
    plt.figure(figsize=(12, 8))
    
    # 전체 파형 비교
    plt.subplot(2, 2, 1)
    time_ms = time_axis * 1000
    plt.plot(time_ms, wave_no_fade, 'r-', alpha=0.7, label='Fade out 없음')
    plt.plot(time_ms, wave_with_fade, 'b-', alpha=0.7, label='Fade out 있음')
    plt.title('전체 파형 비교')
    plt.xlabel('시간 (ms)')
    plt.ylabel('진폭')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 끝부분 확대 (마지막 50ms)
    plt.subplot(2, 2, 2)
    start_idx = len(wave_no_fade) - int(sample_rate * 0.05)  # 마지막 50ms
    end_time_ms = time_ms[start_idx:]
    end_wave_no_fade = wave_no_fade[start_idx:]
    end_wave_with_fade = wave_with_fade[start_idx:]
    
    plt.plot(end_time_ms, end_wave_no_fade, 'r-', linewidth=2, label='Fade out 없음')
    plt.plot(end_time_ms, end_wave_with_fade, 'b-', linewidth=2, label='Fade out 있음')
    plt.title('끝부분 확대 (마지막 50ms)')
    plt.xlabel('시간 (ms)')
    plt.ylabel('진폭')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 주파수 스펙트럼 비교
    plt.subplot(2, 2, 3)
    freq_no_fade = np.fft.fft(wave_no_fade)
    freq_with_fade = np.fft.fft(wave_with_fade)
    freqs = np.fft.fftfreq(len(wave_no_fade), 1/sample_rate)
    
    # 양의 주파수만 표시
    positive_freqs = freqs[:len(freqs)//2]
    plt.plot(positive_freqs, np.abs(freq_no_fade[:len(freqs)//2]), 'r-', alpha=0.7, label='Fade out 없음')
    plt.plot(positive_freqs, np.abs(freq_with_fade[:len(freqs)//2]), 'b-', alpha=0.7, label='Fade out 있음')
    plt.title('주파수 스펙트럼 비교')
    plt.xlabel('주파수 (Hz)')
    plt.ylabel('크기')
    plt.xlim(0, 2000)  # 0-2kHz만 표시
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 끝부분의 갑작스러운 변화 비교
    plt.subplot(2, 2, 4)
    # 마지막 몇 샘플의 차이값 계산
    diff_no_fade = np.diff(wave_no_fade[-100:])  # 마지막 100샘플의 차이
    diff_with_fade = np.diff(wave_with_fade[-100:])
    
    plt.plot(diff_no_fade, 'r-', linewidth=2, label='Fade out 없음 (급격한 변화)')
    plt.plot(diff_with_fade, 'b-', linewidth=2, label='Fade out 있음 (부드러운 변화)')
    plt.title('끝부분 변화율 비교 (클릭 노이즈 원인)')
    plt.xlabel('샘플 인덱스')
    plt.ylabel('샘플간 차이값')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    # 수치적 분석
    print("📊 수치적 분석 결과:")
    print(f"Fade out 없음 - 마지막 샘플 값: {wave_no_fade[-1]:.4f}")
    print(f"Fade out 있음 - 마지막 샘플 값: {wave_with_fade[-1]:.4f}")
    print(f"갑작스러운 변화 (클릭 노이즈 원인): {abs(wave_no_fade[-1]):.4f}")
    
    max_diff_no_fade = np.max(np.abs(np.diff(wave_no_fade[-20:])))
    max_diff_with_fade = np.max(np.abs(np.diff(wave_with_fade[-20:])))
    print(f"최대 변화율 - Fade out 없음: {max_diff_no_fade:.4f}")
    print(f"최대 변화율 - Fade out 있음: {max_diff_with_fade:.4f}")
    print(f"클릭 노이즈 감소 효과: {((max_diff_no_fade - max_diff_with_fade) / max_diff_no_fade * 100):.1f}%")

def demonstrate_haptic_context():
    """햅틱 피드백 맥락에서의 중요성"""
    print(f"\n🎯 햅틱 피드백에서 Fade Out의 중요성:")
    print("=" * 50)
    
    print("1. 🔇 클릭 노이즈 방지")
    print("   - 갑작스러운 사운드 종료 → 스피커에서 '딱' 소리")
    print("   - 햅틱 피드백의 자연스러움 저해")
    
    print("\n2. 🌊 자연스러운 촉감 모사")
    print("   - 실제 촉감: 점진적으로 감소")
    print("   - Fade out: 이러한 자연스러운 감소 모사")
    
    print("\n3. 👂 청각적 편안함")
    print("   - 급격한 변화는 귀에 불편함")
    print("   - 부드러운 전환으로 사용자 경험 향상")
    
    print("\n4. 🔧 기술적 이유")
    print("   - 디지털 신호의 불연속성 문제 해결")
    print("   - 오디오 아티팩트 방지")
    print("   - DAC(Digital-to-Analog Converter) 최적화")

if __name__ == '__main__':
    # matplotlib 설정
    import matplotlib
    matplotlib.rcParams['font.family'] = ['DejaVu Sans', 'Malgun Gothic', 'Arial']
    plt.rcParams['axes.unicode_minus'] = False
    
    demonstrate_click_problem()
    demonstrate_haptic_context()
    
    print(f"\n💡 결론:")
    print("Fade out은 단순한 효과가 아니라 오디오 기반 햅틱 피드백의")
    print("품질과 사용자 경험을 결정하는 핵심 기술입니다!") 