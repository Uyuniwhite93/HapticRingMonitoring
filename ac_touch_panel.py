import tkinter as tk
from tkinter import ttk
import threading
import time
import random
import queue

class ACTouchPanel:
    def __init__(self, status_queue=None, quiz_queue=None):
        self.status_queue = status_queue
        self.quiz_queue = quiz_queue
        
        # AC 상태
        self.ac_on = False
        self.temperature = 22
        self.fan_speed = 1
        self.ac_mode = "Auto"
        
        # 퀴즈 시스템
        self.quiz_active = False
        self.current_question = ""
        self.quiz_target = ""
        self.quiz_timer = 0
        
        # 터치스크린 UI 설정
        self.root = tk.Tk()
        self.root.title("🚗 Vehicle AC Touch Panel")
        self.root.geometry("800x600")
        self.root.configure(bg='#1a1a1a')  # 어두운 배경
        
        # 포커스 설정: 포커스를 가져가지 않음
        self.root.attributes('-topmost', True)  # 항상 위에
        self.root.focus_set = lambda: None  # 포커스 설정 비활성화
        self.root.grab_set = lambda: None   # 포커스 잡기 비활성화
        
        # 터치스크린 스타일
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.setup_ui()
        self.start_quiz_system()
        self.update_status()
        
        # 창 이벤트 바인딩
        self.root.bind('<FocusIn>', self.on_focus_in)
        
    def on_focus_in(self, event):
        """포커스가 들어왔을 때 즉시 포커스를 해제"""
        try:
            # 포커스를 다른 창으로 이동 (운전 시뮬레이션 창으로)
            self.root.after(1, lambda: self.root.focus_force() and self.root.lower())
        except:
            pass
        
    def setup_ui(self):
        """터치스크린 UI 설정"""
        # 메인 프레임
        main_frame = tk.Frame(self.root, bg='#1a1a1a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # 제목
        title_label = tk.Label(main_frame, text="AIR CONDITIONER", 
                              font=("Arial", 24, "bold"), 
                              bg='#1a1a1a', fg='#00ff00')
        title_label.pack(pady=(0, 20))
        
        # 포커스 방지 안내
        focus_label = tk.Label(main_frame, text="Touch Panel - Vehicle controls remain active", 
                              font=("Arial", 10), 
                              bg='#1a1a1a', fg='#888888')
        focus_label.pack(pady=(0, 10))
        
        # 상태 표시 패널
        status_frame = tk.Frame(main_frame, bg='#2d2d2d', relief='raised', bd=3)
        status_frame.pack(fill='x', pady=(0, 20))
        
        self.status_label = tk.Label(status_frame, text="AC: OFF", 
                                    font=("Arial", 18, "bold"), 
                                    bg='#2d2d2d', fg='#ff4444')
        self.status_label.pack(pady=15)
        
        # 전원 버튼 (큰 터치 버튼)
        power_frame = tk.Frame(main_frame, bg='#1a1a1a')
        power_frame.pack(pady=(0, 20))
        
        self.power_button = tk.Button(power_frame, text="POWER\nOFF", 
                                     command=self.toggle_power,
                                     font=("Arial", 16, "bold"),
                                     bg='#ff4444', fg='white',
                                     width=12, height=3,
                                     relief='raised', bd=5,
                                     takefocus=False)  # 포커스 받지 않음
        self.power_button.pack()
        
        # 컨트롤 패널
        control_frame = tk.Frame(main_frame, bg='#1a1a1a')
        control_frame.pack(fill='both', expand=True)
        
        # 온도 조절
        temp_frame = tk.Frame(control_frame, bg='#2d2d2d', relief='raised', bd=3)
        temp_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(temp_frame, text="TEMPERATURE", font=("Arial", 14, "bold"), 
                bg='#2d2d2d', fg='white').pack(pady=(10, 5))
        
        self.temp_display = tk.Label(temp_frame, text="22°C", 
                                    font=("Arial", 24, "bold"),
                                    bg='#2d2d2d', fg='#00aaff')
        self.temp_display.pack(pady=10)
        
        temp_btn_frame = tk.Frame(temp_frame, bg='#2d2d2d')
        temp_btn_frame.pack(pady=(0, 10))
        
        tk.Button(temp_btn_frame, text="▲", command=self.temp_up,
                 font=("Arial", 16, "bold"), bg='#ff6600', fg='white',
                 width=4, height=2, takefocus=False).pack(side='left', padx=5)
        
        tk.Button(temp_btn_frame, text="▼", command=self.temp_down,
                 font=("Arial", 16, "bold"), bg='#0066ff', fg='white',
                 width=4, height=2, takefocus=False).pack(side='left', padx=5)
        
        # 풍량 조절
        fan_frame = tk.Frame(control_frame, bg='#2d2d2d', relief='raised', bd=3)
        fan_frame.pack(side='left', fill='both', expand=True, padx=(5, 5))
        
        tk.Label(fan_frame, text="FAN SPEED", font=("Arial", 14, "bold"), 
                bg='#2d2d2d', fg='white').pack(pady=(10, 5))
        
        self.fan_display = tk.Label(fan_frame, text="1", 
                                   font=("Arial", 24, "bold"),
                                   bg='#2d2d2d', fg='#00ff00')
        self.fan_display.pack(pady=10)
        
        fan_btn_frame = tk.Frame(fan_frame, bg='#2d2d2d')
        fan_btn_frame.pack(pady=(0, 10))
        
        tk.Button(fan_btn_frame, text="▲", command=self.fan_up,
                 font=("Arial", 16, "bold"), bg='#00aa00', fg='white',
                 width=4, height=2, takefocus=False).pack(side='left', padx=5)
        
        tk.Button(fan_btn_frame, text="▼", command=self.fan_down,
                 font=("Arial", 16, "bold"), bg='#aa0000', fg='white',
                 width=4, height=2, takefocus=False).pack(side='left', padx=5)
        
        # 모드 선택
        mode_frame = tk.Frame(control_frame, bg='#2d2d2d', relief='raised', bd=3)
        mode_frame.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(mode_frame, text="MODE", font=("Arial", 14, "bold"), 
                bg='#2d2d2d', fg='white').pack(pady=(10, 5))
        
        self.mode_display = tk.Label(mode_frame, text="Auto", 
                                    font=("Arial", 18, "bold"),
                                    bg='#2d2d2d', fg='#ffaa00')
        self.mode_display.pack(pady=10)
        
        tk.Button(mode_frame, text="CHANGE\nMODE", command=self.change_mode,
                 font=("Arial", 12, "bold"), bg='#aa00aa', fg='white',
                 width=8, height=3, takefocus=False).pack(pady=(0, 10))
        
        # 퀴즈 패널
        quiz_frame = tk.Frame(main_frame, bg='#4d0000', relief='raised', bd=5)
        quiz_frame.pack(fill='x', pady=(20, 0))
        
        tk.Label(quiz_frame, text="🎯 AC OPERATION QUIZ", 
                font=("Arial", 16, "bold"), bg='#4d0000', fg='#ffff00').pack(pady=5)
        
        self.quiz_label = tk.Label(quiz_frame, text="Quiz will start soon...", 
                                  font=("Arial", 12), bg='#4d0000', fg='white',
                                  wraplength=700, justify='center')
        self.quiz_label.pack(pady=5)
        
        self.quiz_timer_label = tk.Label(quiz_frame, text="", 
                                        font=("Arial", 14, "bold"), 
                                        bg='#4d0000', fg='#ff0000')
        self.quiz_timer_label.pack(pady=2)
        
        self.quiz_result_label = tk.Label(quiz_frame, text="", 
                                         font=("Arial", 12, "bold"), bg='#4d0000')
        self.quiz_result_label.pack(pady=5)
    
    def toggle_power(self):
        """전원 토글 - 포커스 복원"""
        self.ac_on = not self.ac_on
        if self.ac_on:
            self.power_button.config(text="POWER\nON", bg='#00aa00')
        else:
            self.power_button.config(text="POWER\nOFF", bg='#ff4444')
        
        self.update_status()
        self.check_quiz_answer()
        print(f"AC Power: {'ON' if self.ac_on else 'OFF'}")
        
        # 포커스를 운전 시뮬레이션으로 되돌리기
        self.restore_driving_focus()
    
    def temp_up(self):
        """온도 증가 - 포커스 복원"""
        if self.temperature < 30:
            self.temperature += 1
            self.temp_display.config(text=f"{self.temperature}°C")
            self.update_status()
            self.check_quiz_answer()
            print(f"Temperature: {self.temperature}°C")
            self.restore_driving_focus()
    
    def temp_down(self):
        """온도 감소 - 포커스 복원"""
        if self.temperature > 16:
            self.temperature -= 1
            self.temp_display.config(text=f"{self.temperature}°C")
            self.update_status()
            self.check_quiz_answer()
            print(f"Temperature: {self.temperature}°C")
            self.restore_driving_focus()
    
    def fan_up(self):
        """풍량 증가 - 포커스 복원"""
        if self.fan_speed < 5:
            self.fan_speed += 1
            self.fan_display.config(text=str(self.fan_speed))
            self.update_status()
            self.check_quiz_answer()
            print(f"Fan Speed: {self.fan_speed}")
            self.restore_driving_focus()
    
    def fan_down(self):
        """풍량 감소 - 포커스 복원"""
        if self.fan_speed > 1:
            self.fan_speed -= 1
            self.fan_display.config(text=str(self.fan_speed))
            self.update_status()
            self.check_quiz_answer()
            print(f"Fan Speed: {self.fan_speed}")
            self.restore_driving_focus()
    
    def change_mode(self):
        """모드 변경 - 포커스 복원"""
        modes = ["Auto", "Cool", "Heat", "Fan"]
        current_idx = modes.index(self.ac_mode)
        next_idx = (current_idx + 1) % len(modes)
        self.ac_mode = modes[next_idx]
        self.mode_display.config(text=self.ac_mode)
        self.update_status()
        self.check_quiz_answer()
        print(f"Mode: {self.ac_mode}")
        self.restore_driving_focus()
    
    def restore_driving_focus(self):
        """운전 시뮬레이션 창으로 포커스 복원"""
        try:
            # 공조기 창을 뒤로 보내기
            self.root.after(10, lambda: self.root.lower())
        except:
            pass
    
    def update_status(self):
        """상태 업데이트"""
        if self.ac_on:
            status_text = f"AC: ON | {self.temperature}°C | Fan {self.fan_speed} | {self.ac_mode}"
            self.status_label.config(text=status_text, fg='#00ff00')
        else:
            status_text = "AC: OFF"
            self.status_label.config(text=status_text, fg='#ff4444')
        
        # 상태를 큐로 전송
        if self.status_queue:
            self.status_queue.put(status_text)
    
    def start_quiz_system(self):
        """퀴즈 시스템 시작"""
        def quiz_loop():
            ac_quizzes = [
                ("Turn ON the air conditioner!", "power_on"),
                ("Set temperature to 25°C!", "temp_25"),
                ("Set temperature to 20°C!", "temp_20"),
                ("Set temperature to 18°C!", "temp_18"),
                ("Set fan speed to 3!", "fan_3"),
                ("Set fan speed to 5!", "fan_5"),
                ("Set fan speed to 1!", "fan_1"),
                ("Change mode to Cool!", "mode_cool"),
                ("Change mode to Heat!", "mode_heat"),
                ("Change mode to Auto!", "mode_auto"),
                ("Change mode to Fan!", "mode_fan"),
                ("Turn OFF the air conditioner!", "power_off"),
            ]
            
            while True:
                time.sleep(15)  # 15초마다 퀴즈
                if not self.quiz_active:
                    question, target = random.choice(ac_quizzes)
                    self.current_question = question
                    self.quiz_target = target
                    self.quiz_active = True
                    self.quiz_timer = 10  # 10초 제한
                    
                    # 퀴즈 표시
                    try:
                        self.root.after(0, self.show_quiz)
                    except:
                        pass
                    
                    # 퀴즈 정보를 시뮬레이션으로 전송
                    if self.quiz_queue:
                        quiz_info = f"AC QUIZ (10s): {question}"
                        self.quiz_queue.put(quiz_info)
                    
                    print(f"🎯 AC Quiz: {question}")
                    
                    # 타이머 시작
                    self.start_quiz_timer()
        
        quiz_thread = threading.Thread(target=quiz_loop, daemon=True)
        quiz_thread.start()
    
    def show_quiz(self):
        """퀴즈 표시"""
        self.quiz_label.config(text=self.current_question, fg='#ffff00')
        self.quiz_result_label.config(text="", fg='white')
        
        # 타이머 업데이트 시작
        self.update_timer_display()
    
    def update_timer_display(self):
        """타이머 표시 업데이트"""
        if self.quiz_active and self.quiz_timer > 0:
            self.quiz_timer_label.config(text=f"⏰ {self.quiz_timer}s remaining")
            try:
                self.root.after(1000, self.update_timer_display)
            except:
                pass
        else:
            self.quiz_timer_label.config(text="")
    
    def start_quiz_timer(self):
        """퀴즈 타이머 시작"""
        def timer():
            while self.quiz_timer > 0 and self.quiz_active:
                time.sleep(1)
                self.quiz_timer -= 1
                if self.quiz_timer <= 0 and self.quiz_active:
                    try:
                        self.root.after(0, self.timeout_quiz)
                    except:
                        pass
        
        timer_thread = threading.Thread(target=timer, daemon=True)
        timer_thread.start()
    
    def timeout_quiz(self):
        """퀴즈 시간 초과"""
        if self.quiz_active:
            self.quiz_active = False
            result_text = f"⏰ TIME OUT! Failed: {self.current_question}"
            self.quiz_result_label.config(text="❌ TIME OUT!", fg='#ff0000')
            
            # 결과를 시뮬레이션으로 전송
            if self.quiz_queue:
                self.quiz_queue.put(result_text)
            
            print(f"❌ Quiz timeout! Failed: {self.current_question}")
            
            # 3초 후 정리
            def clear_quiz():
                time.sleep(3)
                try:
                    self.root.after(0, lambda: self.quiz_label.config(text="Next quiz coming soon...", fg='white'))
                    self.root.after(0, lambda: self.quiz_result_label.config(text=""))
                except:
                    pass
                if self.quiz_queue:
                    self.quiz_queue.put("Next AC quiz coming soon...")
            
            clear_thread = threading.Thread(target=clear_quiz, daemon=True)
            clear_thread.start()
    
    def check_quiz_answer(self):
        """퀴즈 정답 확인"""
        if not self.quiz_active:
            return
        
        correct = False
        
        if self.quiz_target == "power_on" and self.ac_on:
            correct = True
        elif self.quiz_target == "power_off" and not self.ac_on:
            correct = True
        elif self.quiz_target.startswith("temp_"):
            target_temp = int(self.quiz_target.split("_")[1])
            if self.temperature == target_temp:
                correct = True
        elif self.quiz_target.startswith("fan_"):
            target_fan = int(self.quiz_target.split("_")[1])
            if self.fan_speed == target_fan:
                correct = True
        elif self.quiz_target.startswith("mode_"):
            target_mode = self.quiz_target.split("_")[1].capitalize()
            if self.ac_mode == target_mode:
                correct = True
        
        if correct:
            self.quiz_active = False
            result_text = f"✅ CORRECT! Well done: {self.current_question}"
            self.quiz_result_label.config(text="✅ CORRECT!", fg='#00ff00')
            
            # 결과를 시뮬레이션으로 전송
            if self.quiz_queue:
                self.quiz_queue.put(result_text)
            
            print(f"✅ Quiz CORRECT! {self.current_question}")
            
            # 2초 후 정리
            def clear_quiz():
                time.sleep(2)
                try:
                    self.root.after(0, lambda: self.quiz_label.config(text="Next quiz coming soon...", fg='white'))
                    self.root.after(0, lambda: self.quiz_result_label.config(text=""))
                except:
                    pass
                if self.quiz_queue:
                    self.quiz_queue.put("Next AC quiz coming soon...")
            
            clear_thread = threading.Thread(target=clear_quiz, daemon=True)
            clear_thread.start()
    
    def run(self):
        """터치 패널 실행"""
        print("🚗 AC Touch Panel started")
        print("🎯 Complete AC operation quizzes on the touch panel!")
        print("💡 Vehicle controls remain active while using touch panel")
        self.root.mainloop()

def start_ac_touch_panel(status_queue, quiz_queue):
    """터치 패널 시작 함수"""
    panel = ACTouchPanel(status_queue, quiz_queue)
    panel.run()

if __name__ == "__main__":
    panel = ACTouchPanel()
    panel.run() 