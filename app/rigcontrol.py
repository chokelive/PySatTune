import socket

class RigCtlClient:
    def __init__(self, host='localhost', port=4532):
        self.host = host
        self.port = port

    def send_cmd(self, cmd):
        """Send command to rigctld and return the response."""
        try:
            with socket.create_connection((self.host, self.port), timeout=3) as sock:
                sock.sendall((cmd + '\n').encode())
                response = sock.recv(1024).decode().strip()
                return response
        except Exception as e:
            return f"Error: {e}"

    def get_freq(self):
        return self.send_cmd("f")

    def set_freq(self, freq_hz):
        return self.send_cmd(f"F {freq_hz}")

    def get_mode(self):
        return self.send_cmd("m")

    def set_mode(self, mode="USB", passband=1):
        return self.send_cmd(f"M {mode} {passband}")

    def ptt_on(self):
        return self.send_cmd("T 1")

    def ptt_off(self):
        return self.send_cmd("T 0")
    
    def set_split(self):
        self.send_cmd(f"S 1 VFOA")
        return self.send_cmd(f"S 1 VFOB")
    
    def reset_split(self):
        return self.send_cmd(f"S 0 VFOA")
    
    def set_split_freq(self, split_freq):
        return self.send_cmd(f"I {split_freq}")
    
    def set_split_mode(self, mode, passband=1):
        return self.send_cmd(f"X {mode} {passband}")
    
if __name__ == "__main__":
    rig = RigCtlClient()

    print("Current Frequency:", rig.get_freq())
    print("Current Mode:", rig.get_mode())

    print("Setting frequency to 14.074 MHz:", rig.set_freq(14074000))
    print("Setting mode to USB:", rig.set_mode("USB"))

    #print("PTT ON:", rig.ptt_on())
    # time.sleep(2)  # Optional delay
    #print("PTT OFF:", rig.ptt_off())