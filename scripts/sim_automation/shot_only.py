import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import ctypes, pyautogui
user32 = ctypes.windll.user32
h = user32.GetForegroundWindow()
n = user32.GetWindowTextLengthW(h)
buf = ctypes.create_unicode_buffer(n + 1)
user32.GetWindowTextW(h, buf, n + 1)
print('FG', repr(buf.value))
shot = sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\tsion\Projects\eni_dcim\drive_screen.png'
pyautogui.screenshot(shot)
print('SHOT', shot)
