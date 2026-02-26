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
        
        # time to wait for to trigger new event
        self.last_uid = None
        self.last_time = 0
        self.debounce_ms = 800
    
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
        
    def _debounced_connect(self, tag, user_cb):
        try:
            uid = tag.identifier.hex().upper()
        except:
            return False

        now = time.time() * 1000  # ms

        # If same UID within debounce window → ignore
        if uid == self.last_uid and (now - self.last_time) < self.debounce_ms:
            return False

        # Update debounce state
        self.last_uid = uid
        self.last_time = now

        # Fire the real callback
        user_cb(tag)

        return False

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
                        'on-connect': lambda tag: self._debounced_connect(tag, on_connect_cb),
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