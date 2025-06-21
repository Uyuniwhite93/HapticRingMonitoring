import numpy as np
import pygame, json

class HapticPlayModule():
    def __init__(self, freq=44100, size=-16, channels=2, buffer=1024):
        self.sample_rate = freq
        # pygame 초기화
        pygame.mixer.init(freq, size, channels, buffer)        

    def play_sound(self, sound_object, channel_id, volume=1.0):
        """주어진 사운드 객체를 지정된 채널과 볼륨으로 재생합니다."""
        if not isinstance(sound_object, pygame.mixer.Sound):
            print("Error: sound_object is not a pygame.mixer.Sound instance.")
            return
        if not 0 <= volume <= 1.0:
            print(f"Warning: Volume {volume} out of range (0.0-1.0). Clamping.")
            volume = np.clip(volume, 0.0, 1.0)
        
        sound_object.set_volume(volume)
        pygame.mixer.Channel(channel_id).play(sound_object)

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

    def quit(self):
        """Pygame mixer를 종료합니다."""
        pygame.mixer.quit()
        print("AudioPlayer quit.")