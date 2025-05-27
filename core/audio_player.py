import pygame
import numpy as np

class HapticAudioPlayer:
    """햅틱 피드백을 위한 오디오 재생 클래스"""
    
    def __init__(self):
        # 오디오 시스템 초기화 - 버퍼 크기 줄여서 응답성 향상
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=256)
        
        # 볼륨 제어 변수
        self.current_volume = 0.0
        self.target_volume = 0.0
        self.is_playing = False
        self.current_material = "metal"  # 기본 재질
        
        # 추가된 변수: 2D 방향 특성
        self.direction_angle = 0  # 0도: 정면, 90도: 오른쪽, 180도: 뒤, 270도: 왼쪽
        self.direction_intensity = 0.0  # 방향성 강도 (0.0 ~ 1.0)
        
        # 각 재질의 햅틱 신호 미리 생성 (실시간성 향상)
        self.sounds = {
            "metal": self.generate_metal_haptic(),
            "glass": self.generate_glass_haptic(),
            "wood": self.generate_wood_haptic(),
            "fabric": self.generate_fabric_haptic(),
            "silk": self.generate_silk_haptic()
        }
        
        # 이벤트 사운드
        self.event_sounds = {}
        self.generate_event_sounds()
        
        # 채널 생성 (실시간 전환을 위한 여러 채널)
        self.channels = {material: pygame.mixer.Channel(i) for i, material in enumerate(self.sounds.keys())}
        self.event_channel = pygame.mixer.Channel(len(self.sounds))
        
    def generate_event_sounds(self):
        """터치 시작, 종료 등 이벤트 사운드 생성"""
        sample_rate = 44100
        
        # 터치 시작 이벤트 - 짧고 날카로운 충격
        t = np.linspace(0, 0.1, int(sample_rate * 0.1), False)
        
        # 충격음 - 빠른 상승과 감쇠
        wave = 0.9 * np.sin(2 * np.pi * 180 * t) * np.exp(-40 * t)
        # 고주파 하모닉 추가
        wave += 0.4 * np.sin(2 * np.pi * 360 * t) * np.exp(-50 * t)
        wave += 0.2 * np.sin(2 * np.pi * 720 * t) * np.exp(-60 * t)
        
        # 페이드 아웃
        wave[-int(sample_rate * 0.02):] *= np.linspace(1, 0, int(sample_rate * 0.02))
        
        # 정규화
        wave = wave / np.max(np.abs(wave))
        audio_data = (wave * 32767).astype(np.int16)
        
        # 스테레오로 변환 (좌우 동일)
        stereo_data = np.column_stack((audio_data, audio_data))
        
        self.event_sounds["touch_start"] = pygame.mixer.Sound(buffer=stereo_data)
        
        # 터치 종료 이벤트 - 부드러운 릴리즈
        t = np.linspace(0, 0.08, int(sample_rate * 0.08), False)
        
        # 릴리즈 사운드 - 부드러운 감쇠
        wave = 0.7 * np.sin(2 * np.pi * 140 * t) * np.exp(-30 * t)
        # 저주파 성분 추가
        wave += 0.3 * np.sin(2 * np.pi * 70 * t) * np.exp(-20 * t)
        
        # 페이드 아웃
        wave[-int(sample_rate * 0.03):] *= np.linspace(1, 0, int(sample_rate * 0.03))
        
        # 정규화
        wave = wave / np.max(np.abs(wave))
        audio_data = (wave * 32767).astype(np.int16)
        
        # 스테레오로 변환 (좌우 동일)
        stereo_data = np.column_stack((audio_data, audio_data))
        
        self.event_sounds["touch_end"] = pygame.mixer.Sound(buffer=stereo_data)
        
        # 터치 이탈 이벤트 - 빠르고 특징적인 소리
        t = np.linspace(0, 0.15, int(sample_rate * 0.15), False)
        
        # 주파수가 급격히 높아지는 sweep 사운드 (더 강조됨)
        freq_sweep = np.linspace(200, 600, len(t))  # 더 넓은 주파수 범위
        phase = 2 * np.pi * np.cumsum(freq_sweep) / sample_rate
        wave = 0.8 * np.sin(phase) * np.exp(-15 * t)  # 볼륨 증가 및 감쇠 감소
        
        # 노이즈 성분 추가 (과도하게 거친 느낌)
        noise = np.random.normal(0, 0.5, len(t))  # 노이즈 진폭 증가
        noise_envelope = np.exp(-20 * np.linspace(0, 1, len(t))**1.5)  # 감쇠 패턴 변경
        wave += 0.3 * noise * noise_envelope  # 노이즈 비율 증가
        
        # 추가 알림음 요소
        alert_freq = 350  # 경고음 주파수
        alert_beep = 0.4 * np.sin(2 * np.pi * alert_freq * t) * np.exp(-8 * t)  # 느리게 감쇠
        wave += alert_beep
        
        # 페이드 아웃
        wave[-int(sample_rate * 0.05):] *= np.linspace(1, 0, int(sample_rate * 0.05))
        
        # 정규화
        wave = wave / np.max(np.abs(wave))
        audio_data = (wave * 32767).astype(np.int16)
        
        # 스테레오로 변환 (좌우 동일)
        stereo_data = np.column_stack((audio_data, audio_data))
        
        self.event_sounds["touch_exit"] = pygame.mixer.Sound(buffer=stereo_data)
        
    def generate_metal_haptic(self, duration=1.0):
        """금속 질감의 햅틱 피드백 생성 - 부드럽지만 중간중간 마찰질감(틱)이 느껴지도록"""
        sample_rate = 44100
        t = np.arange(0, duration, 1/sample_rate)
        
        # 기본 주파수 감소 (더 저주파로)
        base_freq = 140  # 160에서 140으로 감소
        
        # 기본 사인파 (진폭 감소하여 더 부드럽게)
        wave = 0.35 * np.sin(2 * np.pi * base_freq * t)  # 0.4에서 0.35로 감소
        
        # 고차 하모닉스 추가 (진폭 감소)
        wave += 0.12 * np.sin(2 * np.pi * base_freq * 1.5 * t)  # 0.15에서 0.12로 감소
        wave += 0.04 * np.sin(2 * np.pi * base_freq * 2.2 * t)  # 주파수와 진폭 미세 조정
        
        # 중간중간 마찰질감(틱) 추가 - 속도 의존적
        tick_freq = 9  # 초당 9번의 틱 (7에서 9로 증가)
        tick_pattern = 0.25 * np.sin(2 * np.pi * tick_freq * t)  # 진폭 증가
        tick_pattern = np.tanh(tick_pattern * 5.5) * 0.18  # 더 뚜렷한 틱
        wave += tick_pattern
        
        # 속도 의존적 틱 패턴 추가 (고속에서 더 뚜렷하게)
        speed_tick_freq = 15  # 고속용 틱 주파수
        speed_tick_pattern = 0.2 * np.sin(2 * np.pi * speed_tick_freq * t)
        speed_tick_pattern = np.tanh(speed_tick_pattern * 6) * 0.15  # 날카로운 틱
        
        # 속도 변화 시뮬레이션 (시간에 따른 진폭 변조)
        speed_mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.8 * t)  # 시간에 따른 속도 변화
        wave += speed_tick_pattern * speed_mod  # 속도 변화에 따라 틱 진폭 조절
        
        # 부드러운 노이즈 추가 (저주파 필터링 강화)
        noise = np.random.normal(0, 0.1, len(t))
        noise_envelope = np.exp(-12 * np.abs(np.fft.rfftfreq(len(noise), 1/sample_rate) / (sample_rate/2)))  # 더 강한 필터링
        filtered_noise = np.fft.irfft(np.fft.rfft(noise) * noise_envelope, len(noise))
        wave += 0.045 * filtered_noise  # 노이즈 양 감소
        
        # 정규화 및 반환
        return self._finalize_wave(wave, sample_rate, duration)
    
    def generate_glass_haptic(self, duration=1.0):
        """유리 질감의 햅틱 피드백 생성 - 더 부드럽지만 마찰질감 느껴지게"""
        sample_rate = 44100
        t = np.arange(0, duration, 1/sample_rate)
        
        # 기본 주파수 감소 (더 저주파로)
        base_freq = 120  # 140에서 120으로 감소
        
        # 기본 사인파 (낮은 진폭)
        wave = 0.25 * np.sin(2 * np.pi * base_freq * t)  # 0.3에서 0.25로 감소
        
        # 고차 하모닉스 추가 (매우 낮은 진폭)
        wave += 0.04 * np.sin(2 * np.pi * base_freq * 1.7 * t)  # 1.8에서 1.7로 변경
        wave += 0.02 * np.sin(2 * np.pi * base_freq * 2.3 * t)  # 2.5에서 2.3으로 감소
        
        # 마찰 질감 추가 (저주파 변조로 변경)
        friction_freq = 30  # 40에서 30으로 감소
        friction_mod = 0.08 * np.sin(2 * np.pi * friction_freq * t)  # 0.1에서 0.08로 감소
        # 비선형 처리로 마찰감 강화하되 부드럽게
        friction_mod = np.tanh(friction_mod * 2.5) * 0.06  # 더 부드럽게
        wave += friction_mod
        
        # 미세한 저주파 진동 추가 (매끄러운 슬라이딩 강화)
        smooth_slide = 0.07 * np.sin(2 * np.pi * 2.5 * t + 0.2 * np.sin(2 * np.pi * 0.8 * t))  # 주파수 감소
        wave += smooth_slide
        
        # 매우 적은 노이즈 추가 (더 부드럽게 필터링)
        noise = np.random.normal(0, 0.02, len(t))
        # 고주파 필터링으로 부드럽게
        noise_envelope = np.exp(-18 * np.abs(np.fft.rfftfreq(len(noise), 1/sample_rate) / (sample_rate/2)))  # 15에서 18로 강화
        filtered_noise = np.fft.irfft(np.fft.rfft(noise) * noise_envelope, len(noise))
        wave += 0.008 * filtered_noise  # 0.01에서 0.008로 감소
        
        # 정규화 및 반환
        return self._finalize_wave(wave, sample_rate, duration)
    
    def generate_wood_haptic(self, duration=1.0):
        """나무 질감의 햅틱 피드백 생성 - 저주파 강화 및 나무결 패턴 강조"""
        sample_rate = 44100
        t = np.arange(0, duration, 1/sample_rate)
        
        # 기본 주파수 (저주파로 변경)
        base_freq = 100  # 180에서 100으로 크게 감소
        
        # 기본 사인파
        wave = 0.3 * np.sin(2 * np.pi * base_freq * t)  # 0.25에서 0.3으로 증가
        
        # 하모닉스 추가
        wave += 0.1 * np.sin(2 * np.pi * base_freq * 1.4 * t)  # 1.6에서 1.4로 감소, 진폭 증가
        wave += 0.05 * np.sin(2 * np.pi * base_freq * 2.0 * t)  # 2.2에서 2.0으로 감소, 진폭 증가
        
        # 나무결 패턴 추가 (중주파) - 더 강화
        grain_freq = 12  # 목재 결 빈도
        grain_pattern = 0.2 * np.sin(2 * np.pi * grain_freq * t)  # 진폭 증가
        grain_pattern = np.tanh(grain_pattern * 4) * 0.15  # 더 뚜렷한 나무결 촉감
        wave += grain_pattern
        
        # 속도 의존적 나무결 마찰감 추가
        speed_grain_freq = 18  # 고속용 나무결 주파수
        speed_grain_amplitude = 0.18
        speed_grain = speed_grain_amplitude * np.sin(2 * np.pi * speed_grain_freq * t)
        speed_grain = np.tanh(speed_grain * 5) * 0.14  # 더 날카로운 나무결 느낌
        
        # 속도 변화 시뮬레이션 (시간에 따른 진폭 변조)
        speed_mod = 0.4 + 0.6 * np.sin(2 * np.pi * 0.7 * t)  # 시간에 따른 속도 변화
        wave += speed_grain * speed_mod  # 속도 변화에 따라 나무결 진폭 조절
        
        # 저주파 둥둥거림 추가 (나무의 중후함)
        thump_freq = 4  # 초당 4회 둥둥거림
        thump_pattern = 0.2 * np.sin(2 * np.pi * thump_freq * t)
        thump_pattern = np.tanh(thump_pattern * 2) * 0.12
        wave += thump_pattern
        
        # 중간 레벨 노이즈 추가
        noise = np.random.normal(0, 0.15, len(t))
        # 중간 정도 필터링
        noise_envelope = np.exp(-8 * np.abs(np.fft.rfftfreq(len(noise), 1/sample_rate) / (sample_rate/2)))
        filtered_noise = np.fft.irfft(np.fft.rfft(noise) * noise_envelope, len(noise))
        wave += 0.08 * filtered_noise
        
        # 정규화 및 반환
        return self._finalize_wave(wave, sample_rate, duration)
    
    def generate_fabric_haptic(self, duration=1.0):
        """패브릭 질감의 햅틱 피드백 생성 - 더 부드럽게"""
        sample_rate = 44100
        t = np.arange(0, duration, 1/sample_rate)
        
        # 기본 주파수 감소
        base_freq = 80  # 100에서 80으로 감소
        
        # 기본 사인파
        wave = 0.35 * np.sin(2 * np.pi * base_freq * t)  # 0.4에서 0.35로 감소
        
        # 하모닉스 추가 (더 부드럽게)
        wave += 0.12 * np.sin(2 * np.pi * base_freq * 1.5 * t)  # 1.7에서 1.5로 감소
        wave += 0.07 * np.sin(2 * np.pi * base_freq * 2.1 * t)  # 2.3에서 2.1로 감소
        
        # 패브릭 특유의 미세한 진동 패턴 추가 (저주파로)
        micro_freq = 15  # 20에서 15로 감소
        micro_mod = 0.18 * np.sin(2 * np.pi * micro_freq * t)  # 0.2에서 0.18로 감소
        
        # 랜덤 패턴으로 불규칙한 질감 (더 부드럽게)
        random_pattern = 0.12 * np.sin(2 * np.pi * 8 * t * (1 + 0.18 * np.sin(2 * np.pi * 0.4 * t)))  # 주파수와 강도 감소
        
        # 변조 적용
        wave = wave * (1.0 + 0.25 * micro_mod + 0.15 * random_pattern)  # 변조 강도 감소
        
        # 미디엄 레벨 노이즈 추가 (더 많은 저주파 필터링)
        noise = np.random.normal(0, 0.15, len(t))  # 0.2에서 0.15로 감소
        # 더 강한 필터링
        noise_envelope = np.exp(-8 * np.abs(np.fft.rfftfreq(len(noise), 1/sample_rate) / (sample_rate/2)))  # 5에서 8로 증가
        filtered_noise = np.fft.irfft(np.fft.rfft(noise) * noise_envelope, len(noise))
        wave += 0.08 * filtered_noise  # 0.1에서 0.08로 감소
        
        # 정규화 및 반환
        return self._finalize_wave(wave, sample_rate, duration)
    
    def generate_silk_haptic(self, duration=1.0):
        """실크 질감의 햅틱 피드백 생성 - 매우 부드럽게"""
        sample_rate = 44100
        t = np.arange(0, duration, 1/sample_rate)
        
        # 기본 주파수 (더 낮은 저주파로 변경)
        base_freq = 55  # 더 낮은 주파수로 감소
        
        # 기본 사인파 (낮은 진폭)
        wave = 0.18 * np.sin(2 * np.pi * base_freq * t)  # 진폭 더 감소
        
        # 하모닉스 추가 (극소량)
        wave += 0.05 * np.sin(2 * np.pi * base_freq * 1.2 * t)
        wave += 0.01 * np.sin(2 * np.pi * base_freq * 1.7 * t)
        
        # 매우 부드러운 흐름 추가 (더 저주파)
        flow_freq = 2.5  # 매우 낮은 주파수로 감소
        flow = 0.04 * np.sin(2 * np.pi * flow_freq * t + 0.08 * np.sin(2 * np.pi * 0.2 * t))
        wave += flow
        
        # 실크 특유의 부드러운 질감 패턴
        texture_freq = 8  # 저주파로 감소
        texture_mod = 0.03 * np.sin(2 * np.pi * texture_freq * t)
        # 더 부드러운 사인 함수 형태
        texture_mod = np.sin(texture_mod * np.pi/4) * 0.02
        wave += texture_mod
        
        # v2의 RA파형 참고하여 속도 기반 진폭 변조 요소 추가 (더 부드럽게)
        mod_depth = 0.03  # 더 작은 값으로 설정
        mod_freq = 1.2    # 더 저주파로
        modulation = 1.0 + mod_depth * np.sin(2 * np.pi * mod_freq * t)
        wave = wave * modulation
        
        # 극소량의 노이즈 추가 (초특급 부드러운 질감)
        noise = np.random.normal(0, 0.01, len(t))  # 더 적은 노이즈
        # 매우 강한 저주파 필터링
        noise_envelope = np.exp(-30 * np.abs(np.fft.rfftfreq(len(noise), 1/sample_rate) / (sample_rate/2)))
        filtered_noise = np.fft.irfft(np.fft.rfft(noise) * noise_envelope, len(noise))
        wave += 0.003 * filtered_noise  # 매우 작은 양
        
        # SA 성분 비중 높이기 (부드러운 압력감)
        t_short = np.arange(0, min(0.1, duration), 1/sample_rate)
        sa_pulse = 0.1 * np.sin(2 * np.pi * 6 * t_short)  # 아주 저주파 SA 성분
        sa_pulse = sa_pulse * np.exp(-3 * np.linspace(0, 1, len(t_short)))
        
        # SA 펄스를 파형 시작부에 추가
        if len(sa_pulse) < len(wave):
            wave[:len(sa_pulse)] += sa_pulse
        
        # 정규화 및 반환
        return self._finalize_wave(wave, sample_rate, duration)
        
    def _finalize_wave(self, wave, sample_rate, duration):
        """파형 완성 및 Sound 객체 생성 - SA/RA 수용체 모델 기반"""
        # 음량 페이드 인/아웃 추가 (클릭 방지)
        fade_samples = int(0.01 * sample_rate)  # 10ms 페이드
        if fade_samples > 0:
            wave[:fade_samples] *= np.linspace(0, 1, fade_samples)
            wave[-fade_samples:] *= np.linspace(1, 0, fade_samples)
        
        # SA/RA 수용체 특성 반영
        t = np.arange(0, duration, 1/sample_rate)
        
        # SA (Slowly Adapting) 수용체 특성 - 지속적 압력을 감지
        # SA-I (머켈 디스크): 저주파 반응, 정밀한 공간 해상도
        sa_component = 0.2 * np.sin(2 * np.pi * 12 * t)  # 15에서 12Hz로 감소
        # 적응 패턴 추가 (점진적 감소)
        sa_adaptation = np.exp(-1.2 * np.linspace(0, 1, len(t))**0.8)  # 1.5에서 1.2로 감소
        sa_component = sa_component * (0.4 + 0.6 * sa_adaptation)
        
        # RA (Rapidly Adapting) 수용체 특성 - 변화를 감지
        # RA-I (마이스너 소체): 중주파 반응, 가벼운 터치와 진동 감지
        ra_component = 0.25 * np.sin(2 * np.pi * 35 * t)  # 40에서 35Hz로 감소
        # 빠른 적응 패턴 (빠르게 반응하고 빠르게 감소)
        ra_adaptation = np.exp(-5 * np.linspace(0, 1, len(t))**0.6)  # 6에서 5로 감소
        ra_component = ra_component * ra_adaptation
        
        # 원래 신호에 SA와 RA 반응 통합 (기존 파형 유지하면서)
        enhanced_wave = wave + 0.35 * sa_component + 0.25 * ra_component  # SA 성분 증가, RA 성분 감소
        
        # 정규화
        enhanced_wave = enhanced_wave / np.max(np.abs(enhanced_wave))
        
        # 16비트 PCM 형식으로 변환
        audio_data = (enhanced_wave * 32767).astype(np.int16)
        
        # 사운드 객체 생성
        return pygame.mixer.Sound(buffer=audio_data)
    
    def _apply_directional_panning(self, left_vol, right_vol):
        """방향감을 위한 좌우 볼륨 조절"""
        # 방향각에 따른 좌우 볼륨 계산
        if self.direction_intensity > 0:
            # 방향각을 라디안으로 변환 (0도=정면, 90도=오른쪽, 180도=뒤, 270도=왼쪽)
            angle_rad = np.radians(self.direction_angle)
            
            # 좌우 볼륨 계산 (코사인, 사인 사용)
            right_factor = 0.5 + 0.5 * np.sin(angle_rad)  # 0~1
            left_factor = 0.5 + 0.5 * np.sin(angle_rad + np.pi)  # 0~1
            
            # 방향 강도 적용
            right_factor = 1.0 - self.direction_intensity * (1.0 - right_factor)
            left_factor = 1.0 - self.direction_intensity * (1.0 - left_factor)
            
            # 기존 볼륨에 방향 인자 적용
            left_vol *= left_factor
            right_vol *= right_factor
        
        return left_vol, right_vol
    
    def set_direction(self, angle, intensity=0.7):
        """촉각 자극의 방향 설정
        
        Parameters:
        -----------
        angle : float
            방향각 (0~359도, 0=정면, 90=오른쪽, 180=뒤, 270=왼쪽)
        intensity : float
            방향 강도 (0~1)
        """
        self.direction_angle = angle % 360
        self.direction_intensity = max(0.0, min(1.0, intensity))
        
        # 현재 재생 중이면 볼륨 즉시 갱신
        if self.is_playing:
            channel = self.channels[self.current_material]
            vol = channel.get_volume()
            left_vol, right_vol = self._apply_directional_panning(vol, vol)
            channel.set_volume(left_vol, right_vol)
    
    def set_material(self, material):
        """재질 변경"""
        if material not in self.sounds:
            # 재질별 사운드 생성
            if material == "metal":
                self.sounds[material] = self.generate_metal_haptic()
            elif material == "glass":
                self.sounds[material] = self.generate_glass_haptic()
            elif material == "wood":
                self.sounds[material] = self.generate_wood_haptic()
            elif material == "fabric":
                self.sounds[material] = self.generate_fabric_haptic()
            elif material == "silk":
                self.sounds[material] = self.generate_silk_haptic()
            else:
                print(f"알 수 없는 재질: {material}, 기본값 'metal'로 설정합니다.")
                material = "metal"
                self.sounds[material] = self.generate_metal_haptic()
            
        # 이미 같은 재질이면 무시
        if material == self.current_material:
            return
            
        # 현재 음량 저장
        current_volume = self.channels[self.current_material].get_volume() if self.is_playing else 0
        
        # 기존 재생 채널 페이드 아웃
        if self.is_playing:
            self.channels[self.current_material].fadeout(50)  # 50ms 페이드아웃
        
        # 재질 변경
        self.current_material = material
        print(f"재질 변경: {material}")
        
        # 새 재질의 소리 재생 (이전과 같은 볼륨으로)
        if current_volume > 0.01:
            self.channels[material].play(self.sounds[material], loops=-1)
            
            # 방향감 적용
            left_vol, right_vol = self._apply_directional_panning(current_volume, current_volume)
            self.channels[material].set_volume(left_vol, right_vol)
            
            self.is_playing = True
    
    def play(self):
        """사운드 반복 재생 시작"""
        if not self.is_playing:
            self.channels[self.current_material].play(self.sounds[self.current_material], loops=-1)
            self.is_playing = True
    
    def play_event(self, event_type):
        """이벤트 사운드 재생 (터치 시작, 종료 등)"""
        if event_type in self.event_sounds:
            # 현재 방향감 적용하여 이벤트 사운드 재생
            self.event_channel.play(self.event_sounds[event_type])
            
            # 방향감 적용
            vol = self.event_channel.get_volume()
            left_vol, right_vol = self._apply_directional_panning(vol, vol)
            self.event_channel.set_volume(left_vol, right_vol)
            
    def update_volume(self, volume):
        """볼륨 업데이트"""
        # 볼륨 범위 제한 (0-1)
        volume = max(0.0, min(1.0, volume))
        
        # 볼륨이 0에 가까우면 재생 중지
        if volume < 0.01:
            if self.is_playing:
                self.channels[self.current_material].fadeout(50)  # 50ms 페이드아웃
                self.is_playing = False
            return
        
        # 재생 중이 아니면 재생 시작
        if not self.is_playing:
            self.play()
        
        # 방향감 적용된 볼륨 계산
        left_vol, right_vol = self._apply_directional_panning(volume, volume)
        
        # 볼륨 설정 (채널당 최대 볼륨 0.8로 제한하여 과도한 소리 방지)
        self.channels[self.current_material].set_volume(
            min(0.8, left_vol), 
            min(0.8, right_vol)
        )
    
    def cleanup(self):
        """리소스 정리"""
        pygame.mixer.stop()
        pygame.mixer.quit()
