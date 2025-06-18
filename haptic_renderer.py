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

    def create_material_sound(self, material_type, hz, ms, amp, fade_out_ms=10, **kwargs):
        """
        재질별 특화 파형을 가진 사운드 객체를 생성
        
        Parameters:
        - material_type: 재질 타입 ('glass', 'metal', 'wood', 'plastic', 'fabric', 'ceramic', 'rubber')
        - hz: 기본 주파수 (Hz)
        - ms: 지속시간 (ms)
        - amp: 진폭 (0.0~1.0)
        - fade_out_ms: 페이드아웃 시간 (ms)
        - **kwargs: 재질별 추가 파라미터
        
        Returns:
        - pygame.mixer.Sound: 재질 특성이 반영된 사운드 객체
        """
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