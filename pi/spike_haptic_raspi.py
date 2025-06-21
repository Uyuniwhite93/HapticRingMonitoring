import socket, json, threading, time, subprocess
import numpy as np
import pygame

from player import HapticPlayModule

class SpikeHapticPi:
    def __init__(self):
        self.server_ip = "192.168.32.1" # 모든 인터페이스에서 접속
        self.server_port = 5005
        self.bufsize:int = 65_536
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.server_ip, self.server_port))
        self.sock.setblocking(False)

        self._stop = False
        # 수신 스레드 시작
        threading.Thread(target=self.callback_message, daemon=True).start()

        self.loaded_config = None # config 로드 후 저장할 변수
        self.load_config() # config 설정 로드 함수

        # Haptic 재생 모듈 생성
        self.hatpicPlayer = HapticPlayModule()

        # 프로그램 시작시 기본 PCM 데이터 생성
        snd_cfg = self.loaded_config["sound"]
        self.sa_sound = self.hatpicPlayer.create_sound_object(snd_cfg['sa_hz'], snd_cfg['sa_ms'], snd_cfg['sa_amp'], fade_out_ms=10)
        self.ra_sound = self.hatpicPlayer.create_sound_object(snd_cfg['ra_base_hz'] , snd_cfg['ra_ms'], snd_cfg['ra_base_amp'], fade_out_ms=10)     
        
    def callback_message(self):
        """스레드로 패킷을 받아서 JSON으로 파싱한 뒤 바로 출력"""
        recv_ns = 0
        while not self._stop:
            try:
                data, addr = self.sock.recvfrom(self.bufsize)
                # recv_ns = time.time_ns()              
            except BlockingIOError:
                time.sleep(0.01)
                continue

            try:
                msg = json.loads(data.decode("utf-8"))
                try:                 
                    import datetime
                    # lat_ms = (recv_ns - msg['ts_ns']) / 1_000_000
                    print(f"{datetime.datetime.now()} Data Recevied!")
                except:
                    pass
            except json.JSONDecodeError as e:
                print(f"[ERROR] JSON decode error: {e}")

            # print("[INFO] received:", msg)
            # lat_ms = (recv_ns - msg['ts_ns']) / 1_000_000
            # print(f"one-way latency ≈ {lat_ms:.3f} ms")
            if msg.get("command") :
                command = msg["command"]
                if command == "play":
                    sound = msg["types"]
                    if sound == "sa":
                        self.hatpicPlayer.play_sound(self.sa_sound, msg["channel_id"], msg["volume"])
                    elif sound == "ra":
                        self.hatpicPlayer.play_sound(self.ra_sound, msg["channel_id"], msg["volume"])
                elif command == "change":
                    self.ra_sound = self.hatpicPlayer.create_sound_object(msg["hz"], msg["ms"], msg["amp"], msg["fade_out_ms"])
                elif command == "reset":
                    self.reset_data_transfer()
                # ts_ns = time.time_ns()
                # try:
                    
                #     lat_ms = (ts_ns - recv_ns) / 1_000_000
                #     print(f"one-way latency ≈ {lat_ms:.3f} ms")
                # except:
                #     pass

    def load_config(self):
        """config 설정 파일을 로드"""
        file_path = "config.json"
        
        with open(file_path, "r", encoding="utf-8") as f:
            self.loaded_config = json.load(f)

    def close(self):
        self._stop = True
        try:
            self.sock.close()
        except OSError:
            pass

    def reset_data_transfer(self):
        off_command = subprocess.run(
            ["sudo", "./uhubctl", "-l", "1-1", "-p", "4", "-a", "off"],
            cwd="/home/pi/uhubctl",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        print(off_command.stdout)

        on_command = subprocess.run(
            ["sudo", "./uhubctl", "-l", "1-1", "-p", "4", "-a", "on"],
            cwd="/home/pi/uhubctl",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        print(on_command.stdout)

    # 데이터 신호 끊기
    # sudo ./uhubctl -l 1-1 -p 4 -a off
    # 데이터 신호 연결
    # sudo ./uhubctl -l 1-1 -p 4 -a on
        
if __name__ == '__main__' :
    print("서버 실행")
    __server = SpikeHapticPi()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        __server.close()    