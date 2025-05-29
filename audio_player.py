'''Audio Player for Haptic Feedback'''
import pygame
import numpy as np

class AudioPlayer:
    def __init__(self, freq=44100, size=-16, channels=2, buffer=1024):
        """Pygame mixer를 초기화합니다."""
        pygame.mixer.init(freq, size, channels, buffer)
        print(f"AudioPlayer initialized with: freq={freq}, size={size}, channels={channels}, buffer={buffer}")

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

    def quit(self):
        """Pygame mixer를 종료합니다."""
        pygame.mixer.quit()
        print("AudioPlayer quit.")

# 사용 예시 (테스트용)
if __name__ == '__main__':
    pygame.init() 
    player = AudioPlayer()

    sample_rate = pygame.mixer.get_init()[0]
    duration_ms = 500
    frequency = 440
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    time_array = np.linspace(0, duration_ms / 1000.0, num_samples, False)
    wave_data = 0.5 * np.sin(2 * np.pi * frequency * time_array) 
    fade_out_samples = int(sample_rate * 0.05) 
    if num_samples > fade_out_samples:
        wave_data[num_samples - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
    
    sound_buffer = (wave_data * 32767).astype(np.int16)
    test_sound = pygame.mixer.Sound(buffer=sound_buffer)

    print("Playing test sound on channel 0 with volume 0.7...")
    player.play_sound(test_sound, channel_id=0, volume=0.7)
    pygame.time.wait(1000) 

    print("Playing test sound on channel 1 with volume 0.3...")
    player.play_sound(test_sound, channel_id=1, volume=0.3)
    pygame.time.wait(1000) 
    
    player.quit()
    pygame.quit() 