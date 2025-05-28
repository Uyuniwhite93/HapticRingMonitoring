import pygame
import numpy as np

class HapticAudioPlayer:
    def __init__(self):
        pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=256)

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
                "base_freq": 140, "base_amp": 0.35, "harmonics": [(1.5, 0.12), (2.2, 0.04)],
                "tick_freq": 9, "tick_amp": 0.25,
                "speed_tick_freq": 15, "speed_tick_amp": 0.2,
                "noise_amp": 0.045, "noise_filter": 12
            },
            "glass": {
                "base_freq": 120, "base_amp": 0.25, "harmonics": [(1.7, 0.04), (2.3, 0.02)],
                "tick_freq": 30, "tick_amp": 0.08,
                "speed_tick_freq": 0, "speed_tick_amp": 0,
                "noise_amp": 0.008, "noise_filter": 18
            },
            "wood": {
                "base_freq": 100, "base_amp": 0.3, "harmonics": [(1.4, 0.1), (2.0, 0.05)],
                "tick_freq": 12, "tick_amp": 0.2,
                "speed_tick_freq": 18, "speed_tick_amp": 0.18,
                "noise_amp": 0.08, "noise_filter": 8
            },
            "fabric": {
                "base_freq": 80, "base_amp": 0.35, "harmonics": [(1.5, 0.12), (2.1, 0.07)],
                "tick_freq": 15, "tick_amp": 0.18,
                "speed_tick_freq": 8, "speed_tick_amp": 0.12,
                "noise_amp": 0.08, "noise_filter": 8
            },
            "silk": {
                "base_freq": 55, "base_amp": 0.18, "harmonics": [(1.2, 0.05), (1.7, 0.01)],
                "tick_freq": 8, "tick_amp": 0.03,
                "speed_tick_freq": 0, "speed_tick_amp": 0,
                "noise_amp": 0.003, "noise_filter": 30
            }
        }

        params = material_params.get(material, material_params["metal"])

        wave = params["base_amp"] * np.sin(2 * np.pi * params["base_freq"] * t)
        for harmonic_ratio, harmonic_amp in params["harmonics"]:
            wave += harmonic_amp * np.sin(2 * np.pi * params["base_freq"] * harmonic_ratio * t)

        if params["tick_freq"] > 0:
            tick = params["tick_amp"] * np.sin(2 * np.pi * params["tick_freq"] * t)
            wave += np.tanh(tick * 5.5) * 0.18

        if params["speed_tick_freq"] > 0:
            speed_tick = params["speed_tick_amp"] * np.sin(2 * np.pi * params["speed_tick_freq"] * t)
            speed_tick = np.tanh(speed_tick * 6) * 0.15
            speed_mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.8 * t)
            wave += speed_tick * speed_mod

        noise = np.random.normal(0, params["noise_amp"], len(t))
        noise_envelope = np.exp(-params["noise_filter"] * np.abs(np.fft.rfftfreq(len(noise), 1/sample_rate) / (sample_rate/2)))
        filtered_noise = np.fft.irfft(np.fft.rfft(noise) * noise_envelope, len(noise))
        wave += filtered_noise

        wave = wave / np.max(np.abs(wave))
        return pygame.mixer.Sound(buffer=(wave * 32767).astype(np.int16))

    def generate_all_materials(self):
        for material in ["metal", "glass", "wood", "fabric", "silk"]:
            self.sounds[material] = self.generate_material_haptic(material)

    def _create_event_sound(self, duration, freq_params, decay_rate):
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = sum(amp * np.sin(2 * np.pi * freq * t) * np.exp(-decay_rate * t) for freq, amp in freq_params)
        wave[-int(sample_rate * 0.02):] *= np.linspace(1, 0, int(sample_rate * 0.02))
        wave = wave / np.max(np.abs(wave))
        return pygame.mixer.Sound(buffer=(wave * 32767).astype(np.int16))

    def generate_event_sounds(self):
        self.event_sounds["touch_start"] = self._create_event_sound(0.1, [(180, 0.9), (360, 0.4), (720, 0.2)], 40)
        self.event_sounds["touch_end"] = self._create_event_sound(0.08, [(140, 0.7), (70, 0.3)], 30)

        sample_rate = 44100
        t = np.linspace(0, 0.15, int(sample_rate * 0.15), False)
        freq_sweep = np.linspace(200, 600, len(t))
        phase = 2 * np.pi * np.cumsum(freq_sweep) / sample_rate
        wave = 0.8 * np.sin(phase) * np.exp(-15 * t)
        wave += np.random.normal(0, 0.3, len(t)) * np.exp(-20 * np.linspace(0, 1, len(t)))
        wave += 0.4 * np.sin(2 * np.pi * 350 * t) * np.exp(-8 * t)
        wave[-int(sample_rate * 0.05):] *= np.linspace(1, 0, int(sample_rate * 0.05))
        wave = wave / np.max(np.abs(wave))
        self.event_sounds["touch_exit"] = pygame.mixer.Sound(buffer=(wave * 32767).astype(np.int16))

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
            ch = self.channels[self.current_material]
            ch.set_volume(self._apply_directional_panning(ch.get_volume()))

    def set_material(self, material):
        if material not in self.sounds:
            material = "metal"
        if material == self.current_material:
            return
        if self.is_playing:
            self.channels[self.current_material].fadeout(50)
        self.current_material = material
        ch = self.channels[material]
        ch.play(self.sounds[material], loops=-1)
        ch.set_volume(self._apply_directional_panning(0.5))
        self.is_playing = True

    def play(self):
        if not self.is_playing:
            ch = self.channels[self.current_material]
            ch.play(self.sounds[self.current_material], loops=-1)
            self.is_playing = True

    def play_event(self, event_type):
        if event_type in self.event_sounds:
            ch = self.event_channel
            ch.play(self.event_sounds[event_type])
            ch.set_volume(self._apply_directional_panning(ch.get_volume()))

    def update_volume(self, volume):
        volume = max(0.0, min(1.0, volume))
        if volume < 0.01:
            if self.is_playing:
                self.channels[self.current_material].fadeout(50)
                self.is_playing = False
            return
        if not self.is_playing:
            self.play()
        self.channels[self.current_material].set_volume(min(0.8, self._apply_directional_panning(volume)))

    def cleanup(self):
        pygame.mixer.stop()
        pygame.mixer.quit()
