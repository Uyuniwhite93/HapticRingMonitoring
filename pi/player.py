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
    
    def create_material_sound(self, material_type, hz, ms, amp, fade_out_ms=10, **kwargs):
        if material_type == 'glass':
            sound_buffer = self._create_glass_waveform(hz, ms, amp, fade_out_ms, **kwargs)
        elif material_type == 'metal':
            sound_buffer = self._create_metal_waveform(hz, ms, amp, fade_out_ms, **kwargs)
        elif material_type == 'wood':
            sound_buffer = self._create_wood_waveform(hz, ms, amp, fade_out_ms, **kwargs)
        elif material_type == 'plastic':
            sound_buffer = self._create_plastic_waveform(hz, ms, amp, fade_out_ms, **kwargs)
        elif material_type == 'fabric':
            sound_buffer = self._create_fabric_waveform(hz, ms, amp, fade_out_ms, **kwargs)
        elif material_type == 'ceramic':
            sound_buffer = self._create_ceramic_waveform(hz, ms, amp, fade_out_ms, **kwargs)
        elif material_type == 'rubber':
            sound_buffer = self._create_rubber_waveform(hz, ms, amp, fade_out_ms, **kwargs)
        else:
            # 기본 사인파 사용
            sound_buffer = self.create_sound_buffer(hz, ms, amp, fade_out_ms)
        
        if sound_buffer.size == 0:
            print(f"Warning: Created empty {material_type} sound buffer")
            return pygame.mixer.Sound(buffer=np.array([0], dtype=np.int16))
        
        return pygame.mixer.Sound(buffer=sound_buffer)
    
    def _create_glass_waveform(self, hz, ms, amp, fade_out_ms, brightness=2.0):
        """
        유리 재질 파형 생성 - 맑고 날카로우며 배음이 많은 소리
        특징: 높은 배음, 빠른 어택, 긴 서스테인, 날카로운 특성
        """
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 기본파 + 매우 부드러운 배음들 (지직거림 완전 제거)
        fundamental = amp * 0.9 * np.sin(2 * np.pi * hz * t)
        harmonic2 = amp * 0.15 * brightness * 0.3 * np.sin(2 * np.pi * hz * 2 * t)
        harmonic3 = amp * 0.05 * brightness * 0.2 * np.sin(2 * np.pi * hz * 3 * t)
        # 고배음 완전 제거로 깔끔한 소리
        
        # 고주파 노이즈를 거의 제거 (지직거림 방지)
        high_freq_noise = amp * 0.002 * np.random.normal(0, 1, n_s)  # 노이즈 크게 감소
        # 강한 스무딩으로 부드럽게
        high_freq_noise = np.convolve(high_freq_noise, np.ones(50)/50, mode='same')
        
        wave_data = fundamental + harmonic2 + harmonic3 + high_freq_noise
        
        # 빠른 어택, 긴 서스테인을 위한 envelope
        attack_samples = int(0.001 * self.sample_rate)  # 1ms 빠른 어택
        if attack_samples < n_s:
            wave_data[:attack_samples] *= np.linspace(0, 1, attack_samples)
        
        # 페이드아웃
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        return (np.clip(wave_data, -1, 1) * 32767).astype(np.int16)

    def _create_metal_waveform(self, hz, ms, amp, fade_out_ms, resonance=1.5):
        """
        메탈 재질 파형 생성 - 금속성 울림과 복잡한 배음 구조
        특징: 강한 배음, 금속성 링, 긴 여운, 복잡한 주파수 스펙트럼
        """
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 기본파
        fundamental = amp * 0.6 * np.sin(2 * np.pi * hz * t)
        
        # 금속 특유의 부드러운 배음 (비조화 성분 줄임)
        harmonic2 = amp * 0.3 * resonance * 0.6 * np.sin(2 * np.pi * hz * 2.0 * t)  # 정수배로 변경
        harmonic3 = amp * 0.2 * resonance * 0.6 * np.sin(2 * np.pi * hz * 3.0 * t)  # 정수배로 변경
        # 4배음 제거로 고주파 성분 줄임
        
        # 금속 링(ring) 효과 - 더 부드러운 AM 변조
        ring_freq = hz * 0.05  # 더 낮은 주파수 변조
        ring_modulation = 1 + 0.15 * np.sin(2 * np.pi * ring_freq * t)  # 변조 깊이 줄임
        
        # 금속성 노이즈 크게 줄임
        metallic_noise = amp * 0.01 * np.random.normal(0, 1, n_s)
        
        wave_data = (fundamental + harmonic2 + harmonic3) * ring_modulation + metallic_noise
        
        # 금속 특유의 느린 어택
        attack_samples = int(0.005 * self.sample_rate)  # 5ms 어택
        if attack_samples < n_s:
            wave_data[:attack_samples] *= np.linspace(0, 1, attack_samples)
        
        # 긴 여운을 위한 느린 페이드아웃
        fade_out_samples = max(int(self.sample_rate * (fade_out_ms / 1000.0)), int(n_s * 0.3))
        if n_s > fade_out_samples:
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        return (np.clip(wave_data, -1, 1) * 32767).astype(np.int16)

    def _create_wood_waveform(self, hz, ms, amp, fade_out_ms, warmth=1.0):
        """
        나무 재질 파형 생성 - 따뜻하고 부드러운 소리
        특징: 부드러운 배음, 따뜻한 톤, 중간 정도의 어택
        """
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 나무 특유의 부드러운 배음 구조
        fundamental = amp * 0.8 * np.sin(2 * np.pi * hz * t)
        harmonic2 = amp * 0.3 * warmth * np.sin(2 * np.pi * hz * 2 * t)
        harmonic3 = amp * 0.2 * warmth * np.sin(2 * np.pi * hz * 3 * t)
        
        # 저주파 성분 강화 (따뜻함)
        sub_harmonic = amp * 0.1 * warmth * np.sin(2 * np.pi * hz * 0.5 * t)
        
        # 나무의 자연스러운 질감을 위한 저주파 노이즈
        wood_texture = amp * 0.02 * np.random.normal(0, 1, n_s)
        # 저역 통과 필터 효과
        for i in range(1, len(wood_texture)):
            wood_texture[i] = 0.7 * wood_texture[i] + 0.3 * wood_texture[i-1]
        
        wave_data = fundamental + harmonic2 + harmonic3 + sub_harmonic + wood_texture
        
        # 중간 속도 어택
        attack_samples = int(0.003 * self.sample_rate)  # 3ms 어택
        if attack_samples < n_s:
            wave_data[:attack_samples] *= np.linspace(0, 1, attack_samples)
        
        # 자연스러운 페이드아웃
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        return (np.clip(wave_data, -1, 1) * 32767).astype(np.int16)

    def _create_plastic_waveform(self, hz, ms, amp, fade_out_ms, hardness=1.0):
        """
        플라스틱 재질 파형 생성 - 인공적이고 날카로운 소리
        특징: 인공적인 톤, 빠른 감쇠, 중간 정도의 배음
        """
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 플라스틱 특유의 부드러운 인공적인 소리
        fundamental = amp * 0.8 * np.sin(2 * np.pi * hz * t)
        harmonic2 = amp * 0.2 * hardness * 0.7 * np.sin(2 * np.pi * hz * 2 * t)
        # 3배음 제거하고 부드럽게
        
        # 플라스틱의 인공적 특성을 위한 약한 사각파 성분
        square_component = amp * 0.03 * np.sign(np.sin(2 * np.pi * hz * t))  # 사각파 성분 크게 줄임
        
        wave_data = fundamental + harmonic2 + square_component
        
        # 빠른 감쇠 (플라스틱의 짧은 여운)
        decay_envelope = np.exp(-3 * t / (ms / 1000.0))
        wave_data *= decay_envelope
        
        # 빠른 어택
        attack_samples = int(0.001 * self.sample_rate)  # 1ms 어택
        if attack_samples < n_s:
            wave_data[:attack_samples] *= np.linspace(0, 1, attack_samples)
        
        # 페이드아웃
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        return (np.clip(wave_data, -1, 1) * 32767).astype(np.int16)

    def _create_fabric_waveform(self, hz, ms, amp, fade_out_ms, softness=1.0):
        """
        직물 재질 파형 생성 - 부드럽고 노이즈가 많은 소리
        특징: 높은 노이즈 성분, 부드러운 질감, 낮은 음량
        """
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 기본 톤을 더 강하게, 노이즈는 줄임
        fundamental = amp * 0.6 * np.sin(2 * np.pi * hz * t)
        
        # 직물 특유의 부드러운 마찰 노이즈 (크게 줄임)
        fabric_noise = amp * 0.3 * softness * np.random.normal(0, 1, n_s)
        
        # 더 강한 저주파 필터링 (부드러운 느낌)
        for i in range(1, len(fabric_noise)):
            fabric_noise[i] = 0.3 * fabric_noise[i] + 0.7 * fabric_noise[i-1]  # 더 부드럽게
        
        wave_data = fundamental + fabric_noise
        
        # 매우 부드러운 어택
        attack_samples = int(0.01 * self.sample_rate)  # 10ms 어택
        if attack_samples < n_s:
            wave_data[:attack_samples] *= np.linspace(0, 1, attack_samples)
        
        # 자연스러운 페이드아웃
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        return (np.clip(wave_data, -1, 1) * 32767).astype(np.int16)

    def _create_ceramic_waveform(self, hz, ms, amp, fade_out_ms, brittleness=1.5):
        """
        세라믹 재질 파형 생성 - 유리와 비슷하지만 더 둔한 소리
        특징: 중간 정도의 배음, 유리보다 덜 날카로움
        """
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 세라믹 특유의 배음 구조
        fundamental = amp * 0.7 * np.sin(2 * np.pi * hz * t)
        harmonic2 = amp * 0.3 * brittleness * np.sin(2 * np.pi * hz * 2 * t)
        harmonic3 = amp * 0.2 * brittleness * np.sin(2 * np.pi * hz * 3 * t)
        harmonic4 = amp * 0.1 * brittleness * np.sin(2 * np.pi * hz * 4 * t)
        
        wave_data = fundamental + harmonic2 + harmonic3 + harmonic4
        
        # 중간 속도 어택
        attack_samples = int(0.002 * self.sample_rate)  # 2ms 어택
        if attack_samples < n_s:
            wave_data[:attack_samples] *= np.linspace(0, 1, attack_samples)
        
        # 페이드아웃
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        return (np.clip(wave_data, -1, 1) * 32767).astype(np.int16)

    def _create_rubber_waveform(self, hz, ms, amp, fade_out_ms, elasticity=1.0):
        """
        고무 재질 파형 생성 - 부드럽고 탄성적인 소리
        특징: 낮은 주파수, 부드러운 감쇠, 탄성적 특성
        """
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 고무의 탄성적 특성을 위한 낮은 주파수 성분
        fundamental = amp * 0.8 * np.sin(2 * np.pi * hz * 0.8 * t)  # 약간 낮은 주파수
        harmonic2 = amp * 0.2 * elasticity * np.sin(2 * np.pi * hz * 1.6 * t)
        
        # 탄성적 변조 효과
        elastic_modulation = 1 + 0.2 * np.sin(2 * np.pi * hz * 0.1 * t)
        
        wave_data = (fundamental + harmonic2) * elastic_modulation
        
        # 부드러운 어택
        attack_samples = int(0.005 * self.sample_rate)  # 5ms 어택
        if attack_samples < n_s:
            wave_data[:attack_samples] *= np.linspace(0, 1, attack_samples)
        
        # 부드러운 감쇠
        decay_envelope = np.exp(-2 * t / (ms / 1000.0))
        wave_data *= decay_envelope
        
        # 페이드아웃
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        return (np.clip(wave_data, -1, 1) * 32767).astype(np.int16)

    def quit(self):
        """Pygame mixer를 종료합니다."""
        pygame.mixer.quit()
        print("AudioPlayer quit.")