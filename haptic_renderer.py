'''Haptic Renderer for generating sound objects from parameters'''
import numpy as np
import pygame

class HapticRenderer:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        if pygame.mixer.get_init() is None:
            print("Warning: Pygame mixer is not initialized. HapticRenderer might rely on a default sample rate.")
        else:
            pass 

    def create_sound_buffer(self, hz, ms, amp, fade_out_ms=10):
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        wave_data = amp * np.sin(2 * np.pi * hz * t)
        
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        return (wave_data * 32767).astype(np.int16)

    def create_sound_object(self, hz, ms, amp, fade_out_ms=10):
        sound_buffer = self.create_sound_buffer(hz, ms, amp, fade_out_ms)
        if sound_buffer.size == 0:
            print(f"Warning: Created empty sound buffer for hz={hz}, ms={ms}, amp={amp}")
            return pygame.mixer.Sound(buffer=np.array([0], dtype=np.int16))
        return pygame.mixer.Sound(buffer=sound_buffer)

# 사용 예시 (테스트용)
if __name__ == '__main__':
    pygame.init()
    if pygame.mixer.get_init() is None:
        pygame.mixer.init()

    renderer = HapticRenderer()
    player = AudioPlayer()

    print("Creating SA sound object...")
    sa_sound = renderer.create_sound_object(hz=120, ms=120, amp=0.15, fade_out_ms= (120 * 0.1) if 120 > 10 else 0)

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