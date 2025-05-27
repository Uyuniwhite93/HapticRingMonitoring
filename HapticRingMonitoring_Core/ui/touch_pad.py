import sys
import time
from collections import deque
import numpy as np
from PyQt6.QtWidgets import (QWidget, QLabel, QFrame, QPushButton) # QApplication, QMainWindow, QVBoxLayout, QHBoxLayout are not directly used
from PyQt6.QtCore import Qt, QPointF, QTimer, QRectF, QThread, pyqtSignal, QMargins # QTimer, QThread, pyqtSignal, QMargins are not directly used
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QPainterPath, QPixmap, QRadialGradient, QFont, QFontDatabase, QCursor # QFont, QFontDatabase are not directly used
# from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis # Not used
# import gc # Not used
# from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor # Not used
# import multiprocessing as mp # Not used
# from numba import jit, prange # Not used
# import psutil # Not used
# import pygame # Not used

class TouchPadWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)  # 4:3 ratio
        self.main_window = parent
        self.current_material = "metal"  # Default material

        # Define image properties for each material
        self.material_properties = {
            "metal": {
                "base_color": QColor(75, 82, 93),  # Metal base color - blue-gray
                "highlight_opacity": 90,  # Metal has strong reflection
                "texture_pattern": "linear",  # Metal has linear pattern
                "texture_scale": 2.0,  # Pattern scale
                "specular": 0.8  # Reflectivity
            },
            "glass": {
                "base_color": QColor(80, 100, 120),  # Glass base color - bluish gray
                "highlight_opacity": 100,  # Glass has very strong reflection
                "texture_pattern": "smooth",  # Glass is smooth
                "texture_scale": 0.5,  # Pattern scale
                "specular": 0.9  # High reflectivity
            },
            "wood": {
                "base_color": QColor(150, 110, 70),  # Wood base color - brown
                "highlight_opacity": 40,  # Wood has weak reflection
                "texture_pattern": "wood",  # Wood grain pattern
                "texture_scale": 5.0,  # Pattern scale
                "specular": 0.3  # Low reflectivity
            },
            "fabric": {
                "base_color": QColor(100, 120, 130),  # Fabric base color - blue-gray
                "highlight_opacity": 30,  # Fabric has weak reflection
                "texture_pattern": "weave",  # Fabric weave pattern
                "texture_scale": 6.0,  # Pattern scale
                "specular": 0.2  # Very low reflectivity
            },
            "silk": {
                "base_color": QColor(220, 220, 240),  # Silk base color - light purple
                "highlight_opacity": 60,  # Silk has subtle reflection
                "texture_pattern": "smooth_weave",  # Smooth weave pattern
                "texture_scale": 4.0,  # Pattern scale
                "specular": 0.5  # Medium reflectivity
            }
        }
        self._cached_pixmaps = {} # Cache for generated texture pixmaps

    def is_inside_pad(self, position):
        """Check if the touch position is inside the touchpad."""
        # Set boundary considering margin (add a small margin)
        margin = 2
        rect = QRectF(self.rect()).adjusted(margin, margin, -margin, -margin)
        return rect.contains(position)

    def set_material(self, material):
        """Method to change material."""
        if material in self.material_properties:
            self.current_material = material
            self.update()  # Redraw widget

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.main_window.handlePress(event.position())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.main_window.handleRelease()

    def mouseMoveEvent(self, event):
        position = event.position()
        if self.is_inside_pad(position):
            # Recognized as touch if inside the area
            if not self.main_window.is_pressed:
                self.main_window.handlePress(position)
            self.main_window.handleMove(position)
        else:
            # Process as exit if outside the area
            if self.main_window.is_pressed:
                self.main_window.handleExit(position)

    def leaveEvent(self, event):
        """Event called when the mouse leaves the widget."""
        # Process exit only when touched
        if self.main_window.is_pressed:
            # Get mouse cursor position
            cursor_pos = self.mapFromGlobal(QCursor.pos())
            self.main_window.handleExit(QPointF(cursor_pos.x(), cursor_pos.y()))
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Draw touchpad area rounded
        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        border_radius = 14  # More rounded

        # Get properties based on current material
        material_props = self.material_properties[self.current_material]
        base_color = material_props["base_color"]
        highlight_opacity = material_props["highlight_opacity"]
        texture_pattern = material_props["texture_pattern"]
        texture_scale = material_props["texture_scale"]
        specular = material_props["specular"]

        # Background gradient (changes based on material)
        gradient = QLinearGradient(0, 0, self.width(), self.height())

        # Create darker/lighter variations from base color
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

        # Border line
        border_path = QPainterPath()
        border_path.addRoundedRect(rect, border_radius, border_radius)

        # Shadow effect (draw manually)
        for i in range(10):
            shadow_offset = 0.5 * i  # Small offset
            shadow_rect = rect.adjusted(-shadow_offset, shadow_offset * 0.7, shadow_offset, shadow_offset * 1.5)
            shadow_path = QPainterPath()
            shadow_path.addRoundedRect(shadow_rect, border_radius, border_radius)
            shadow_opacity = 10 - i  # Gradually fading shadow
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, shadow_opacity))
            painter.drawPath(shadow_path)

        # Main background
        painter.setPen(QPen(QColor(70, 72, 78), 1.0))  # Subtle border
        painter.setBrush(QBrush(gradient))
        painter.drawPath(border_path)

        # Apply texture pattern based on material
        if texture_pattern == "wood":
            self.draw_wood_texture(painter, rect, border_path, base_color, texture_scale)
        elif texture_pattern == "weave":
            self.draw_fabric_texture(painter, rect, border_path, base_color, texture_scale)
        elif texture_pattern == "smooth_weave":
            self.draw_silk_texture(painter, rect, border_path, base_color, texture_scale)

        # Top gloss effect (adjust intensity based on material)
        highlight = QLinearGradient(0, 0, 0, self.height() * 0.8)
        highlight.setColorAt(0.0, QColor(255, 255, 255, highlight_opacity))
        highlight.setColorAt(0.2, QColor(255, 255, 255, int(highlight_opacity * 0.8)))
        highlight.setColorAt(0.5, QColor(255, 255, 255, int(highlight_opacity * 0.5)))
        highlight.setColorAt(0.8, QColor(255, 255, 255, int(highlight_opacity * 0.2)))
        highlight.setColorAt(1.0, QColor(255, 255, 255, 0))

        painter.setBrush(QBrush(highlight))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(border_path)

        # Diagonal gloss effect (apply differently based on material)
        if specular > 0.3:  # Only for materials with reflection
            diagonal_highlight = QLinearGradient(
                0, self.height(), self.width() * 0.8, 0)
            diagonal_highlight.setColorAt(0.0, QColor(255, 255, 255, int(10 * specular)))
            diagonal_highlight.setColorAt(0.3, QColor(255, 255, 255, int(30 * specular)))
            diagonal_highlight.setColorAt(0.5, QColor(255, 255, 255, int(50 * specular)))
            diagonal_highlight.setColorAt(0.7, QColor(255, 255, 255, int(30 * specular)))
            diagonal_highlight.setColorAt(1.0, QColor(255, 255, 255, int(10 * specular)))

            painter.setBrush(QBrush(diagonal_highlight))
            painter.drawPath(border_path)

        # Circular gloss effect (adjust intensity based on reflectivity)
        if specular > 0.2:  # Materials with minimal reflection
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

        # Touchpad border
        painter.setPen(QPen(QColor(80, 82, 88), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(border_path)

        # Sparkling point effect (add only to metal, glass)
        if self.current_material in ["metal", "glass"]:
            painter.setPen(Qt.PenStyle.NoPen)
            np.random.seed(10)  # Use fixed random pattern
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

    def _get_cached_pixmap(self, key, rect, generator_func, *args):
        """Helper to get or create cached pixmap."""
        if key in self._cached_pixmaps:
            cached_pixmap, cached_rect = self._cached_pixmaps[key]
            if cached_rect == rect:
                return cached_pixmap
        
        pixmap = QPixmap(rect.size().toSize())
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        generator_func(painter, QRectF(QPointF(0,0), rect.size()), *args) # Draw on pixmap with adjusted rect
        painter.end()
        self._cached_pixmaps[key] = (pixmap, rect)
        return pixmap

    def draw_wood_texture(self, painter, rect, clip_path, base_color, scale):
        """Draw wood texture pattern (optimized)."""
        painter.save()
        painter.setClipPath(clip_path)

        cache_key = f"wood_{int(rect.width())}_{int(rect.height())}_{int(scale*10)}"
        
        pixmap = self._get_cached_pixmap(cache_key, rect, self._render_wood_texture, base_color, scale)
        painter.drawPixmap(rect.topLeft(), pixmap)
        painter.restore()

    def _render_wood_texture(self, p, r, base_color, scale):
        """Renders the wood texture to a QPainter."""
        np.random.seed(0) # Consistent randomness
        num_rings = int(10 * scale)
        
        for i in range(num_rings):
            # Ring properties
            ring_color_variation = np.random.randint(-20, 20)
            ring_color = QColor(
                max(0, min(255, base_color.red() + ring_color_variation)),
                max(0, min(255, base_color.green() + ring_color_variation - 5)), # Slightly greener
                max(0, min(255, base_color.blue() + ring_color_variation - 10)) # Slightly browner
            )
            ring_width = (np.random.rand() * 0.02 + 0.005) * r.width() * (5 / scale)
            
            path = QPainterPath()
            start_y = r.top() + (i / num_rings) * r.height() * (1 + np.random.uniform(-0.1, 0.1))
            path.moveTo(r.left() - r.width()*0.1, start_y)

            # Introduce waviness and knots
            num_segments = 20
            for j in range(num_segments + 1):
                x = r.left() + (j / num_segments) * r.width() * 1.2 # Extend beyond bounds for clipping
                y_offset = np.sin(j / num_segments * np.pi * 2 * np.random.uniform(0.5,1.5) + np.random.rand()) * r.height() * 0.03 * scale
                
                # Knot simulation
                if np.random.rand() < 0.05 * (scale/2): # More knots with larger scale
                    knot_radius = np.random.rand() * r.width() * 0.02 * scale
                    knot_x = x + np.random.uniform(-knot_radius, knot_radius)
                    knot_y = start_y + y_offset + np.random.uniform(-knot_radius, knot_radius)
                    
                    # Draw a darker ellipse for the knot
                    knot_color = ring_color.darker(150)
                    p.setPen(QPen(knot_color, 1))
                    p.setBrush(QBrush(knot_color))
                    p.drawEllipse(QPointF(knot_x, knot_y), knot_radius, knot_radius * np.random.uniform(0.5, 0.8))
                
                path.lineTo(x, start_y + y_offset)

            p.setPen(QPen(ring_color, ring_width))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)

        # Add subtle noise/grain
        noise_density = int(500 * (scale/2)) # More noise with larger scale
        for _ in range(noise_density):
            nx = r.left() + np.random.rand() * r.width()
            ny = r.top() + np.random.rand() * r.height()
            noise_color = base_color.darker(110 + np.random.randint(0,20))
            noise_color.setAlpha(np.random.randint(30,70))
            p.setPen(QPen(noise_color, 0.5 + np.random.rand()))
            p.drawPoint(QPointF(nx,ny))


    def draw_fabric_texture(self, painter, rect, clip_path, base_color, scale):
        """Draw fabric texture pattern (optimized)."""
        painter.save()
        painter.setClipPath(clip_path)

        cache_key = f"fabric_{int(rect.width())}_{int(rect.height())}_{int(scale*10)}"
        pixmap = self._get_cached_pixmap(cache_key, rect, self._render_fabric_texture, base_color, scale)
        painter.drawPixmap(rect.topLeft(), pixmap)

        painter.restore()

    def _render_fabric_texture(self, p, r, base_color, scale):
        """Renders the fabric texture to a QPainter."""
        np.random.seed(1) # Consistent randomness
        density = int(25 * scale) # Higher density for finer weave
        thread_thickness_base = max(0.5, 3.0 / scale)

        # Weave colors with slight variations
        warp_color_dark = base_color.darker(120)
        warp_color_light = base_color.lighter(110)
        weft_color_dark = base_color.darker(130)
        weft_color_light = base_color.lighter(120)

        # Warp threads (vertical)
        for i in range(int(r.width() / density * scale * 2)): # Increased count for visual density
            x = r.left() + (i * density / (scale*2)) + np.random.uniform(-2,2) / scale
            if x > r.right() + thread_thickness_base * 2: continue

            is_light_thread = (i % 4) < 2 # Alternate light/dark appearance
            thread_color = warp_color_light if is_light_thread else warp_color_dark
            thread_thickness = thread_thickness_base + np.random.uniform(-0.2, 0.2) / scale
            
            p.setPen(QPen(thread_color, thread_thickness))
            p.drawLine(QPointF(x, r.top() - 5), QPointF(x, r.bottom() + 5)) # Extend beyond bounds

        # Weft threads (horizontal)
        for i in range(int(r.height() / density * scale * 2)): # Increased count
            y = r.top() + (i * density / (scale*2)) + np.random.uniform(-2,2) / scale
            if y > r.bottom() + thread_thickness_base * 2: continue
            
            is_light_thread = ((i + (int(scale) % 2)) % 4) < 2 # Offset alternation for weave
            thread_color = weft_color_light if is_light_thread else weft_color_dark
            thread_thickness = thread_thickness_base + np.random.uniform(-0.2, 0.2) / scale

            p.setPen(QPen(thread_color, thread_thickness))
            
            # Simulate thread going over/under
            segment_length = density * 2 / scale
            current_x = r.left() - 5
            while current_x < r.right() + 5:
                # Determine if this segment is "over" or "under" based on nearby warp threads
                # This is a simplified approach; true weave simulation is complex
                is_over = ( (current_x // (density / scale)) % 2 == (i // 2) % 2) 
                
                if is_over:
                    p.setPen(QPen(thread_color.lighter(110) if is_light_thread else thread_color.lighter(105), thread_thickness))
                else:
                    p.setPen(QPen(thread_color.darker(110) if not is_light_thread else thread_color.darker(105), thread_thickness))
                
                p.drawLine(QPointF(current_x, y), QPointF(min(r.right() + 5, current_x + segment_length), y))
                current_x += segment_length


    def draw_silk_texture(self, painter, rect, clip_path, base_color, scale):
        """Draw silk texture pattern (optimized)."""
        painter.save()
        painter.setClipPath(clip_path)

        cache_key = f"silk_{int(rect.width())}_{int(rect.height())}_{int(scale*10)}"
        pixmap = self._get_cached_pixmap(cache_key, rect, self._render_silk_texture, base_color, scale)
        painter.drawPixmap(rect.topLeft(), pixmap)
        painter.restore()

    def _render_silk_texture(self, p, r, base_color, scale):
        """Renders the silk texture to a QPainter."""
        np.random.seed(2) # Consistent randomness
        num_strands = int(150 * scale) # Silk has many fine strands

        for i in range(num_strands):
            path = QPainterPath()
            
            # Strand properties
            start_angle = np.random.uniform(0, 2 * np.pi)
            start_x = r.center().x() + np.cos(start_angle) * r.width() * np.random.uniform(0.1, 0.6)
            start_y = r.center().y() + np.sin(start_angle) * r.height() * np.random.uniform(0.1, 0.6)
            path.moveTo(start_x, start_y)

            # Strand color with sheen
            alpha = np.random.randint(20, 70) # More translucent
            hue_shift = np.random.randint(-10, 10)
            sat_shift = np.random.randint(5, 25)
            val_shift = np.random.randint(10, 30)
            
            strand_color = QColor.fromHsv(
                (base_color.hue() + hue_shift) % 360,
                max(0, min(255, base_color.saturation() + sat_shift)),
                max(0, min(255, base_color.value() + val_shift)),
                alpha
            )
            strand_thickness = max(0.3, (0.5 + np.random.rand()*0.5) / scale)
            p.setPen(QPen(strand_color, strand_thickness, cap=Qt.PenCapStyle.RoundCap))

            # Smooth, flowing curves
            num_segments = np.random.randint(3, 7)
            length_factor = r.width() * np.random.uniform(0.1, 0.3) / scale

            current_x, current_y = start_x, start_y
            current_angle = np.random.uniform(0, 2*np.pi)

            for _ in range(num_segments):
                # Control points for Bezier curve to make it wavy and smooth
                turn_angle = np.random.uniform(-np.pi / 3, np.pi / 3) # Less sharp turns
                current_angle += turn_angle
                
                ctrl_len1 = length_factor * np.random.uniform(0.3, 0.7)
                ctrl_angle1 = current_angle + np.random.uniform(-np.pi/6, np.pi/6)
                c1x = current_x + ctrl_len1 * np.cos(ctrl_angle1)
                c1y = current_y + ctrl_len1 * np.sin(ctrl_angle1)

                end_len = length_factor * np.random.uniform(0.5, 1.0)
                end_angle = current_angle + np.random.uniform(-np.pi/8, np.pi/8) # Smoother continuation
                ex = current_x + end_len * np.cos(end_angle)
                ey = current_y + end_len * np.sin(end_angle)
                
                ctrl_len2 = length_factor * np.random.uniform(0.3, 0.7)
                ctrl_angle2 = end_angle + np.random.uniform(-np.pi/6, np.pi/6) # Control point towards the end
                c2x = ex - ctrl_len2 * np.cos(ctrl_angle2) # Note: subtracted for smoother curve
                c2y = ey - ctrl_len2 * np.sin(ctrl_angle2)
                
                path.cubicTo(c1x, c1y, c2x, c2y, ex, ey)
                current_x, current_y = ex, ey
            
            p.drawPath(path)

        # Add a very subtle sheen layer
        sheen_gradient = QRadialGradient(r.center().x() + r.width()*0.1, r.center().y() - r.height()*0.1, r.width()*0.8)
        sheen_color1 = QColor(base_color.lighter(130))
        sheen_color1.setAlpha(int(25 * (scale/2))) # Very subtle
        sheen_color2 = QColor(base_color.lighter(110))
        sheen_color2.setAlpha(int(10* (scale/2)))

        sheen_gradient.setColorAt(0, sheen_color1)
        sheen_gradient.setColorAt(0.6, sheen_color2)
        sheen_gradient.setColorAt(1, QColor(0,0,0,0))
        p.setBrush(QBrush(sheen_gradient))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(r) 