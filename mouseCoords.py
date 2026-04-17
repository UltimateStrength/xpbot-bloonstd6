import pyautogui
import time

time.sleep(5)

x, y = pyautogui.position()

print(f"X = {x} Y = {y}")