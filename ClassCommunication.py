import socket, threading, struct, time, json

class CommunicationModule() :
    def __init__(self, udp_ip:str = "192.168.32.1", udp_port:int = 5005):
        self.udp_ip = udp_ip
        self.udp_port = udp_port
        self.udp_bind = (udp_ip, udp_port)
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.setblocking(False)  # 논블로킹

    def send_json(self, msg_dict:dict):
        """딕셔너리를 JSON으로 바꿔 UDP 패킷에 실어 보냄"""
        payload = json.dumps(msg_dict, separators=(",", ":")).encode("utf-8")
        if len(payload) > 65_507 : 
            raise ValueError("payload too big for one UDP packet")
        self.udp_sock.sendto(payload, self.udp_bind)
        print(f"succeed to send")

    def send_dynamic_params(self, **kwargs:any) -> None:
        print("Parametes: ", kwargs)
        self.send_json(kwargs)

    def send_data_reset_signal(self):
        reset_command = "reset".encode('utf-8')
        self.udp_sock.sendto(reset_command, self.udp_bind)