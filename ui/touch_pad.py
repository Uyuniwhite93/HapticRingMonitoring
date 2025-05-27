import sys
import time
from collections import deque
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                           QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton)
from PyQt6.QtCore import Qt, QPointF, QTimer, QRectF, QThread, pyqtSignal, QMargins
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QPainterPath, QPixmap, QRadialGradient, QFont, QFontDatabase, QCursor
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
import gc
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp
from numba import jit, prange
import psutil
import pygame

class TouchPadWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)  # 4:3 비율
        self.main_window = parent
        self.current_material = "metal"  # 기본 재질
        
        # 재질별 이미지 특성 정의
        self.material_properties = {
            "metal": {
                "base_color": QColor(75, 82, 93),  # 금속 기본색 - 청회색
                "highlight_opacity": 90,  # 금속은 반사가 강함
                "texture_pattern": "linear",  # 금속은 직선적 패턴
                "texture_scale": 2.0,  # 패턴 스케일
                "specular": 0.8  # 반사도
            },
            "glass": {
                "base_color": QColor(80, 100, 120),  # 유리 기본색 - 푸른 회색
                "highlight_opacity": 100,  # 유리는 반사가 매우 강함
                "texture_pattern": "smooth",  # 유리는 매끄러움
                "texture_scale": 0.5,  # 패턴 스케일
                "specular": 0.9  # 반사도가 높음
            },
            "wood": {
                "base_color": QColor(150, 110, 70),  # 나무 기본색 - 갈색
                "highlight_opacity": 40,  # 나무는 반사가 약함
                "texture_pattern": "wood",  # 나무결 패턴
                "texture_scale": 5.0,  # 패턴 스케일
                "specular": 0.3  # 반사도가 낮음
            },
            "fabric": {
                "base_color": QColor(100, 120, 130),  # 직물 기본색 - 청회색
                "highlight_opacity": 30,  # 직물은 반사가 약함
                "texture_pattern": "weave",  # 직물 직조 패턴
                "texture_scale": 6.0,  # 패턴 스케일
                "specular": 0.2  # 반사도가 매우 낮음
            },
            "silk": {
                "base_color": QColor(220, 220, 240),  # 실크 기본색 - 연한 자주색
                "highlight_opacity": 60,  # 실크는 은은한 반사
                "texture_pattern": "smooth_weave",  # 부드러운 직조 패턴
                "texture_scale": 4.0,  # 패턴 스케일
                "specular": 0.5  # 중간 정도의 반사도
            }
        }
        
    def is_inside_pad(self, position):
        """터치 위치가 터치패드 내부인지 확인"""
        # 여백을 고려한 경계 설정 (약간의 마진 추가)
        margin = 2
        rect = QRectF(self.rect()).adjusted(margin, margin, -margin, -margin)
        return rect.contains(position)
        
    def set_material(self, material):
        """재질 변경 메서드"""
        if material in self.material_properties:
            self.current_material = material
            self.update()  # 위젯 다시 그리기
            
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.main_window.handlePress(event.position())
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.main_window.handleRelease()
        
    def mouseMoveEvent(self, event):
        position = event.position()
        if self.is_inside_pad(position):
            # 영역 안에 있으면 터치로 인식
            if not self.main_window.is_pressed:
                self.main_window.handlePress(position)
            self.main_window.handleMove(position)
        else:
            # 영역 밖으로 나가면 이탈 처리
            if self.main_window.is_pressed:
                self.main_window.handleExit(position)
        
    def leaveEvent(self, event):
        """마우스가 위젯을 떠날 때 호출되는 이벤트"""
        # 터치 중일 때만 이탈 처리
        if self.main_window.is_pressed:
            # 마우스 커서 위치 가져오기
            cursor_pos = self.mapFromGlobal(QCursor.pos())
            self.main_window.handleExit(QPointF(cursor_pos.x(), cursor_pos.y()))
        super().leaveEvent(event)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        # 터치패드 영역을 둥글게 그리기
        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        border_radius = 14  # 더 둥글게
        
        # 현재 재질에 따른 속성 가져오기
        material_props = self.material_properties[self.current_material]
        base_color = material_props["base_color"]
        highlight_opacity = material_props["highlight_opacity"]
        texture_pattern = material_props["texture_pattern"]
        texture_scale = material_props["texture_scale"]
        specular = material_props["specular"]
        
        # 배경 그라디언트 (재질에 따라 변경)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        
        # 기본 색상으로부터 어두운/밝은 변형 생성
        darker_color = QColor(
            max(0, base_color.red() - 15),
            max(0, base_color.green() - 15),
            max(0, base_color.blue() - 15)
        )
        darkest_color = QColor(
            max(0, base_color.red() - 25),
            max(0, base_color.green() - 25),
            max(0, base_color.blue() - 25)
        )
        lighter_color = QColor(
            min(255, base_color.red() + 15),
            min(255, base_color.green() + 15),
            min(255, base_color.blue() + 15)
        )
        
        gradient.setColorAt(0.0, lighter_color)
        gradient.setColorAt(0.3, base_color)
        gradient.setColorAt(0.7, darker_color)
        gradient.setColorAt(1.0, darkest_color)
        
        # 경계선
        border_path = QPainterPath()
        border_path.addRoundedRect(rect, border_radius, border_radius)
        
        # 그림자 효과 (수동으로 그리기)
        for i in range(10):
            shadow_offset = 0.5 * i  # 작은 오프셋
            shadow_rect = rect.adjusted(-shadow_offset, shadow_offset * 0.7, shadow_offset, shadow_offset * 1.5)
            shadow_path = QPainterPath()
            shadow_path.addRoundedRect(shadow_rect, border_radius, border_radius)
            shadow_opacity = 10 - i  # 점점 희미해지는 그림자
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, shadow_opacity))
            painter.drawPath(shadow_path)
        
        # 메인 배경
        painter.setPen(QPen(QColor(70, 72, 78), 1.0))  # 은은한 테두리
        painter.setBrush(QBrush(gradient))
        painter.drawPath(border_path)
        
        # 재질에 따른 텍스처 패턴 적용
        if texture_pattern == "wood":
            # 나무결 패턴
            self.draw_wood_texture(painter, rect, border_path, base_color, texture_scale)
        elif texture_pattern == "weave":
            # 직물 패턴
            self.draw_fabric_texture(painter, rect, border_path, base_color, texture_scale)
        elif texture_pattern == "smooth_weave":
            # 실크 패턴
            self.draw_silk_texture(painter, rect, border_path, base_color, texture_scale)
        
        # 상단 광택 효과 (재질에 따라 강도 조절)
        highlight = QLinearGradient(0, 0, 0, self.height() * 0.8)
        highlight.setColorAt(0.0, QColor(255, 255, 255, highlight_opacity))
        highlight.setColorAt(0.2, QColor(255, 255, 255, int(highlight_opacity * 0.8)))
        highlight.setColorAt(0.5, QColor(255, 255, 255, int(highlight_opacity * 0.5)))
        highlight.setColorAt(0.8, QColor(255, 255, 255, int(highlight_opacity * 0.2)))
        highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
        
        painter.setBrush(QBrush(highlight))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(border_path)
        
        # 사선 광택 효과 (재질에 따라 다르게 적용)
        if specular > 0.3:  # 반사가 있는 재질만
            diagonal_highlight = QLinearGradient(
                0, self.height(), self.width() * 0.8, 0)
            diagonal_highlight.setColorAt(0.0, QColor(255, 255, 255, int(10 * specular)))
            diagonal_highlight.setColorAt(0.3, QColor(255, 255, 255, int(30 * specular)))
            diagonal_highlight.setColorAt(0.5, QColor(255, 255, 255, int(50 * specular)))
            diagonal_highlight.setColorAt(0.7, QColor(255, 255, 255, int(30 * specular)))
            diagonal_highlight.setColorAt(1.0, QColor(255, 255, 255, int(10 * specular)))
            
            painter.setBrush(QBrush(diagonal_highlight))
            painter.drawPath(border_path)
        
        # 원형 광택 효과 (반사도에 따라 강도 조절)
        if specular > 0.2:  # 최소한의 반사가 있는 재질
            center_x = rect.center().x() + rect.width() * 0.05
            center_y = rect.center().y() - rect.height() * 0.1
            radial_gradient = QRadialGradient(
                center_x, center_y, rect.width() * 0.9)
            radial_gradient.setColorAt(0.0, QColor(255, 255, 255, int(60 * specular)))
            radial_gradient.setColorAt(0.4, QColor(255, 255, 255, int(40 * specular)))
            radial_gradient.setColorAt(0.7, QColor(255, 255, 255, int(20 * specular)))
            radial_gradient.setColorAt(1.0, QColor(255, 255, 255, 0))
            
            painter.setBrush(QBrush(radial_gradient))
            painter.drawPath(border_path)
        
        # 터치패드 경계선
        painter.setPen(QPen(QColor(80, 82, 88), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(border_path)
        
        # 반짝이는 포인트 효과 (금속, 유리에만 추가)
        if self.current_material in ["metal", "glass"]:
            painter.setPen(Qt.PenStyle.NoPen)
            np.random.seed(10)  # 고정된 랜덤 패턴 사용
            for i in range(8):
                spark_x = rect.left() + rect.width() * (0.2 + 0.6 * np.random.random())
                spark_y = rect.top() + rect.height() * (0.2 + 0.6 * np.random.random())
                spark_size = 1.5 + 2.0 * np.random.random()
                spark_opacity = 40 + 80 * np.random.random() * specular
                
                spark_gradient = QRadialGradient(spark_x, spark_y, spark_size)
                spark_gradient.setColorAt(0.0, QColor(255, 255, 255, int(spark_opacity)))
                spark_gradient.setColorAt(1.0, QColor(255, 255, 255, 0))
                
                painter.setBrush(QBrush(spark_gradient))
                painter.drawEllipse(QPointF(spark_x, spark_y), spark_size, spark_size)
    
    def draw_wood_texture(self, painter, rect, clip_path, base_color, scale):
        """나무 질감 패턴 그리기 (최적화)"""
        painter.save()
        painter.setClipPath(clip_path)  # 테두리 경계 설정
        
        # 크기 기반 캐싱 키 생성
        cache_key = f"wood_{int(rect.width())}_{int(rect.height())}_{int(scale*10)}"
        
        # 캐시된 패턴이 있는지 확인
        if cache_key in self.material_properties.get('wood_cache', {}):
            # 캐시된 픽스맵 사용
            pixmap = self.material_properties['wood_cache'][cache_key]
            painter.drawPixmap(rect.toRect(), pixmap)
            painter.restore()
            return
        
        # 최초 그리기 또는 크기 변경 시 새로 생성
        pixmap = QPixmap(int(rect.width()), int(rect.height()))
        pixmap.fill(Qt.GlobalColor.transparent)
        
        off_painter = QPainter(pixmap)
        off_painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        # 나무결 방향 (세로 방향)
        num_lines = max(20, int(rect.width() / (8 / scale)))  # 라인 수 증가
        line_width = 2.5 * scale  # 더 얇은 라인
        
        # 나무결 색상 변화 (자연스러운 색상)
        light_color = QColor(
            min(255, base_color.red() + 20),
            min(255, base_color.green() + 15),
            min(255, base_color.blue() + 5)
        )
        dark_color = QColor(
            max(0, base_color.red() - 15),
            max(0, base_color.green() - 10),
            max(0, base_color.blue() - 5)
        )
        
        # 랜덤 시드 고정
        np.random.seed(42)
        
        # 나무결 그리기 (더 자연스러운 곡선)
        for i in range(num_lines):
            x = rect.left() + i * (rect.width() / num_lines)
            
            path = QPainterPath()
            path.moveTo(x, 0)
            
            # 더 부드러운 곡선으로 나무결 표현
            control_points = []
            num_segments = 8  # 더 많은 세그먼트
            for j in range(num_segments):
                y_pos = j * rect.height() / (num_segments - 1)
                x_offset = np.random.normal(0, 3) * scale  # 변동 폭 감소
                control_points.append(QPointF(x + x_offset, y_pos))
            
            # 베지어 곡선으로 부드럽게 연결
            for j in range(1, len(control_points)):
                if j == 1:
                    path.lineTo(control_points[j])
                else:
                    prev = control_points[j-1]
                    curr = control_points[j]
                    path.quadTo(prev, QPointF(
                        (prev.x() + curr.x()) / 2,
                        (prev.y() + curr.y()) / 2
                    ))
            
            # 나무결 그리기
            wood_pen = QPen()
            
            # 더 자연스러운 색상 변화
            if i % 3 == 0:
                wood_pen.setColor(dark_color)
            elif i % 3 == 1:
                wood_pen.setColor(light_color)
            else:
                wood_pen.setColor(base_color)
                
            wood_pen.setWidth(int(line_width))
            wood_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            
            # 나무결의 투명도 변화
            opacity = 30 + (np.random.random() * 30)  # 더 은은한 투명도
            wood_pen.setColor(QColor(wood_pen.color().red(), 
                                    wood_pen.color().green(), 
                                    wood_pen.color().blue(), 
                                    int(opacity)))
            
            off_painter.setPen(wood_pen)
            off_painter.drawPath(path)
        
        off_painter.end()
        
        # 완성된 나무결 이미지를 캐시에 저장
        if 'wood_cache' not in self.material_properties:
            self.material_properties['wood_cache'] = {}
        self.material_properties['wood_cache'][cache_key] = pixmap
        
        # 캐시된 이미지 그리기
        painter.drawPixmap(rect.toRect(), pixmap)
        painter.restore()
    
    def draw_fabric_texture(self, painter, rect, clip_path, base_color, scale):
        """직물 질감 패턴 그리기 (최적화)"""
        painter.save()
        painter.setClipPath(clip_path)
        
        cache_key = f"fabric_{int(rect.width())}_{int(rect.height())}_{int(scale*10)}"
        
        if cache_key in self.material_properties.get('fabric_cache', {}):
            pixmap = self.material_properties['fabric_cache'][cache_key]
            painter.drawPixmap(rect.toRect(), pixmap)
            painter.restore()
            return
        
        pixmap = QPixmap(int(rect.width()), int(rect.height()))
        pixmap.fill(Qt.GlobalColor.transparent)
        
        off_painter = QPainter(pixmap)
        off_painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        # 직물 격자 크기 조정
        grid_size = int(3 * scale)  # 더 조밀한 격자
        line_width = 1  # 더 얇은 선
        
        # 직물 색상 (더 부드러운 색상 차이)
        warp_color = QColor(  # 세로 방향 실
            min(255, base_color.red() + 5),
            min(255, base_color.green() + 5),
            min(255, base_color.blue() + 8)
        )
        weft_color = QColor(  # 가로 방향 실
            max(0, base_color.red() - 5),
            max(0, base_color.green() - 5),
            max(0, base_color.blue() - 3)
        )
        
        # 격자 간격
        step = grid_size
        
        # 세로선 (직조 패턴)
        for x in range(0, int(rect.width()), step):
            for y in range(0, int(rect.height()), step * 2):
                # 직조 패턴을 위한 시작점 변동
                start_y = y + (step/2 if (x//step) % 2 == 0 else 0)
                end_y = min(start_y + step * 1.5, rect.height())
                
                fabric_pen = QPen(warp_color)
                fabric_pen.setWidth(line_width)
                fabric_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                
                # 투명도 변화로 입체감 표현
                opacity = 20 + (10 * np.sin(x * 0.1))
                fabric_pen.setColor(QColor(warp_color.red(),
                                         warp_color.green(),
                                         warp_color.blue(),
                                         int(opacity)))
                
                off_painter.setPen(fabric_pen)
                off_painter.drawLine(QPointF(x, start_y), QPointF(x, end_y))
        
        # 가로선 (직조 패턴)
        for y in range(0, int(rect.height()), step):
            for x in range(0, int(rect.width()), step * 2):
                # 직조 패턴을 위한 시작점 변동
                start_x = x + (step/2 if (y//step) % 2 == 0 else 0)
                end_x = min(start_x + step * 1.5, rect.width())
                
                fabric_pen = QPen(weft_color)
                fabric_pen.setWidth(line_width)
                fabric_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                
                # 투명도 변화로 입체감 표현
                opacity = 20 + (10 * np.sin(y * 0.1))
                fabric_pen.setColor(QColor(weft_color.red(),
                                         weft_color.green(),
                                         weft_color.blue(),
                                         int(opacity)))
                
                off_painter.setPen(fabric_pen)
                off_painter.drawLine(QPointF(start_x, y), QPointF(end_x, y))
        
        off_painter.end()
        
        if 'fabric_cache' not in self.material_properties:
            self.material_properties['fabric_cache'] = {}
        self.material_properties['fabric_cache'][cache_key] = pixmap
        
        painter.drawPixmap(rect.toRect(), pixmap)
        painter.restore()
    
    def draw_silk_texture(self, painter, rect, clip_path, base_color, scale):
        """실크 질감 패턴 그리기 (최적화)"""
        painter.save()
        painter.setClipPath(clip_path)  # 테두리 경계 설정
        
        # 크기 기반 캐싱 키 생성
        cache_key = f"silk_{int(rect.width())}_{int(rect.height())}_{int(scale*10)}"
        
        # 캐시된 패턴이 있는지 확인
        if cache_key in self.material_properties.get('silk_cache', {}):
            # 캐시된 픽스맵 사용
            pixmap = self.material_properties['silk_cache'][cache_key]
            painter.drawPixmap(rect.toRect(), pixmap)
            painter.restore()
            return
        
        # 오프스크린 렌더링으로 픽스맵 생성
        pixmap = QPixmap(int(rect.width()), int(rect.height()))
        pixmap.fill(Qt.GlobalColor.transparent)
        
        off_painter = QPainter(pixmap)
        off_painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        # 실크는 매우 세밀한 직조 패턴
        grid_size = int(2 * scale)
        line_width = int(1.0)  # int로 변환
        
        # 실크 특유의 광택을 위한 색상
        sheen_color = QColor(
            min(255, base_color.red() + 25),
            min(255, base_color.green() + 25),
            min(255, base_color.blue() + 30)
        )
        
        # 최적화: 더 적은 각도만 사용
        angles = [45]  # 135도 제거하여 반복 횟수 감소
        
        # 실크 특유의 얇은 무광 효과
        for angle in angles:  # 대각선 패턴
            off_painter.save()
            off_painter.translate(rect.center())
            off_painter.rotate(angle)
            
            # 계산된 중심 기준 좌표
            half_width = rect.width() * 0.7  # 대각선이므로 더 길게
            half_height = rect.height() * 0.7
            
            # 대각선 줄무늬
            step = int(grid_size * 4)  # 간격 증가로 선 개수 감소
            
            for offset in range(-int(half_width * 2), int(half_width * 2), step):
                silk_pen = QPen(sheen_color)
                silk_pen.setWidth(line_width)
                silk_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                # 투명도 변화로 실크 광택 표현
                opacity = int(15 + (offset % 20))  # int로 변환
                silk_pen.setColor(QColor(silk_pen.color().red(), 
                                        silk_pen.color().green(), 
                                        silk_pen.color().blue(), 
                                        opacity))
                
                off_painter.setPen(silk_pen)
                off_painter.drawLine(QPointF(offset, -half_height), QPointF(offset, half_height))
            
            off_painter.restore()
            
            # 다른 방향 패턴 (추가 각도)
            off_painter.save()
            off_painter.translate(rect.center())
            off_painter.rotate(135)  # 두 번째 방향
            
            for offset in range(-int(half_width * 2), int(half_width * 2), step):
                if offset % 2 == 0:  # 선 개수 절반으로 감소
                    silk_pen = QPen(sheen_color)
                    silk_pen.setWidth(line_width)
                    silk_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    opacity = int(15 + (offset % 20))  # int로 변환
                    silk_pen.setColor(QColor(silk_pen.color().red(), 
                                            silk_pen.color().green(), 
                                            silk_pen.color().blue(), 
                                            opacity))
                    
                    off_painter.setPen(silk_pen)
                    off_painter.drawLine(QPointF(offset, -half_height), QPointF(offset, half_height))
            
            off_painter.restore()
        
        off_painter.end()
        
        # 캐시에 저장
        if 'silk_cache' not in self.material_properties:
            self.material_properties['silk_cache'] = {}
        self.material_properties['silk_cache'][cache_key] = pixmap
        
        # 캐시된 이미지 그리기
        painter.drawPixmap(rect.toRect(), pixmap)
        painter.restore()
