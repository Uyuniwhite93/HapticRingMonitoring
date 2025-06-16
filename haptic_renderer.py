'''
Haptic Renderer for generating sound objects from parameters
햅틱 렌더러 - 뉴런 스파이크 신호를 사운드 객체로 변환하는 모듈
주파수, 지속시간, 진폭 파라미터를 받아서 pygame.mixer.Sound 객체를 생성
'''
import numpy as np
import pygame

class HapticRenderer:
    """
    햅틱 피드백을 위한 사운드 렌더링 클래스
    
    뉴런의 스파이크 이벤트를 사운드로 변환하여 촉각적 피드백을 제공합니다.
    다양한 타입의 사운드 (단일 주파수, 주파수 스위프)를 생성할 수 있으며,
    각 뉴런 타입(SA, RA)에 맞는 특성의 사운드를 생성합니다.
    
    Data Flow:
    뉴런 스파이크 → 파라미터 (hz, ms, amp) → HapticRenderer → pygame.mixer.Sound
    """
    
    def __init__(self, sample_rate=44100):
        """
        햅틱 렌더러 초기화
        
        Parameters:
        - sample_rate: 오디오 샘플링 주파수 (Hz)
        """
        self.sample_rate = sample_rate
        # pygame mixer 초기화 상태 확인
        if pygame.mixer.get_init() is None:
            print("Warning: Pygame mixer is not initialized. HapticRenderer might rely on a default sample rate.")
        else:
            pass 

    def create_sound_buffer(self, hz, ms, amp, fade_out_ms=10):
        """
        주어진 파라미터로 사운드 버퍼(원시 오디오 데이터)를 생성
        
        Parameters:
        - hz: 주파수 (Hz) - SA뉴런은 낮은 주파수(50Hz), RA뉴런은 높은 주파수(80Hz+)
        - ms: 지속시간 (milliseconds) - SA는 길게(120ms), RA는 짧게(100ms)
        - amp: 진폭 (0.0~1.0) - 소리 크기 결정
        - fade_out_ms: 페이드아웃 시간 (ms) - 갑작스런 소리 끊김 방지
        
        Returns:
        - numpy.ndarray: 16비트 정수 형태의 오디오 데이터
        """
        # 샘플 수 계산: 지속시간 × 샘플레이트
        n_s = int(self.sample_rate * (ms / 1000.0))
        
        # 시간 축 생성 (0부터 지속시간까지)
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 사인파 생성: y = amp * sin(2π * freq * time)
        wave_data = amp * np.sin(2 * np.pi * hz * t)
        
        # 페이드아웃 효과 적용 (끝부분에서 점진적으로 볼륨 감소)
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            # 끝부분을 1에서 0으로 선형 감소
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        # 16비트 정수로 변환 (-32768 ~ 32767 범위)
        return (wave_data * 32767).astype(np.int16)

    def create_sound_object(self, hz, ms, amp, fade_out_ms=10):
        """
        pygame.mixer.Sound 객체를 생성
        
        Parameters:
        - hz: 주파수 (Hz)
        - ms: 지속시간 (ms) 
        - amp: 진폭 (0.0~1.0)
        - fade_out_ms: 페이드아웃 시간 (ms)
        
        Returns:
        - pygame.mixer.Sound: AudioPlayer에서 재생할 수 있는 사운드 객체
        
        Usage in main.py:
        SA뉴런 스파이크 시 → sa_sound = create_sound_object(50, 120, 0.15)
        RA뉴런 스파이크 시 → ra_sound = create_sound_object(80, 100, 0.6)
        """
        sound_buffer = self.create_sound_buffer(hz, ms, amp, fade_out_ms)
        
        # 빈 버퍼 처리 (에러 방지)
        if sound_buffer.size == 0:
            print(f"Warning: Created empty sound buffer for hz={hz}, ms={ms}, amp={amp}")
            return pygame.mixer.Sound(buffer=np.array([0], dtype=np.int16))
        
        return pygame.mixer.Sound(buffer=sound_buffer)

    def create_sweep_sound(self, start_hz, end_hz, ms, amp, fade_out_ms=10):
        """
        주파수 스위프 사운드 생성 (시작 주파수에서 끝 주파수로 변화)
        
        이 기능은 현재 main.py에서 사용되지 않지만, 향후 더 복잡한 햅틱 효과를 위해 준비된 기능입니다.
        예: 마우스 속도에 따라 주파수가 변하는 효과
        
        Parameters:
        - start_hz: 시작 주파수 (Hz)
        - end_hz: 끝 주파수 (Hz) 
        - ms: 지속시간 (ms)
        - amp: 진폭 (0.0~1.0)
        - fade_out_ms: 페이드아웃 시간 (ms)
        
        Returns:
        - pygame.mixer.Sound: 주파수가 시간에 따라 변하는 사운드 객체
        """
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 선형적으로 변화하는 주파수 배열
        frequency_sweep = np.linspace(start_hz, end_hz, n_s)
        
        # 적분하여 위상 계산 (frequency sweep를 위해)
        # 각 시점에서의 순간 주파수를 적분하여 위상 계산
        phase = 2 * np.pi * np.cumsum(frequency_sweep) * (ms / 1000.0) / n_s
        wave_data = amp * np.sin(phase)
        
        # 페이드 아웃 적용
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        sound_buffer = (wave_data * 32767).astype(np.int16)
        if sound_buffer.size == 0:
            print(f"Warning: Created empty sweep sound buffer")
            return pygame.mixer.Sound(buffer=np.array([0], dtype=np.int16))
        return pygame.mixer.Sound(buffer=sound_buffer)

# 사용 예시 (테스트용)
if __name__ == '__main__':
    """
    HapticRenderer 테스트 코드
    SA뉴런과 RA뉴런에 해당하는 사운드를 생성하고 재생
    """
    pygame.init()
    if pygame.mixer.get_init() is None:
        pygame.mixer.init()

    renderer = HapticRenderer()
    player = AudioPlayer()  # AudioPlayer import 필요

    print("Creating SA sound object...")
    # SA뉴런용 사운드: 낮은 주파수(120Hz), 긴 지속시간(120ms), 작은 진폭(0.15)
    sa_sound = renderer.create_sound_object(hz=120, ms=120, amp=0.15, fade_out_ms= (120 * 0.1) if 120 > 10 else 0)

    print("Creating RA sound object...")
    # RA뉴런용 사운드: 높은 주파수(220Hz), 짧은 지속시간(60ms), 큰 진폭(0.25)  
    ra_sound = renderer.create_sound_object(hz=220, ms=60, amp=0.25, fade_out_ms= (60*0.1) if 60 > 10 else 0)

    if sa_sound:
        print("Playing SA sound...")
        player.play_sound(sa_sound, channel_id=0, volume=0.8)
        pygame.time.wait(500)

    if ra_sound:
        print("Playing RA sound...")
        player.play_sound(ra_sound, channel_id=1, volume=0.7)
        pygame.time.wait(500)

    player.quit()
    pygame.quit() 