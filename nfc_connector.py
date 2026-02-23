import nfc
import threading
import time
import usb

#
# nfc_connector.py NFCReader
# Wrapper for NFC Reader with libusbk
# Values hardcoded for ACR122U
# Authored for Tangible Cards
# Adapted from Proteus in conjunction with Waterloo
# 
class NFCReader:
    DEVICE_NAME = "usb:072F:2200"
    
    def __init__(self):
        self.device_name = self.DEVICE_NAME
        self.stop_event = threading.Event()
        self.thread = None
        self.clf = None
    
    def start(self, on_connect_cb):
        # NFC loop background thread
        # entry point
        self.thread = threading.Thread(
            target=self.reader_loop,
            args=(on_connect_cb,),
            daemon=True
        )
        self.thread.start()
        print(f"NFCReader: started thread for {self.device_name}")
    
    def stop(self):
        print("NFCReader: stopping…")
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.clf:
            try:
                self.clf.close()
            except Exception:
                pass
        print("NFCReader: stopped")
    
    def reader_loop(self, on_connect_cb):
        # On thread loop that
        # pools for continous nfc reads
        try:
            self.clf = nfc.ContactlessFrontend()
            if not self.clf.open(self.device_name):
                print(f"NFCReader: Could not open device {self.device_name}")
                return

            print(f"NFCReader: Opened {self.device_name}, waiting for taps…")

            while not self.stop_event.is_set():
                self.clf.connect(
                    rdwr={
                        'on-connect': on_connect_cb,
                        'iterations': 10,
                        'interval': 0.1,
                        'beep-on-connect': True,
                    }
                )
        except Exception as e:
            print(f"NFCReader: Error on {self.device_name}: {e}")
        finally:
            if self.clf:
                try:
                    self.clf.close()
                except Exception:
                    pass
            print("NFCReader: reader loop exited")