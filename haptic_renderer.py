'''Haptic Renderer for generating sound objects from parameters'''
import numpy as np
import pygame

class HapticRenderer:
    def __init__(self, sample_rate=44100):
        """초기화 시 샘플링 속도를 설정합니다."""
        self.sample_rate = sample_rate
        # Pygame mixer가 초기화되어 있어야 get_init() 호출 가능. 
        # AudioPlayer 등 외부에서 mixer 초기화를 보장한다고 가정
        # 또는 여기서 pygame.mixer.get_init() 호출 대신 명시적 sample_rate 사용
        if pygame.mixer.get_init() is None:
            print("Warning: Pygame mixer is not initialized. HapticRenderer might rely on a default sample rate.")
        else:
            # 실제 mixer의 샘플레이트를 가져와서 사용할 수도 있음
            # self.sample_rate = pygame.mixer.get_init()[0] 
            pass 

    def create_sound_buffer(self, hz, ms, amp, fade_out_ms=10):
        """주어진 파라미터로 사운드 버퍼(Numpy array)를 생성합니다."""
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        wave_data = amp * np.sin(2 * np.pi * hz * t)
        
        # Fade out
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        return (wave_data * 32767).astype(np.int16)

    def create_sound_object(self, hz, ms, amp, fade_out_ms=10):
        """주어진 파라미터로 pygame.mixer.Sound 객체를 생성합니다."""
        sound_buffer = self.create_sound_buffer(hz, ms, amp, fade_out_ms)
        if sound_buffer.size == 0:
            print(f"Warning: Created empty sound buffer for hz={hz}, ms={ms}, amp={amp}")
            # 빈 사운드 객체 반환 (오류 방지)
            return pygame.mixer.Sound(buffer=np.array([0], dtype=np.int16))
        return pygame.mixer.Sound(buffer=sound_buffer)

# 사용 예시 (테스트용)
if __name__ == '__main__':
    pygame.init() # Pygame 전체 초기화
    if pygame.mixer.get_init() is None: # 믹서 초기화 확인 및 수행
        pygame.mixer.init()

    renderer = HapticRenderer()
    player = AudioPlayer() # 이전 단계에서 만든 AudioPlayer 사용

    print("Creating SA sound object...")
    # fade_out_ms 파라미터는 _create_sound의 로직(0.01 * sr)을 기반으로 ms 단위로 설정
    sa_sound = renderer.create_sound_object(hz=120, ms=120, amp=0.15, fade_out_ms= (120 * 0.1) if 120 > 10 else 0) # 예시 fade_out_ms, 기존 로직과 유사하게

    print("Creating RA sound object...")
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