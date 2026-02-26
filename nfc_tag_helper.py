import nfc
import threading
import time
import usb
import re

# -----------------------------------------
# NFCReader class (your existing code)
# -----------------------------------------
class NFCReader:
    DEVICE_NAME = "usb:072F:2200"
    
    def __init__(self):
        self.device_name = self.DEVICE_NAME
        self.stop_event = threading.Event()
        self.thread = None
        self.clf = None
    
    def start(self, on_connect_cb):
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


# -----------------------------------------
# Helper script logic
# -----------------------------------------

def extract_mac_from_tag(tag):
    if not tag.ndef:
        return None

    for record in tag.ndef.records:
        # Decode safely
        try:
            data = record.data.decode('ascii', errors='ignore')
        except:
            continue

        # 1. Your original format: mac=XXXXXXXXXXXX
        m = re.search(r'mac=([A-Fa-f0-9]{12})', data)
        if m:
            return m.group(1)

        # 2. Minew URI formats
        m = re.search(r'([A-Fa-f0-9]{12})', data)
        if m:
            return m.group(1)

        # 3. Raw hex payload
        if len(data) >= 12 and all(c in "0123456789ABCDEFabcdef" for c in data.strip()):
            return data.strip()[:12]

    return None

def on_tag_connect(tag):
    """
    Called every time a tag is tapped.
    Prints the UID in hex.
    """
    try:
        uid_bytes = tag.identifier
        uid_hex = uid_bytes.hex().upper()
        print(f"\n✔ Tag detected! UID = {uid_hex} MAC = {extract_mac_from_tag(tag)}")
    except Exception as e:
        print(f"Error reading tag UID: {e}")

    # Returning True keeps the tag connected briefly; False disconnects immediately.
    return False


if __name__ == "__main__":
    print("=== NFC UID Capture Tool ===")
    print("Tap each tag to print its UID.")
    print("Press Ctrl+C to exit.\n")

    reader = NFCReader()
    reader.start(on_tag_connect)

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping NFC reader…")
        reader.stop()