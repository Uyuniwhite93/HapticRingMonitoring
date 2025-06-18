"""
Driving Simulator with Separate AC Touch Panel - 별도 터치 공조기 패널
"""

from metadrive import MetaDriveEnv
import time
import threading
import random
import queue

# 공조기 상태와 퀴즈 정보를 공유하기 위한 큐
ac_status_queue = queue.Queue()
quiz_queue = queue.Queue()

class DrivingSimulator:
    def __init__(self):
        # Keyboard input state for vehicle
        self.keys_pressed = {
            'w': False, 'a': False, 's': False, 'd': False
        }
        
        # UI overlays for driving only
        self.overlays = {}
        
    def setup_config(self):
        return {
            "use_render": True,
            "traffic_density": 0.1,
            "map": "OOOOOOOOOO",
            "manual_control": True,
            "start_seed": 42,
            "window_size": (1200, 800),
            "horizon": 999999,
            
            # First person view
            "prefer_track_agent": None,
            "camera_height": 1.2,
            "camera_dist": 0.8,
            "camera_pitch": 0,
            "camera_smooth": False,
            "use_chase_camera_follow_lane": False,
            
            # Vehicle settings
            "vehicle_config": {
                "enable_reverse": False,
                "show_navi_mark": False,
                "show_dest_mark": False,
                "show_line_to_dest": False,
            },
            
            # Interface settings
            "show_interface": True,
            "interface_panel": ["dashboard"],
            
            # Never terminate
            "crash_vehicle_done": False,
            "crash_object_done": False,
            "out_of_road_done": False,
            
            # Zero penalties
            "crash_vehicle_penalty": 0,
            "crash_object_penalty": 0,
            "out_of_road_penalty": 0,
        }
    
    def setup_keyboard_bindings(self, env):
        """Setup keyboard event handling for vehicle only"""
        try:
            if hasattr(env.engine, 'accept'):
                # Vehicle controls only
                env.engine.accept('w', self.on_key_press, ['w'])
                env.engine.accept('w-up', self.on_key_release, ['w'])
                env.engine.accept('a', self.on_key_press, ['a'])
                env.engine.accept('a-up', self.on_key_release, ['a'])
                env.engine.accept('s', self.on_key_press, ['s'])
                env.engine.accept('s-up', self.on_key_release, ['s'])
                env.engine.accept('d', self.on_key_press, ['d'])
                env.engine.accept('d-up', self.on_key_release, ['d'])
                
                print("Vehicle keyboard bindings setup complete")
        except Exception as e:
            print(f"Keyboard setup error: {e}")
    
    def on_key_press(self, key):
        """Handle key press for vehicle"""
        if key in self.keys_pressed:
            self.keys_pressed[key] = True
    
    def on_key_release(self, key):
        """Handle key release for vehicle"""
        if key in self.keys_pressed:
            self.keys_pressed[key] = False
    
    def setup_ui_overlays(self, env):
        """Setup UI overlays for driving info only"""
        try:
            if hasattr(env.engine, 'taskMgr'):
                from direct.gui.DirectGui import DirectLabel
                
                # Vehicle controls guide
                self.overlays['controls'] = DirectLabel(
                    text="VEHICLE CONTROLS: W=Forward A=Left S=Backward D=Right",
                    scale=0.04,
                    pos=(0, 0, 0.9),
                    text_fg=(1, 1, 1, 1),
                    text_bg=(0, 0, 0, 0.7),
                    relief=None,
                    text_align=1
                )
                
                # AC status display (from separate panel)
                self.overlays['ac_status'] = DirectLabel(
                    text="AC Panel: Starting...",
                    scale=0.04,
                    pos=(-0.9, 0, -0.8),
                    text_fg=(1, 1, 0, 1),
                    text_bg=(0, 0, 0, 0.8),
                    relief=None,
                    text_align=0
                )
                
                # Quiz display (from AC panel)
                self.overlays['quiz'] = DirectLabel(
                    text="AC Quiz will appear on touch panel",
                    scale=0.04,
                    pos=(0, 0, 0.8),
                    text_fg=(1, 1, 0, 1),
                    text_bg=(1, 0, 0, 0.8),
                    relief=None,
                    text_align=1
                )
                
                # Driving status
                self.overlays['driving'] = DirectLabel(
                    text="Auto Driving",
                    scale=0.04,
                    pos=(0.9, 0, -0.8),
                    text_fg=(0, 1, 0, 1),
                    text_bg=(0, 0, 0, 0.7),
                    relief=None,
                    text_align=2
                )
                
                print("Driving UI overlays created")
        except Exception as e:
            print(f"UI setup error: {e}")
    
    def update_driving_status(self):
        """Update driving status"""
        if 'driving' in self.overlays:
            active_keys = [k.upper() for k, v in self.keys_pressed.items() if v]
            if active_keys:
                status_text = f"Manual: {'+'.join(active_keys)}"
                self.overlays['driving']['text_fg'] = (1, 1, 0, 1)
            else:
                status_text = "Auto Driving"
                self.overlays['driving']['text_fg'] = (0, 1, 0, 1)
            
            self.overlays['driving']['text'] = status_text
    
    def update_displays_from_queues(self):
        """Update displays from AC panel queues"""
        # Update AC status from queue
        try:
            while not ac_status_queue.empty():
                ac_status = ac_status_queue.get_nowait()
                if 'ac_status' in self.overlays:
                    self.overlays['ac_status']['text'] = f"AC: {ac_status}"
        except queue.Empty:
            pass
        
        # Update quiz from queue
        try:
            while not quiz_queue.empty():
                quiz_info = quiz_queue.get_nowait()
                if 'quiz' in self.overlays:
                    self.overlays['quiz']['text'] = quiz_info
        except queue.Empty:
            pass
    
    def get_vehicle_action(self):
        """Get vehicle action from keyboard input"""
        throttle = 0.0
        steering = 0.0
        
        if self.keys_pressed['w']:  # Forward
            throttle = 0.6
        if self.keys_pressed['s']:  # Backward
            throttle = -0.3
        if self.keys_pressed['a']:  # Left
            steering = -0.5
        if self.keys_pressed['d']:  # Right
            steering = 0.5
        
        # Auto forward if no input
        if not any(self.keys_pressed.values()):
            throttle = 0.2
        
        return [throttle, steering]
    
    def cleanup_overlays(self):
        """Clean up UI overlays"""
        try:
            for overlay in self.overlays.values():
                if overlay:
                    overlay.destroy()
        except:
            pass
    
    def run(self):
        """Run the driving simulator"""
        config = self.setup_config()
        env = MetaDriveEnv(config)
        
        try:
            print("Driving Simulator with Separate AC Touch Panel Starting...")
            print("Vehicle Controls: W(Forward) A(Left) S(Backward) D(Right)")
            print("AC Touch Panel will open in separate window")
            print("Close window or Ctrl+C to exit")
            
            # Start AC touch panel in separate thread
            try:
                from ac_touch_panel import start_ac_touch_panel
                ac_thread = threading.Thread(
                    target=start_ac_touch_panel, 
                    args=(ac_status_queue, quiz_queue), 
                    daemon=True
                )
                ac_thread.start()
                print("AC Touch Panel started in separate window")
            except ImportError:
                print("AC Touch Panel module not found")
            except Exception as e:
                print(f"AC Touch Panel error: {e}")
            
            obs, info = env.reset()
            
            # Setup UI and controls
            self.setup_ui_overlays(env)
            self.setup_keyboard_bindings(env)
            
            step = 0
            
            while True:
                # Get vehicle action
                action = self.get_vehicle_action()
                obs, reward, terminated, truncated, info = env.step(action)
                
                # Update displays
                self.update_driving_status()
                self.update_displays_from_queues()
                
                # Get vehicle speed
                vehicle = env.agent
                current_speed = 0
                if vehicle is not None:
                    current_speed = vehicle.speed * 3.6 if hasattr(vehicle, 'speed') else 0
                
                step += 1
                
                # Status output every 300 steps
                if step % 300 == 0:
                    active_keys = [k.upper() for k, v in self.keys_pressed.items() if v]
                    control_info = f"Keys: {'+'.join(active_keys) if active_keys else 'AUTO'}"
                    print(f"Step {step}: Speed {current_speed:.1f} km/h | {control_info}")
                
                time.sleep(0.01)
            
        except KeyboardInterrupt:
            print("\nTerminated by user!")
        except Exception as e:
            print(f"Error occurred: {e}")
        finally:
            self.cleanup_overlays()
            env.close()

def main():
    simulator = DrivingSimulator()
    simulator.run()

if __name__ == "__main__":
    main() 