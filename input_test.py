import ctypes
import time
from ctypes import wintypes, c_size_t, c_void_p, create_string_buffer, windll
import win32gui
import win32process
import win32api
import win32con

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
user32 = ctypes.WinDLL('user32', use_last_error=True)

# Process access rights
PROCESS_ALL_ACCESS = (0x000F0000 | 0x00100000 | 0xFFF)
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008

# Keyboard input constants
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

VIRTUAL_KEYS = {
    'a': 0x41,
    's': 0x53,
    'd': 0x44,
    'w': 0x57,
    'f': 0x46,
    '1': 0x31,
    '2': 0x32,
    '6': 0x36
}

# C structures for SendInput
class MOUSEINPUT(ctypes.Structure):
    _fields_ = (("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)))

class KEYBDINPUT(ctypes.Structure):
    _fields_ = (("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)))

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = (("uMsg", wintypes.DWORD),
                ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD))

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = (("ki", KEYBDINPUT),
                   ("mi", MOUSEINPUT),
                   ("hi", HARDWAREINPUT))
    _anonymous_ = ("_input",)
    _fields_ = (("type", wintypes.DWORD),
                ("_input", _INPUT))

class MemoryAccess:
    def __init__(self):
        self.process_handle = None
        self.process_id = None
        
    def attach_to_process(self, window_title):
        """Connects to the process via window title"""
        hwnd = win32gui.FindWindow(None, window_title)
        if not hwnd:
            print(f"Window '{window_title}' not found")
            return False
            
        _, self.process_id = win32process.GetWindowThreadProcessId(hwnd)
        if not self.process_id:
            print("Could not determine process ID")
            return False
            
        self.process_handle = kernel32.OpenProcess(
            PROCESS_ALL_ACCESS,
            False,
            self.process_id
        )
        
        if not self.process_handle:
            error = ctypes.get_last_error()
            print(f"Could not open process: {error}")
            return False
            
        print(f"Successfully connected to process (PID: {self.process_id})")
        return True
        
    def write_memory(self, address, data):
        """Writes data to memory at the specified address"""
        if not self.process_handle:
            print("Not connected to process")
            return False
            
        bytes_written = c_size_t()
        
        if not kernel32.WriteProcessMemory(
            self.process_handle,
            address,
            data,
            len(data),
            ctypes.byref(bytes_written)
        ):
            print(f"Error writing to memory: {ctypes.get_last_error()}")
            return False
            
        return True

    def write_key_state(self, key, is_pressed):
        """Writes the key state"""
        if not self.process_handle:
            print("Not connected to process")
            return False
        
        key_code = VIRTUAL_KEYS.get(key.lower())
        if not key_code:
            print(f"Invalid key: {key}")
            return False
        
        # Write the state (0x8000 for pressed, 0x0000 for released)
        state = bytes([0x80, 0x00] if is_pressed else [0x00, 0x00])
        
        # Convert address to 64-bit pointer
        base_address = c_void_p(0x00007FFC982078E0)
        target_address = c_void_p(base_address.value + (key_code * 2))
        
        # Write directly to memory
        success = self.write_memory(target_address, state)
        
        if success:
            print(f"Key {key} {'pressed' if is_pressed else 'released'}")
        else:
            print(f"Error writing key {key}")
        
        return success
        
    def __del__(self):
        """Cleanup on exit"""
        if self.process_handle:
            kernel32.CloseHandle(self.process_handle)

def test_memory_key_press(key='a', duration=0.5):
    """Tests writing the key state directly to memory"""
    mem = MemoryAccess()
    if mem.attach_to_process("Temtem"):
        print(f"Testing key {key}...")
        
        # Press key
        if mem.write_key_state(key, True):
            time.sleep(duration)
            
            # Release key
            if mem.write_key_state(key, False):
                print(f"Test for key {key} completed")
                return True
    
    return False

if __name__ == "__main__":
    # Test Memory Key Press
    test_memory_key_press('a', 0.5)