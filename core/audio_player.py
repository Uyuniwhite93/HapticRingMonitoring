import pygame
import numpy as np

class HapticAudioPlayer:
    def __init__(self):
        pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=256)
        
        self.current_volume = 0.0
        self.target_volume = 0.0
        self.is_playing = False
        self.current_material = "metal"
        
        self.direction_angle = 0
        self.direction_intensity = 0.0
        
        self.sounds = {}
        self.generate_all_materials()
        
        self.event_sounds = {}
        self.generate_event_sounds()
        
        self.channels = {material: pygame.mixer.Channel(i) for i, material in enumerate(self.sounds.keys())}
        self.event_channel = pygame.mixer.Channel(len(self.sounds))
        
    def generate_material_haptic(self, material, duration=1.0):
        sample_rate = 44100
        t = np.arange(0, duration, 1/sample_rate)
        
        material_params = {
            "metal": {
                "base_freq": 140,
                "base_amp": 0.35,
                "harmonics": [(1.5, 0.12), (2.2, 0.04)],
                "tick_freq": 9,
                "tick_amp": 0.25,
                "speed_tick_freq": 15,
                "speed_tick_amp": 0.2,
                "noise_amp": 0.045,
                "noise_filter": 12
            },
            "glass": {
                "base_freq": 120,
                "base_amp": 0.25,
                "harmonics": [(1.7, 0.04), (2.3, 0.02)],
                "tick_freq": 30,
                "tick_amp": 0.08,
                "speed_tick_freq": 0,
                "speed_tick_amp": 0,
                "noise_amp": 0.008,
                "noise_filter": 18
            },
            "wood": {
                "base_freq": 100,
                "base_amp": 0.3,
                "harmonics": [(1.4, 0.1), (2.0, 0.05)],
                "tick_freq": 12,
                "tick_amp": 0.2,
                "speed_tick_freq": 18,
                "speed_tick_amp": 0.18,
                "noise_amp": 0.08,
                "noise_filter": 8
            },
            "fabric": {
                "base_freq": 80,
                "base_amp": 0.35,
                "harmonics": [(1.5, 0.12), (2.1, 0.07)],
                "tick_freq": 15,
                "tick_amp": 0.18,
                "speed_tick_freq": 8,
                "speed_tick_amp": 0.12,
                "noise_amp": 0.08,
                "noise_filter": 8
            },
            "silk": {
                "base_freq": 55,
                "base_amp": 0.18,
                "harmonics": [(1.2, 0.05), (1.7, 0.01)],
                "tick_freq": 8,
                "tick_amp": 0.03,
                "speed_tick_freq": 0,
                "speed_tick_amp": 0,
                "noise_amp": 0.003,
                "noise_filter": 30
            }
        }
        
        params = material_params.get(material, material_params["metal"])
        
        base_freq = params["base_freq"]
        wave = params["base_amp"] * np.sin(2 * np.pi * base_freq * t)
        
        for harmonic_ratio, harmonic_amp in params["harmonics"]:
            wave += harmonic_amp * np.sin(2 * np.pi * base_freq * harmonic_ratio * t)
        
        if params["tick_freq"] > 0:
            tick_pattern = params["tick_amp"] * np.sin(2 * np.pi * params["tick_freq"] * t)
            tick_pattern = np.tanh(tick_pattern * 5.5) * 0.18
            wave += tick_pattern
        
        if params["speed_tick_freq"] > 0:
            speed_tick_pattern = params["speed_tick_amp"] * np.sin(2 * np.pi * params["speed_tick_freq"] * t)
            speed_tick_pattern = np.tanh(speed_tick_pattern * 6) * 0.15
            speed_mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.8 * t)
            wave += speed_tick_pattern * speed_mod
        
        if material == "wood":
            thump_freq = 4
            thump_pattern = 0.2 * np.sin(2 * np.pi * thump_freq * t)
            thump_pattern = np.tanh(thump_pattern * 2) * 0.12
            wave += thump_pattern
        elif material == "glass":
            friction_freq = 30
            friction_mod = 0.08 * np.sin(2 * np.pi * friction_freq * t)
            friction_mod = np.tanh(friction_mod * 2.5) * 0.06
            wave += friction_mod
            smooth_slide = 0.07 * np.sin(2 * np.pi * 2.5 * t + 0.2 * np.sin(2 * np.pi * 0.8 * t))
            wave += smooth_slide
        elif material == "fabric":
            micro_freq = 15
            micro_mod = 0.18 * np.sin(2 * np.pi * micro_freq * t)
            random_pattern = 0.12 * np.sin(2 * np.pi * 8 * t * (1 + 0.18 * np.sin(2 * np.pi * 0.4 * t)))
            wave = wave * (1.0 + 0.25 * micro_mod + 0.15 * random_pattern)
        elif material == "silk":
            flow_freq = 2.5
            flow = 0.04 * np.sin(2 * np.pi * flow_freq * t + 0.08 * np.sin(2 * np.pi * 0.2 * t))
            wave += flow
            texture_freq = 8
            texture_mod = 0.03 * np.sin(2 * np.pi * texture_freq * t)
            texture_mod = np.sin(texture_mod * np.pi/4) * 0.02
            wave += texture_mod
            mod_depth = 0.03
            mod_freq = 1.2
            modulation = 1.0 + mod_depth * np.sin(2 * np.pi * mod_freq * t)
            wave = wave * modulation
        
        noise = np.random.normal(0, params["noise_amp"], len(t))
        noise_envelope = np.exp(-params["noise_filter"] * np.abs(np.fft.rfftfreq(len(noise), 1/sample_rate) / (sample_rate/2)))
        filtered_noise = np.fft.irfft(np.fft.rfft(noise) * noise_envelope, len(noise))
        wave += filtered_noise
        
        return self._finalize_wave(wave, sample_rate, duration)
        
    def generate_all_materials(self):
        materials = ["metal", "glass", "wood", "fabric", "silk"]
        for material in materials:
            self.sounds[material] = self.generate_material_haptic(material)
        
    def _create_event_sound(self, duration, freq_params, decay_rate):
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = np.zeros_like(t)
        
        for freq, amp in freq_params:
            wave += amp * np.sin(2 * np.pi * freq * t) * np.exp(-decay_rate * t)
        
        fade_samples = int(sample_rate * 0.02)
        if len(wave) > fade_samples:
            wave[-fade_samples:] *= np.linspace(1, 0, fade_samples)
        
        wave = wave / np.max(np.abs(wave))
        return pygame.mixer.Sound(buffer=(wave * 32767).astype(np.int16))
    
    def generate_event_sounds(self):
        self.event_sounds["touch_start"] = self._create_event_sound(
            0.1, [(180, 0.9), (360, 0.4), (720, 0.2)], 40
        )
        self.event_sounds["touch_end"] = self._create_event_sound(
            0.08, [(140, 0.7), (70, 0.3)], 30
        )
        
        sample_rate = 44100
        t = np.linspace(0, 0.15, int(sample_rate * 0.15), False)
        freq_sweep = np.linspace(200, 600, len(t))
        phase = 2 * np.pi * np.cumsum(freq_sweep) / sample_rate
        wave = 0.8 * np.sin(phase) * np.exp(-15 * t)
        noise = np.random.normal(0, 0.3, len(t)) * np.exp(-20 * np.linspace(0, 1, len(t)))
        wave += noise + 0.4 * np.sin(2 * np.pi * 350 * t) * np.exp(-8 * t)
        
        fade_samples = int(sample_rate * 0.05)
        wave[-fade_samples:] *= np.linspace(1, 0, fade_samples)
        wave = wave / np.max(np.abs(wave))
        self.event_sounds["touch_exit"] = pygame.mixer.Sound(buffer=(wave * 32767).astype(np.int16))
        
    def _finalize_wave(self, wave, sample_rate, duration):
        fade_samples = int(0.01 * sample_rate)
        if fade_samples > 0:
            wave[:fade_samples] *= np.linspace(0, 1, fade_samples)
            wave[-fade_samples:] *= np.linspace(1, 0, fade_samples)
        
        t = np.arange(0, duration, 1/sample_rate)
        
        sa_component = 0.2 * np.sin(2 * np.pi * 12 * t)
        sa_adaptation = np.exp(-1.2 * np.linspace(0, 1, len(t))**0.8)
        sa_component = sa_component * (0.4 + 0.6 * sa_adaptation)
        
        ra_component = 0.25 * np.sin(2 * np.pi * 35 * t)
        ra_adaptation = np.exp(-5 * np.linspace(0, 1, len(t))**0.6)
        ra_component = ra_component * ra_adaptation
        
        enhanced_wave = wave + 0.35 * sa_component + 0.25 * ra_component
        enhanced_wave = enhanced_wave / np.max(np.abs(enhanced_wave))
        audio_data = (enhanced_wave * 32767).astype(np.int16)
        
        return pygame.mixer.Sound(buffer=audio_data)
    
    def _apply_directional_panning(self, volume):
        if self.direction_intensity > 0:
            angle_rad = np.radians(self.direction_angle)
            direction_factor = 0.5 + 0.5 * np.cos(angle_rad)
            volume *= (1.0 - self.direction_intensity * 0.5 + self.direction_intensity * direction_factor)
        return volume
    
    def set_direction(self, angle, intensity=0.7):
        self.direction_angle = angle % 360
        self.direction_intensity = max(0.0, min(1.0, intensity))
        if self.is_playing:
            channel = self.channels[self.current_material]
            vol = self._apply_directional_panning(channel.get_volume())
            channel.set_volume(vol)
    
    def set_material(self, material):
        if material not in self.sounds:
            print(f"알 수 없는 재질: {material}, 기본값 'metal'로 설정합니다.")
            material = "metal"
            
        if material == self.current_material:
            return
            
        current_volume = self.channels[self.current_material].get_volume() if self.is_playing else 0
        
        if self.is_playing:
            self.channels[self.current_material].fadeout(50)
        
        self.current_material = material
        print(f"재질 변경: {material}")
        
        if current_volume > 0.01:
            self.channels[material].play(self.sounds[material], loops=-1)
            vol = self._apply_directional_panning(current_volume)
            self.channels[material].set_volume(vol)
            self.is_playing = True
    
    def play(self):
        if not self.is_playing:
            self.channels[self.current_material].play(self.sounds[self.current_material], loops=-1)
            self.is_playing = True
    
    def play_event(self, event_type):
        if event_type in self.event_sounds:
            self.event_channel.play(self.event_sounds[event_type])
            vol = self._apply_directional_panning(self.event_channel.get_volume())
            self.event_channel.set_volume(vol)
            
    def update_volume(self, volume):
        volume = max(0.0, min(1.0, volume))
        
        if volume < 0.01:
            if self.is_playing:
                self.channels[self.current_material].fadeout(50)
                self.is_playing = False
            return
        
        if not self.is_playing:
            self.play()
        
        vol = self._apply_directional_panning(volume)
        self.channels[self.current_material].set_volume(min(0.8, vol))
    
    def cleanup(self):
        pygame.mixer.stop()
        pygame.mixer.quit()