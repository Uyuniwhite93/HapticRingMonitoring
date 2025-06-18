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
        self.width = 1400
        self.height = 800
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Automotive Haptic Interface")
        
        # 색상 정의 - 미니멀 automotive 스타일
        self.BLACK_GLASS = (8, 8, 12)         # 어두운 배경
        self.WHITE = (255, 255, 255)          # 흰색 텍스트/아이콘
        self.BLUE_ACTIVE = (100, 160, 255)    # 파란색 활성화
        self.ORANGE_ACTIVE = (255, 150, 70)   # 주황색 활성화
        self.GRAY_INACTIVE = (120, 120, 130)  # 비활성화 회색
        self.GREEN_ACTIVE = (100, 255, 100)   # 초록색 활성화
        
        # 폰트 설정
        self.font_large = pygame.font.Font(None, 56)
        self.font_medium = pygame.font.Font(None, 42)
        self.font_small = pygame.font.Font(None, 32)
        self.font_tiny = pygame.font.Font(None, 24)
        
        # 햅틱 시스템 초기화 (플라스틱 재질 고정)
        self.setup_haptic_system()
        
        # 플라스틱 재질 고정
        self.material_roughness = 0.4  # 플라스틱 거칠기
        self.material_name = "Plastic"
        
        # 사운드 초기화
        self.init_sounds()
        
        # 자동차 버튼들 생성 (아이콘 형태)
        self.buttons = self.create_automotive_buttons()
        
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
        self.hover_start_time = 0.0
        
        # 설정
        self.max_speed_clamp = 100000.0
        self.mouse_stop_threshold = 0.02
        self.min_mouse_delta_time = 0.0001
        
        # 시계
        self.clock = pygame.time.Clock()
        
    def setup_haptic_system(self):
        """햅틱 시스템 초기화 - 플라스틱 재질 고정"""
        self.haptic_renderer = HapticRenderer(44100)
        self.audio_player = AudioPlayer()
        
        # main.py와 동일한 뉴런 파라미터
        sa_params = {
            'a': 0.05, 'b': 0.25, 'c': -65.0, 'd': 6.0, 
            'v_init': -70.0, 'init_a': 0.05
        }
        ra_params = {
            'base_a': 0.4, 'base_b': 0.25, 'base_c': -65.0, 'base_d': 1.5, 
            'v_init': -65.0
        }
        ra_click_params = {
            'a': 0.3, 'b': 0.25, 'c': -65.0, 'd': 6.0, 'v_init': -65.0
        }
        
        # main.py와 동일한 입력 설정
        input_config = {
            'click_mag': 12.0,
            'ra_click_scl_chg': 25.0,
            'RA_CLICK_SUSTAIN_DURATION': 3,
            'ra_motion_scl_spd_dev': 0.02,
            'ra_min_spd_for_input': 1.0,
            'ra_click_clip_min': -40.0,
            'ra_click_clip_max': 40.0,
            'ra_motion_clip_min': -30.0,
            'ra_motion_clip_max': 30.0,
        }
        
        self.spike_encoder = SpikeEncoder(
            sa_params=sa_params,
            ra_params=ra_params,
            ra_click_params=ra_click_params,
            neuron_dt_ms=1.0,
            input_config=input_config
        )
        
        # main.py와 동일한 사운드 설정 - 세기 대폭 증가
        self.sound_config = {
            'sa_hz': 25, 'sa_ms': 120, 'sa_amp': 0.6, 'sa_sound_volume': 1.8,  # 진폭/볼륨 대폭 증가
            'ra_motion_base_hz': 35, 'ra_motion_ms': 90, 'ra_motion_base_amp': 1.2,  # 진폭 대폭 증가
            'ra_motion_vol_min_spd': 100.0, 'ra_motion_vol_max_spd': 5000.0,
            'ra_motion_min_vol_scl': 1.0, 'ra_motion_max_vol_scl': 2.0,  # 볼륨 범위 대폭 증가
            'ra_click_hz': 50, 'ra_click_ms': 70, 'ra_click_amp': 1.3, 'ra_click_volume': 1.6  # 진폭/볼륨 대폭 증가
        }
        
    def init_sounds(self):
        """사운드 초기화 - 플라스틱 재질 고정"""
        snd_cfg = self.sound_config
        
        # SA 뉴런 사운드 (압력 피드백)
        self.sa_sound = self.haptic_renderer.create_sound_object(
            snd_cfg['sa_hz'], snd_cfg['sa_ms'], snd_cfg['sa_amp'], fade_out_ms=10
        )
        
        # 플라스틱 재질 고정 파라미터
        plastic_params = {'hardness': 1.1}
        plastic_f = 1.0  # 플라스틱 주파수 계수
        
        # RA 움직임 뉴런 사운드 (플라스틱 특화)
        ra_motion_hz = int(snd_cfg['ra_motion_base_hz'] * plastic_f)  # 35Hz
        self.ra_motion_sound = self.haptic_renderer.create_material_sound(
            'plastic', ra_motion_hz, snd_cfg['ra_motion_ms'], snd_cfg['ra_motion_base_amp'], 
            fade_out_ms=10, **plastic_params
        )
        
        # RA 클릭 뉴런 사운드 (플라스틱 특화)
        ra_click_hz = int(snd_cfg['ra_click_hz'] * plastic_f)  # 50Hz
        click_amp = snd_cfg['ra_click_amp'] * 1.2
        self.ra_click_sound = self.haptic_renderer.create_material_sound(
            'plastic', ra_click_hz, snd_cfg['ra_click_ms'], click_amp, 
            fade_out_ms=5, **plastic_params
        )
        
        # 버튼 호버링용 특별한 RA 사운드 - 강도 최대로 증가
        self.ra_hover_sound = self.haptic_renderer.create_material_sound(
            'plastic', 80, 60, 2.0, fade_out_ms=3, **plastic_params  # 진폭 1.4 → 2.0 (최대)
        )
        
        # 버튼 이탈용 RA 사운드 - 강도 대폭 증가
        self.ra_exit_sound = self.haptic_renderer.create_material_sound(
            'plastic', 60, 40, 1.6, fade_out_ms=2, **plastic_params  # 진폭 1.1 → 1.6
        )
        
        print(f"Plastic sounds initialized: Motion={ra_motion_hz}Hz, Click={ra_click_hz}Hz, Hover=80Hz(2.0amp), Exit=60Hz(1.6amp)")
        
    def create_automotive_buttons(self):
        """자동차 UI 버튼들 생성 - 아이콘 형태로 변경"""
        buttons = []
        
        # 중앙 위치 계산
        center_x = self.width // 2
        center_y = self.height // 2
        
        # 기후 제어 버튼들 (상단 줄) - 간격과 크기 증가
        climate_y = center_y - 120  # 위치 조정
        climate_buttons = [
            {"name": "AC", "icon": "AC", "text": "A/C", "x": center_x - 280, "active": True, "color": "blue"},  # 간격 증가
            {"name": "Heat", "icon": "HEAT", "text": "HEAT", "x": center_x - 140, "active": False, "color": "orange"},
            {"name": "Fan", "icon": "FAN", "text": "FAN", "x": center_x, "active": False, "color": "green"},
            {"name": "Defrost", "icon": "DEF", "text": "DEFROST", "x": center_x + 140, "active": False, "color": "blue"},
            {"name": "Auto", "icon": "AUTO", "text": "AUTO", "x": center_x + 280, "active": False, "color": "green"},
        ]
        
        for btn in climate_buttons:
            btn.update({
                "y": climate_y,
                "rect": pygame.Rect(btn["x"] - 70, climate_y - 50, 140, 100),  # 버튼 크기 증가
                "type": "climate"
            })
            buttons.append(btn)
        
        # 차량 제어 버튼들 (하단 줄) - 간격과 크기 증가
        vehicle_y = center_y + 120  # 위치 조정
        vehicle_buttons = [
            {"name": "Lock", "icon": "LOCK", "text": "LOCK", "x": center_x - 210, "active": False, "color": "orange"},  # 간격 증가
            {"name": "Windows", "icon": "WIN", "text": "WINDOWS", "x": center_x - 70, "active": False, "color": "blue"},
            {"name": "Lights", "icon": "LITE", "text": "LIGHTS", "x": center_x + 70, "active": True, "color": "green"},
            {"name": "Horn", "icon": "HORN", "text": "HORN", "x": center_x + 210, "active": False, "color": "orange"},
        ]
        
        for btn in vehicle_buttons:
            btn.update({
                "y": vehicle_y,
                "rect": pygame.Rect(btn["x"] - 70, vehicle_y - 50, 140, 100),  # 버튼 크기 증가
                "type": "vehicle"
            })
            buttons.append(btn)
            
        return buttons
    
    def draw_button(self, button):
        """버튼 그리기 - 아이콘 중심, 사각형 제거"""
        x, y = button["x"], button["y"]
        
        # 활성 상태에 따른 색상
        if button.get("active"):
            color = self.get_button_color(button.get("color", "white"))
            text_color = color
            icon_scale = 1.2  # 활성화된 버튼은 아이콘 크게
        else:
            color = self.GRAY_INACTIVE
            text_color = self.GRAY_INACTIVE
            icon_scale = 1.0
        
        # 호버 상태 강조 - 더 큰 글로우
        if self.hovered_button == button:
            # 호버 시 더 강한 글로우 효과
            glow_color = tuple(min(255, c + 100) for c in color[:3])  # 글로우 더 강화
            pygame.draw.rect(self.screen, glow_color, 
                           (x - 80, y - 55, 160, 110), 4)  # 더 큰 글로우
            icon_scale *= 1.3  # 호버 시 더 크게
        
        # 아이콘 그리기 (텍스트 기반) - 크기 증가
        icon_size = int(36 * icon_scale)  # 기본 크기 증가 24 → 36
        icon_font = pygame.font.Font(None, icon_size)
        icon_surface = icon_font.render(button["icon"], True, text_color)
        icon_rect = icon_surface.get_rect(center=(x, y))
        self.screen.blit(icon_surface, icon_rect)
        
        # 텍스트 레이블 제거 (아이콘만 표시)
        # text_surface = self.font_tiny.render(button["text"], True, text_color)
        # text_rect = text_surface.get_rect(center=(x, y + 20))
        # self.screen.blit(text_surface, text_rect)
    
    def get_button_color(self, color_name):
        """버튼 색상 반환"""
        colors = {
            "blue": self.BLUE_ACTIVE,
            "orange": self.ORANGE_ACTIVE,
            "green": self.GREEN_ACTIVE,
            "white": self.WHITE
        }
        return colors.get(color_name, self.WHITE)
    
    def handle_click(self, pos):
        """버튼 클릭 처리"""
        for button in self.buttons:
            if button["rect"].collidepoint(pos):
                # 버튼 토글
                button["active"] = not button["active"]
                status = "ON" if button["active"] else "OFF"
                print(f"🔘 Button {button['name']}: {status}")
                return button
        
        # 배경 클릭 - 아무 반응 없음
        print("🔘 Background click - No haptic")
        return None

    def handle_mouse_move(self, pos):
        """마우스 이동 처리"""
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
                # 새 버튼 진입 - RA 호버 피드백 (강화)
                self.trigger_button_hover_ra()
                self.hover_start_time = current_time
                print(f"🎯 HOVER ENTER: {self.hovered_button['name']}")
            elif self.prev_hovered_button:
                # 버튼 이탈 - RA 이탈 피드백 추가
                self.trigger_button_exit_ra()
                print(f"🎯 HOVER EXIT: {self.prev_hovered_button['name']}")
        
        # 마우스 속도 계산 (버튼 위에서만)
        if self.hovered_button and self.last_mouse_pos:
            dx = pos[0] - self.last_mouse_pos[0]
            dy = pos[1] - self.last_mouse_pos[1]
            distance = np.sqrt(dx**2 + dy**2)
            dt = current_time - self.last_mouse_time
            
            if dt > self.min_mouse_delta_time:
                self.mouse_speed = min(distance / dt, self.max_speed_clamp)
                self.speed_history.append(self.mouse_speed)
                self.avg_mouse_speed = np.mean(self.speed_history)
                
                self.last_mouse_pos = pos
                self.last_mouse_time = current_time
        elif not self.hovered_button:
            # 버튼 밖에서는 속도 0
            self.mouse_speed = 0.0
            self.avg_mouse_speed = 0.0
    
    def trigger_button_hover_ra(self):
        """버튼 호버링 시 RA 피드백 - 강도 최대"""
        if self.ra_hover_sound:
            self.audio_player.play_sound(self.ra_hover_sound, channel_id=1, volume=2.0)  # 볼륨 1.5 → 2.0 (최대)
    
    def trigger_button_exit_ra(self):
        """버튼 이탈 시 RA 피드백 - 강도 대폭 증가"""
        if self.ra_exit_sound:
            self.audio_player.play_sound(self.ra_exit_sound, channel_id=1, volume=1.8)  # 볼륨 1.3 → 1.8
    
    def update_haptic_system(self):
        """햅틱 시스템 업데이트 - 버튼 위에서만 반응"""
        # 마우스 정지 감지
        if (time.perf_counter() - self.last_mouse_time) > self.mouse_stop_threshold and self.mouse_pressed:
            self.mouse_speed = 0.0
        
        # 버튼 위에서만 뉴런 시뮬레이션 실행
        if self.hovered_button:
            sa_fired, ra_motion_fired, ra_click_fired, sa_vu, ra_motion_vu, ra_click_vu = self.spike_encoder.step(
                mouse_speed=self.mouse_speed,
                avg_mouse_speed=self.avg_mouse_speed,
                material_roughness=self.material_roughness,
                mouse_pressed=self.mouse_pressed
            )
            
            # SA 뉴런 스파이크 처리 (버튼 위에서만) - 볼륨 증가
            if sa_fired:
                self.audio_player.play_sound(self.sa_sound, channel_id=0, 
                                           volume=self.sound_config['sa_sound_volume'])  # 1.2로 증가
            
            # RA 움직임 뉴런 스파이크 처리 (버튼 위에서만) - 볼륨 증가
            if ra_motion_fired and self.ra_motion_sound:
                # 마우스 속도에 따른 동적 볼륨 계산 (범위 증가)
                s = self.mouse_speed
                snd_cfg = self.sound_config
                vol_scl = snd_cfg['ra_motion_min_vol_scl']  # 0.7
                
                if s <= snd_cfg['ra_motion_vol_min_spd']:
                    vol_scl = snd_cfg['ra_motion_min_vol_scl']
                elif s >= snd_cfg['ra_motion_vol_max_spd']:
                    vol_scl = snd_cfg['ra_motion_max_vol_scl']  # 1.3
                else:
                    den = snd_cfg['ra_motion_vol_max_spd'] - snd_cfg['ra_motion_vol_min_spd']
                    if den > 0:
                        vol_scl = snd_cfg['ra_motion_min_vol_scl'] + ((s - snd_cfg['ra_motion_vol_min_spd']) / den) * (snd_cfg['ra_motion_max_vol_scl'] - snd_cfg['ra_motion_min_vol_scl'])
                
                self.audio_player.play_sound(self.ra_motion_sound, channel_id=1, 
                                           volume=np.clip(vol_scl, 0.0, 2.5))  # 최대 볼륨 1.5 → 2.5
            
            # RA 클릭 뉴런 스파이크 처리 (버튼 위에서만) - 볼륨 증가
            if ra_click_fired and self.ra_click_sound:
                self.audio_player.play_sound(self.ra_click_sound, channel_id=2, 
                                           volume=self.sound_config['ra_click_volume'])  # 1.1로 증가
        else:
            # 버튼 밖에서는 뉴런 시뮬레이션 안 함 (배경에서 RA 반응 없음)
            # SA 입력도 0으로 유지
            self.spike_encoder.update_sa_input(0.0)
    
    def draw_hud(self):
        """HUD 정보 표시"""
        # 제목
        title = self.font_large.render("Automotive Haptic Interface", True, self.WHITE)
        self.screen.blit(title, (50, 30))
        
        # 재질 정보 (플라스틱 고정)
        material_info = f"Material: {self.material_name} (Roughness: {self.material_roughness:.1f}) - Fixed"
        material_text = self.font_medium.render(material_info, True, (255, 200, 100))  # 플라스틱 색상
        self.screen.blit(material_text, (50, 80))
        
        # 마우스 상태 (버튼 위에서만 표시)
        if self.hovered_button:
            mouse_info = f"Speed: {self.mouse_speed:.0f} | Avg: {self.avg_mouse_speed:.0f} | Pressed: {self.mouse_pressed}"
            mouse_text = self.font_small.render(mouse_info, True, self.WHITE)
            self.screen.blit(mouse_text, (50, self.height - 80))
        
        # Hover 상태
        if self.hovered_button:
            hover_info = f"Hovering: {self.hovered_button['name']} ({self.hovered_button['icon']})"
            hover_color = self.get_button_color(self.hovered_button.get("color", "white"))
        else:
            hover_info = "Hovering: None - Move over buttons for haptic feedback"
            hover_color = self.GRAY_INACTIVE
            
        hover_text = self.font_small.render(hover_info, True, hover_color)
        self.screen.blit(hover_text, (50, self.height - 50))
        
        # 햅틱 안내 - 업데이트
        haptic_info = "Haptic only on buttons: SA(Pressure) + RA_Motion(Movement) + RA_Click(Click) + RA_Hover(Enter) + RA_Exit(Leave)"
        haptic_text = self.font_tiny.render(haptic_info, True, self.GRAY_INACTIVE)
        self.screen.blit(haptic_text, (50, self.height - 20))
    
    def draw_plastic_background(self):
        """플라스틱 재질 배경 효과"""
        # 플라스틱 특유의 인공적인 패턴
        plastic_color = (15, 15, 20)  # 플라스틱 색조
        
        # 기본 별빛 효과
        for i in range(60):
            x = (i * 137) % self.width
            y = (i * 211) % self.height
            alpha = 15 + (i % 20)
            color = (alpha//3, alpha//3, alpha//2)
            pygame.draw.circle(self.screen, color, (x, y), 1)
        
        # 플라스틱 특유의 직선 패턴
        for i in range(0, self.width, 80):
            for j in range(0, self.height, 80):
                # 격자 패턴
                alpha = int(5 + 3 * np.sin(i * 0.02) * np.cos(j * 0.02))
                if alpha > 0:
                    color = tuple(min(255, c + alpha) for c in plastic_color)
                    pygame.draw.rect(self.screen, color, (i, j, 2, 2))
        
        # 플라스틱 표면 반사 효과
        for i in range(0, self.width, 150):
            for j in range(0, self.height, 100):
                alpha = int(8 + 4 * np.sin((i + j) * 0.01))
                if alpha > 0:
                    color = (alpha + 10, alpha + 12, alpha + 15)
                    pygame.draw.circle(self.screen, color, (i, j), 2)
    
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
                        
                        # 버튼 위에서만 SA 입력 시작 - 세기 대폭 증가
                        if self.hovered_button:
                            self.spike_encoder.update_sa_input(25.0)  # 18.0A → 25.0A로 대폭 증가
                            print(f"🔴 SA START: Click on {self.hovered_button['name']} (25.0A)")
                        
                        # 클릭 처리
                        self.handle_click(event.pos)
                        
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.mouse_pressed = False
                        self.mouse_speed = 0.0
                        
                        # SA 입력 중지
                        self.spike_encoder.update_sa_input(0.0)
                        print(f"🔵 SA STOP: Mouse released (0.0A)")
                        
                elif event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_move(event.pos)
            
            # 햅틱 시스템 업데이트
            self.update_haptic_system()
            
            # 화면 그리기
            self.screen.fill(self.BLACK_GLASS)
            self.draw_plastic_background()
            
            # 버튼들 그리기 (아이콘 형태)
            for button in self.buttons:
                self.draw_button(button)
            
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