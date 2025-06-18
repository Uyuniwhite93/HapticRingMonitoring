'''
Audio Player for Haptic Feedback
햅틱 피드백용 오디오 플레이어 - pygame을 사용하여 뉴런 스파이크를 소리로 변환하여 재생
'''
import pygame
import numpy as np
import logging

class AudioPlayer:
    """
    햅틱 피드백을 위한 오디오 플레이어 클래스
    
    pygame.mixer를 사용하여 실시간으로 사운드를 재생하며,
    여러 채널을 통해 동시에 다른 소리들을 재생할 수 있습니다.
    주로 SA(천천히 적응) 뉴런과 RA(빠르게 적응) 뉴런의 스파이크를 
    서로 다른 주파수의 소리로 구분하여 재생합니다.
    """
    
    def __init__(self, freq=44100, size=-16, channels=1, buffer=128):
        """
        Pygame mixer를 초기화합니다.
        
        Parameters:
        - freq: 샘플링 주파수 (Hz) - 오디오 품질 결정
        - size: 샘플 크기 (bits) - 음질과 메모리 사용량 결정
        - channels: 오디오 채널 수 (1=모노, 2=스테레오)
        - buffer: 오디오 버퍼 크기 - 지연시간과 안정성에 영향
        """
        try:
            pygame.mixer.init(freq, size, channels, buffer)
            self.is_initialized = True
            print(f"AudioPlayer initialized with: freq={freq}, size={size}, channels={channels}, buffer={buffer}")
        except pygame.error as e:
            logging.error(f"Failed to initialize pygame mixer: {e}")
            self.is_initialized = False
        except Exception as e:
            logging.error(f"Unexpected error during AudioPlayer initialization: {e}")
            self.is_initialized = False

    def play_sound(self, sound_object, channel_id, volume=1.0):
        """
        주어진 사운드 객체를 지정된 채널과 볼륨으로 재생합니다.
        
        Parameters:
        - sound_object: pygame.mixer.Sound 객체 (HapticRenderer에서 생성)
        - channel_id: 재생할 채널 ID (0=SA뉴런용, 1=RA뉴런용)
        - volume: 재생 볼륨 (0.0~1.0)
        
        Returns:
        - bool: 재생 성공 여부
        
        Data Flow:
        HapticRenderer → Sound Object → AudioPlayer → 스피커 출력
        """
        if not self.is_initialized:
            logging.warning("AudioPlayer not initialized. Cannot play sound.")
            return False
            
        # 입력 검증: pygame.mixer.Sound 객체인지 확인
        if not isinstance(sound_object, pygame.mixer.Sound):
            logging.error("Error: sound_object is not a pygame.mixer.Sound instance.")
            return False
            
        # 입력 검증: 채널 ID가 유효한지 확인
        if not isinstance(channel_id, int) or channel_id < 0:
            logging.error(f"Invalid channel_id: {channel_id}. Must be non-negative integer.")
            return False
            
        # 입력 검증: 볼륨 범위 확인 및 클램핑
        if not 0 <= volume <= 1.0:
            logging.warning(f"Volume {volume} out of range (0.0-1.0). Clamping.")
            volume = np.clip(volume, 0.0, 1.0)
        
        try:
            # 볼륨 설정 후 지정된 채널에서 사운드 재생
            sound_object.set_volume(volume)
            channel = pygame.mixer.Channel(channel_id)
            channel.play(sound_object)
            return True
        except pygame.error as e:
            logging.error(f"Failed to play sound: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error during sound playback: {e}")
            return False

    def quit(self):
        """
        Pygame mixer를 종료합니다.
        메모리 해제 및 리소스 정리를 수행합니다.
        """
        try:
            if self.is_initialized:
                pygame.mixer.quit()
                self.is_initialized = False
                print("AudioPlayer quit.")
        except Exception as e:
            logging.error(f"Error during AudioPlayer quit: {e}")

# 사용 예시 (테스트용)
if __name__ == '__main__':
    """
    AudioPlayer 테스트 코드
    440Hz 사인파를 생성하여 다른 채널과 볼륨으로 재생 테스트
    """
    pygame.init() 
    player = AudioPlayer()

    # 테스트용 440Hz (A4 음) 사인파 생성
    sample_rate = pygame.mixer.get_init()[0]  # 현재 설정된 샘플레이트 가져오기
    duration_ms = 500      # 500ms 길이
    frequency = 440        # 440Hz (A4 음표)
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    time_array = np.linspace(0, duration_ms / 1000.0, num_samples, False)
    
    # 사인파 데이터 생성 (진폭 0.5로 제한하여 클리핑 방지)
    wave_data = 0.5 * np.sin(2 * np.pi * frequency * time_array) 
    
    # 페이드 아웃 효과 추가 (끝부분에서 급격한 소리 차단 방지)
    fade_out_samples = int(sample_rate * 0.05)  # 50ms 페이드 아웃
    if num_samples > fade_out_samples:
        wave_data[num_samples - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
    
    # 16비트 정수로 변환하여 pygame.mixer.Sound 객체 생성
    sound_buffer = (wave_data * 32767).astype(np.int16)
    test_sound = pygame.mixer.Sound(buffer=sound_buffer)

    # 테스트 재생: 채널 0에서 볼륨 0.7로 재생
    print("Playing test sound on channel 0 with volume 0.7...")
    player.play_sound(test_sound, channel_id=0, volume=0.7)
    pygame.time.wait(1000)  # 1초 대기

    # 테스트 재생: 채널 1에서 볼륨 0.3으로 재생
    print("Playing test sound on channel 1 with volume 0.3...")
    player.play_sound(test_sound, channel_id=1, volume=0.3)
    pygame.time.wait(1000)  # 1초 대기
    
    # 리소스 정리
    player.quit()
    pygame.quit() 