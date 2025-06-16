import pygame
import sys
import numpy as np
import time
from collections import deque
import os

# 콘솔 창 숨기기 (Windows)
if sys.platform == "win32":
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

from izhikevich_neuron import IzhikevichNeuron
from spike_encoder import SpikeEncoder
from haptic_renderer import HapticRenderer
from audio_player import AudioPlayer

class AutomotiveDisplay:
    def __init__(self):
        pygame.init()
        
        # 화면 설정
        self.width = 1200
        self.height = 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Automotive Haptic Display")
        
        # 색상 정의 - 미니멀 automotive 스타일
        self.BLACK_GLASS = (8, 8, 12)         # 더 어두운 검은 유리 배경
        self.WHITE = (255, 255, 255)          # 흰색 텍스트/아이콘
        self.BLUE_ACTIVE = (100, 160, 255)    # 파란색 활성화
        self.ORANGE_ACTIVE = (255, 150, 70)   # 주황색 활성화
        self.GRAY_INACTIVE = (120, 120, 130)  # 비활성화 회색
        
        # 폰트 설정
        self.font_large = pygame.font.Font(None, 56)
        self.font_medium = pygame.font.Font(None, 42)
        self.font_small = pygame.font.Font(None, 32)
        
        # 재질 설정 (Glass로 고정)
        self.material_roughness = 0.3  # Glass 고정
        
        # 풍향 제어 시스템 (먼저 정의)
        self.wind_level = 3  # 기본 풍향 단계 (1~8)
        
        # 햅틱 시스템 초기화
        self.setup_haptic_system()
        
        # 간소화된 버튼들 (박스 없이 텍스트/아이콘만)
        self.buttons = self.create_minimal_buttons()
        
        # 마우스 상태
        self.mouse_pressed = False
        self.last_mouse_pos = (0, 0)
        self.last_mouse_time = time.perf_counter()
        self.mouse_speed = 0.0
        self.speed_history = deque(maxlen=10)
        self.avg_mouse_speed = 0.0
        
        # 버튼 hover 상태 추적
        self.hovered_button = None
        self.prev_hovered_button = None
        self.sa_hover_active = False  # SA hover 상태 추적
        
        # 설정
        self.max_speed_clamp = 100000.0
        self.mouse_stop_threshold = 0.02
        self.min_mouse_delta_time = 0.0001
        
        # 사운드 초기화
        self.init_sounds()
        
        # 시계
        self.clock = pygame.time.Clock()
        
    def setup_haptic_system(self):
        """햅틱 시스템 초기화"""
        # 먼저 renderer와 audio player 초기화
        self.haptic_renderer = HapticRenderer(44100)
        self.audio_player = AudioPlayer()
        
        # SA 뉴런 설정 (50Hz, 120ms, 0.15 amplitude)
        self.sa_sound = self.haptic_renderer.create_sound_object(50, 120, 0.15, fade_out_ms=10)
        
        # Spike Encoder 초기화
        sa_params = {'a': 0.03, 'b': 0.25, 'c': -65.0, 'd': 6.0, 'v_init': -70.0, 'init_a': 0.03}
        ra_params = {'base_a': 0.15, 'base_b': 0.25, 'base_c': -65.0, 'base_d': 1.5, 'v_init': -65.0, 'click_d_burst': 25.0}
        input_config = {
            'click_mag': 12.0, 'ra_scl_chg': 20.0, 'ra_scl_spd_dev': 0.02,
            'ra_clip_min': -30.0, 'ra_clip_max': 30.0, 'RA_SUSTAIN_DURATION': 5, 'ra_min_spd_for_input': 1.0
        }
        
        self.spike_encoder = SpikeEncoder(sa_params, ra_params, 1.0, input_config)
        
        # 뉴런 업데이트 타이머
        self.last_neuron_update = time.perf_counter()
        
    def init_sounds(self):
        """사운드 초기화 - Glass 재질로 고정"""
        # SA 사운드 (클릭용)
        self.sa_sound = self.haptic_renderer.create_sound_object(50, 120, 0.15, fade_out_ms=10)
        
        # RA 사운드 (Glass 재질로 고정)
        glass_freq = int(80 * 1.0)  # Glass 재질 주파수
        self.ra_sound = self.haptic_renderer.create_sound_object(
            glass_freq, 100, 0.6, fade_out_ms=10
        )
        
        # 버튼 hover용 강한 burst 사운드
        self.button_hover_sound = self.haptic_renderer.create_sound_object(
            120, 80, 0.4, fade_out_ms=5  # 짧고 강한 사운드
        )
    
    def create_minimal_buttons(self):
        """간소화된 버튼들 생성 (박스 없이 텍스트/아이콘만)"""
        buttons = []
        
        # 중앙 정렬된 간소화된 버튼들 (세로도 중앙)
        center_x = self.width // 2
        center_y = self.height // 2
        
        # 상단 줄 - 기후 제어 (중앙에서 위로)
        top_y = center_y - 80
        spacing = 180
        
        climate_buttons = [
            {"name": "AC", "text": "A/C", "x": center_x - spacing, "active": True, "color": "blue"},
            {"name": "Circulation", "text": "AIR\nCIRC", "x": center_x, "active": False},
            {"name": "Heat", "text": "HEAT", "x": center_x + spacing, "active": False},
        ]
        
        for btn in climate_buttons:
            btn.update({
                "y": top_y,
                "rect": pygame.Rect(btn["x"] - 30, top_y - 25, 60, 50)
            })
            buttons.append(btn)
        
        # 하단 줄 - 차량 제어 (중앙에서 아래로)
        bottom_y = center_y + 80
        
        vehicle_buttons = [
            {"name": "Recirculate", "text": "RECIRC", "x": center_x - spacing, "active": True, "color": "orange"},
            {"name": "Auto", "text": "AUTO", "x": center_x, "active": False},
            {"name": "Defrost", "text": "DEFROST", "x": center_x + spacing, "active": False},
        ]
        
        for btn in vehicle_buttons:
            btn.update({
                "y": bottom_y,
                "rect": pygame.Rect(btn["x"] - 30, bottom_y - 25, 60, 50)
            })
            buttons.append(btn)
        
        # 풍향 제어 시스템 - 맨 아래
        wind_y = center_y + 160
        wind_spacing = 80
        
        # 풍향 감소 버튼
        buttons.append({
            "name": "WindDown", "text": "-", "x": center_x - wind_spacing * 1.5,
            "y": wind_y, "active": False,
            "rect": pygame.Rect(center_x - wind_spacing * 1.5 - 25, wind_y - 20, 50, 40)
        })
        
        # 풍향 단계 표시 (세로 바 형태)
        for i in range(8):
            step_x = center_x - wind_spacing + (i * 20)
            is_active = i < self.wind_level  # 현재 단계까지 활성화
            bar_height = 8 + (i * 4)  # 점점 커지는 바 높이
            buttons.append({
                "name": f"WindStep{i+1}", "bar_height": bar_height, "x": step_x,
                "y": wind_y, "active": is_active, "color": "blue" if is_active else None,
                "rect": pygame.Rect(step_x - 6, wind_y - bar_height//2, 12, bar_height), 
                "wind_step": True, "wind_bar": True
            })
        
        # 풍향 증가 버튼
        buttons.append({
            "name": "WindUp", "text": "+", "x": center_x + wind_spacing * 1.5,
            "y": wind_y, "active": False,
            "rect": pygame.Rect(center_x + wind_spacing * 1.5 - 25, wind_y - 20, 50, 40)
        })
            
        return buttons
    
    def draw_floating_element(self, button):
        """떠있는 버튼 그리기 (박스 없이 깔끔하게)"""
        x = button["x"]
        y = button["y"]
        
        # 활성 상태에 따른 색상
        if button.get("active"):
            if button.get("color") == "blue":
                color = self.BLUE_ACTIVE
            elif button.get("color") == "orange":
                color = (255, 140, 0)
            else:
                color = self.WHITE
        else:
            color = self.GRAY_INACTIVE
        
        # 풍향 바 (세로로 점점 커지는)
        if button.get("wind_bar"):
            bar_height = button.get("bar_height", 20)
            bar_width = 8
            
            # 바 배경 (어두운 테두리)
            bar_rect = pygame.Rect(x - bar_width//2, y - bar_height//2, bar_width, bar_height)
            pygame.draw.rect(self.screen, (40, 40, 40), bar_rect)
            
            # 활성화된 바 (밝은 색상)
            if button.get("active"):
                pygame.draw.rect(self.screen, color, bar_rect)
            
            # 테두리
            pygame.draw.rect(self.screen, color if button.get("active") else (80, 80, 80), bar_rect, 1)
        else:
            # 일반 버튼들 - 텍스트만
            if button.get("text"):
                if '\n' in button["text"]:
                    # 여러 줄 텍스트 처리
                    lines = button["text"].split('\n')
                    total_height = len(lines) * 18
                    start_y = y - total_height // 2
                    for i, line in enumerate(lines):
                        line_surface = self.font_small.render(line, True, color)
                        line_rect = line_surface.get_rect(center=(x, start_y + i * 18))
                        self.screen.blit(line_surface, line_rect)
                else:
                    # 한 줄 텍스트
                    text_surface = self.font_medium.render(button["text"], True, color)
                    text_rect = text_surface.get_rect(center=(x, y))
                    self.screen.blit(text_surface, text_rect)
    
    def handle_click(self, pos):
        """버튼 클릭 처리"""
        for button in self.buttons:
            if button["rect"].collidepoint(pos):
                # 풍향 제어 버튼 처리
                if button["name"] == "WindDown":
                    if self.wind_level > 1:
                        self.wind_level -= 1
                        self.update_wind_display()
                        self.trigger_wind_decrease_feedback()
                        print(f"🌪 WIND DOWN → Level {self.wind_level}")
                elif button["name"] == "WindUp":
                    if self.wind_level < 8:
                        self.wind_level += 1
                        self.update_wind_display()
                        self.trigger_wind_increase_feedback()
                        print(f"🌪 WIND UP → Level {self.wind_level}")
                elif button.get("wind_step"):
                    # 풍향 단계 직접 클릭
                    step_num = int(button["name"][-1])  # WindStep1 -> 1
                    old_level = self.wind_level
                    self.wind_level = step_num
                    self.update_wind_display()
                    if step_num > old_level:
                        self.trigger_wind_increase_feedback()
                    else:
                        self.trigger_wind_decrease_feedback()
                    print(f"🌪 WIND SET → Level {self.wind_level}")
                else:
                    # 일반 버튼 토글 - 버튼 상태에 따른 SA 강도
                    button["active"] = not button["active"]
                    
                    # 버튼 상태에 따른 클릭 SA 강도
                    if button["active"]:
                        click_sa = 30.0
                        print(f"🔵 {button['name']} ACTIVATED: {click_sa}A")
                    else:
                        click_sa = 20.0
                        print(f"⚪ {button['name']} DEACTIVATED: {click_sa}A")
                    
                    self.spike_encoder.update_sa_input(click_sa)
                
                return button
        
        # 버튼이 아닌 배경 클릭 시 - SA 입력 없음 (main.py와 동일)
        print("🔘 BACKGROUND CLICK - No haptic")
        return None
    
    def trigger_strong_sa_feedback(self):
        """버튼 클릭 시 강한 SA 피드백"""
        self.spike_encoder.update_sa_input(25.0)  # 더 강한 전류
        if self.sa_sound:
            # 더 큰 볼륨과 더 깊은 사운드
            strong_sa_sound = self.haptic_renderer.create_sound_object(40, 150, 0.25, fade_out_ms=15)
            self.audio_player.play_sound(strong_sa_sound, channel_id=0, volume=1.0)
        
        # SA 입력을 빠르게 리셋
        pygame.time.set_timer(pygame.USEREVENT + 1, 100)  # 100ms 후 리셋
    
    def trigger_weak_sa_feedback(self):
        """배경 클릭 시 약한 SA 피드백"""
        self.spike_encoder.update_sa_input(8.0)  # 약한 전류
        if self.sa_sound:
            # 작은 볼륨과 짧은 사운드
            weak_sa_sound = self.haptic_renderer.create_sound_object(60, 80, 0.1, fade_out_ms=5)
            self.audio_player.play_sound(weak_sa_sound, channel_id=0, volume=0.5)
        
        # SA 입력을 빠르게 리셋
        pygame.time.set_timer(pygame.USEREVENT + 2, 50)  # 50ms 후 리셋
    
    def handle_mouse_move(self, pos):
        """마우스 이동 처리 - 완전한 SA 제어"""
        # 현재 시간
        current_time = time.perf_counter()
        
        # 버튼 hover 상태 확인
        self.prev_hovered_button = self.hovered_button
        self.hovered_button = None
        
        for button in self.buttons:
            if button["rect"].collidepoint(pos):
                self.hovered_button = button
                break
        
        # 버튼 진입/이탈 감지
        if self.hovered_button != self.prev_hovered_button:
            if self.hovered_button:
                # 새 버튼 진입
                self.trigger_button_enter_burst()
                self.start_sa_hover()
                print(f"🔵 ENTERED: {self.hovered_button['name']}")
            elif self.prev_hovered_button:
                # 버튼 이탈 - SA 완전 리셋
                self.trigger_button_exit_burst()
                self.stop_sa_hover()
                self.spike_encoder.update_sa_input(0.0)  # 확실한 리셋
                print(f"🔴 EXITED: {self.prev_hovered_button['name']}")
        
        # 마우스 속도 계산 (RA 비활성화)
        if self.last_mouse_pos:
            dx = pos[0] - self.last_mouse_pos[0]
            dy = pos[1] - self.last_mouse_pos[1]
            distance = np.sqrt(dx**2 + dy**2)
            dt = current_time - self.last_mouse_time
            
            if dt > self.min_mouse_delta_time:
                self.mouse_speed = distance / dt
                self.speed_history.append(self.mouse_speed)
                self.avg_mouse_speed = np.mean(self.speed_history)
                
                self.last_mouse_pos = pos
                self.last_mouse_time = current_time
    
    def trigger_button_enter_burst(self):
        """버튼 진입 시 강한 SA burst"""
        self.spike_encoder.update_sa_input(30.0)
        enter_sound = self.haptic_renderer.create_sound_object(120, 60, 0.45, fade_out_ms=5)
        if enter_sound:
            self.audio_player.play_sound(enter_sound, channel_id=1, volume=1.0)
        
        pygame.time.set_timer(pygame.USEREVENT + 3, 60)
    
    def trigger_button_exit_burst(self):
        """버튼 이탈 시 강한 SA burst"""
        self.spike_encoder.update_sa_input(25.0)
        exit_sound = self.haptic_renderer.create_sound_object(100, 60, 0.4, fade_out_ms=5)
        if exit_sound:
            self.audio_player.play_sound(exit_sound, channel_id=1, volume=0.9)
        
        pygame.time.set_timer(pygame.USEREVENT + 4, 50)
    
    def trigger_button_click_ra_burst(self):
        """버튼 클릭 시 강력한 RA burst"""
        # 강력한 RA burst를 위한 특별한 RA 활성화
        ra_fired, _, _, ra_vu = self.spike_encoder.step(
            mouse_speed=8000.0,      # 매우 높은 속도로 RA 트리거
            avg_mouse_speed=8000.0,
            material_roughness=1.5,   # 거친 재질로 강한 RA
            mouse_pressed=True
        )
        
        if ra_fired:
            # 강력한 RA 사운드 생성
            ra_burst_sound = self.haptic_renderer.create_sound_object(180, 80, 0.8, fade_out_ms=5)
            if ra_burst_sound:
                self.audio_player.play_sound(ra_burst_sound, channel_id=2, volume=1.0)
            print(f"💥 STRONG RA BURST: Click feedback")
    
    def trigger_button_release_ra_burst(self):
        """버튼 해제 시 강력한 RA burst"""
        # 버튼 해제용 RA burst (클릭보다 약간 약함)
        ra_fired, _, _, ra_vu = self.spike_encoder.step(
            mouse_speed=6000.0,      # 높은 속도
            avg_mouse_speed=6000.0,
            material_roughness=1.2,   # 거친 재질
            mouse_pressed=True
        )
        
        if ra_fired:
            # RA 해제 사운드
            ra_release_sound = self.haptic_renderer.create_sound_object(150, 60, 0.6, fade_out_ms=8)
            if ra_release_sound:
                self.audio_player.play_sound(ra_release_sound, channel_id=2, volume=0.8)
            print(f"💫 RA BURST: Release feedback")
    
    def start_sa_hover(self):
        """버튼 hover 시 SA 지속 시작 - 버튼 상태별 차별화"""
        self.sa_hover_active = True
        
        # 버튼 활성 상태에 따른 SA 강도 차별화
        if self.hovered_button.get("active"):
            sa_current = 25.0
            status = "ON (웅웅웅!!)"
        else:
            sa_current = 15.0
            status = "OFF (웅..웅..웅)"
        
        self.spike_encoder.update_sa_input(sa_current)
        print(f"🎯 HOVER {status}: {sa_current}A")
    
    def stop_sa_hover(self):
        """버튼 hover SA 지속 중지"""
        self.sa_hover_active = False
        self.spike_encoder.update_sa_input(0.0)
        print(f"⏹️  HOVER STOPPED: 0.0A")
    
    def update_haptic_system(self):
        """햅틱 시스템 업데이트 - SA만 활성화, RA 완전 비활성화"""
        # SA hover 상태 지속 (버튼 상태별 차별화)
        if self.sa_hover_active and self.hovered_button:
            if self.hovered_button.get("active"):
                base_sa = 25.0
                click_sa = 35.0
            else:
                base_sa = 15.0
                click_sa = 22.0
            
            current_sa = click_sa if self.mouse_pressed else base_sa
            self.spike_encoder.update_sa_input(current_sa)
        elif not self.hovered_button:
            # 버튼 밖에 있으면 SA 완전 중지
            self.spike_encoder.update_sa_input(0.0)
        
        # 뉴런 시뮬레이션 (RA 비활성화)
        sa_fired, ra_fired, sa_vu, ra_vu = self.spike_encoder.step(
            mouse_speed=0.0,  # RA 비활성화
            avg_mouse_speed=0.0,  # RA 비활성화
            material_roughness=0.0,  # RA 비활성화
            mouse_pressed=False  # RA 비활성화
        )
        
        # SA spike만 처리 (RA 무시)
        if sa_fired:
            context = self.get_current_context()
            packet = self.encode_spike_packet('SA', sa_vu[0], context)
            self.decode_spike_packet_to_haptic(packet)
    
    def draw_hud(self):
        """HUD 정보 표시"""
        # 제목
        title = self.font_large.render("Automotive Button Explorer", True, self.WHITE)
        self.screen.blit(title, (50, 50))
        
        # 현재 hover 상태
        if self.hovered_button:
            hover_info = f"Hovering: {self.hovered_button['name']}"
            hover_color = self.BLUE_ACTIVE
        else:
            hover_info = "Hovering: None"
            hover_color = self.GRAY_INACTIVE
            
        hover_text = self.font_small.render(hover_info, True, hover_color)
        self.screen.blit(hover_text, (50, 100))
        
        # 풍향 단계 정보
        wind_info = f"Wind Level: {self.wind_level}/8"
        wind_color = self.BLUE_ACTIVE if self.wind_level > 0 else self.GRAY_INACTIVE
        wind_text = self.font_small.render(wind_info, True, wind_color)
        self.screen.blit(wind_text, (50, 130))
        
        # 하단 안내
        instruction = self.font_small.render("Move mouse to explore • Feel burst on button entry/exit • Wind level affects vibration intensity", True, self.GRAY_INACTIVE)
        self.screen.blit(instruction, (50, self.height - 50))
    
    def draw_glass_background(self):
        """고급스러운 유리 효과 배경"""
        # 기본 별빛 효과
        for i in range(50):
            x = (i * 137) % self.width
            y = (i * 211) % self.height
            alpha = 30 + (i % 30)
            color = (alpha//3, alpha//3, alpha//2)
            pygame.draw.circle(self.screen, color, (x, y), 1)
        
        # 유리 반사 효과 - 대각선 그라데이션
        for i in range(0, self.width, 8):
            for j in range(0, self.height, 8):
                # 거리에 따른 반사 강도
                distance_factor = ((i + j) / (self.width + self.height)) * 2
                if distance_factor > 1:
                    distance_factor = 2 - distance_factor
                
                alpha = int(15 * distance_factor)
                if alpha > 0:
                    color = (alpha + 5, alpha + 8, alpha + 12)  # 약간의 블루 틴트
                    pygame.draw.circle(self.screen, color, (i, j), 1)
        
        # 미묘한 수직 반사선들
        for x in range(0, self.width, 120):
            for y in range(0, self.height, 3):
                alpha = int(8 + 4 * np.sin(y * 0.01))
                if alpha > 0:
                    color = (alpha, alpha, alpha + 3)
                    pygame.draw.circle(self.screen, color, (x, y), 1)
    
    def update_wind_display(self):
        """풍향 단계 표시 업데이트"""
        for button in self.buttons:
            if button.get("wind_step"):
                step_num = int(button["name"][-1])
                button["active"] = step_num <= self.wind_level
                button["color"] = "blue" if button["active"] else None
                
                # 바 높이 재계산 (rect도 업데이트)
                bar_height = 8 + ((step_num - 1) * 4)  # 8, 12, 16, 20, 24, 28, 32, 36
                button["bar_height"] = bar_height
                button["rect"] = pygame.Rect(button["x"] - 6, button["y"] - bar_height//2, 12, bar_height)
    
    def trigger_wind_increase_feedback(self):
        """풍향 증가 시 강화된 SA 입력"""
        base_current = 20.0
        wind_multiplier = 1.0 + (self.wind_level - 1) * 0.5
        final_current = base_current * wind_multiplier
        
        self.spike_encoder.update_sa_input(final_current)
        
        reset_time = 30 + (self.wind_level * 12)
        pygame.time.set_timer(pygame.USEREVENT + 6, reset_time)
    
    def trigger_wind_decrease_feedback(self):
        """풍향 감소 시 강화된 SA 입력"""
        base_current = 18.0
        wind_multiplier = 1.0 + (self.wind_level - 1) * 0.4
        final_current = base_current * wind_multiplier
        
        self.spike_encoder.update_sa_input(final_current)
        
        reset_time = 35 + (self.wind_level * 10)
        pygame.time.set_timer(pygame.USEREVENT + 7, reset_time)
    
    def encode_spike_packet(self, spike_type, voltage, context_info):
        """spike 정보를 무선 전송용 패킷으로 인코딩"""
        packet = {
            'type': spike_type,
            'voltage': voltage,
            'timestamp': time.perf_counter(),
            'context': context_info
        }
        # 무선 패킷 출력 제거 (너무 많음)
        return packet
    
    def decode_spike_packet_to_haptic(self, packet):
        """무선 수신한 spike 패킷을 디코딩하여 햅틱 신호 생성"""
        voltage = packet['voltage'] 
        context = packet['context']
        
        if packet['type'] == 'SA':
            # SA spike 디코딩
            if voltage > -35:
                haptic_intensity = "VERY_STRONG"
                volume = 1.0
            elif voltage > -45:
                haptic_intensity = "STRONG" 
                volume = 0.9
            elif voltage > -55:
                haptic_intensity = "MEDIUM"
                volume = 0.7
            else:
                haptic_intensity = "WEAK"
                volume = 0.5
            
            # 햅틱 신호 생성
            if self.sa_sound:
                self.audio_player.play_sound(self.sa_sound, channel_id=0, volume=volume)
            
            # 중요한 이벤트만 출력
            button_name = context.get('hovered_button', 'None')
            button_active = context.get('button_active', False)
            state = "ON" if button_active else "OFF"
            print(f"⚡ {haptic_intensity} haptic: {button_name}({state}) V={voltage:.1f}")
    
    def get_current_context(self):
        """현재 상황의 컨텍스트 정보 생성"""
        context = {
            'hovered_button': self.hovered_button['name'] if self.hovered_button else None,
            'button_active': self.hovered_button.get('active') if self.hovered_button else None,
            'wind_level': self.wind_level,
            'mouse_pressed': self.mouse_pressed
        }
        return context
    
    def run(self):
        """메인 실행 루프"""
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # 왼쪽 클릭
                        self.mouse_pressed = True
                        self.last_mouse_pos = event.pos
                        self.last_mouse_time = time.perf_counter()
                        self.mouse_speed = 0.0
                        self.speed_history.clear()
                        self.avg_mouse_speed = 0.0
                        
                        # 클릭 처리
                        clicked_button = self.handle_click(event.pos)
                        
                        # 버튼 클릭 시 강력한 RA burst
                        if clicked_button:
                            self.trigger_button_click_ra_burst()
                            
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.mouse_pressed = False
                        self.mouse_speed = 0.0
                        
                        # 버튼 해제 시 RA burst
                        if self.hovered_button:
                            self.trigger_button_release_ra_burst()
                            # 버튼 위에 있으면 hover SA로 복귀
                            self.start_sa_hover()
                        else:
                            # 버튼 밖이면 SA 완전 중지
                            self.spike_encoder.update_sa_input(0.0)
                elif event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_move(event.pos)
                elif event.type == pygame.USEREVENT + 1:
                    # 강한 SA 입력 리셋
                    self.spike_encoder.update_sa_input(0.0)
                    pygame.time.set_timer(pygame.USEREVENT + 1, 0)  # 타이머 비활성화
                elif event.type == pygame.USEREVENT + 2:
                    # 약한 SA 입력 리셋
                    self.spike_encoder.update_sa_input(0.0)
                    pygame.time.set_timer(pygame.USEREVENT + 2, 0)  # 타이머 비활성화
                elif event.type == pygame.USEREVENT + 3:
                    # 강한 burst 리셋
                    self.spike_encoder.update_sa_input(0.0)
                    pygame.time.set_timer(pygame.USEREVENT + 3, 0)  # 타이머 비활성화
                elif event.type == pygame.USEREVENT + 4:
                    # 강한 burst 리셋
                    self.spike_encoder.update_sa_input(0.0)
                    pygame.time.set_timer(pygame.USEREVENT + 4, 0)  # 타이머 비활성화
                elif event.type == pygame.USEREVENT + 6:
                    # 풍향 증가 피드백 리셋
                    self.spike_encoder.update_sa_input(0.0)
                    pygame.time.set_timer(pygame.USEREVENT + 6, 0)  # 타이머 비활성화
                elif event.type == pygame.USEREVENT + 7:
                    # 풍향 감소 피드백 리셋
                    self.spike_encoder.update_sa_input(0.0)
                    pygame.time.set_timer(pygame.USEREVENT + 7, 0)  # 타이머 비활성화
            
            # 햅틱 시스템 업데이트
            self.update_haptic_system()
            
            # 화면 그리기
            self.screen.fill(self.BLACK_GLASS)
            self.draw_glass_background()
            
            # 떠있는 버튼들 그리기
            for button in self.buttons:
                self.draw_floating_element(button)
            
            # HUD 그리기
            self.draw_hud()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        # 정리
        self.audio_player.quit()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    display = AutomotiveDisplay()
    display.run() 