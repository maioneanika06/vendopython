from gpiozero import Button
from time import sleep

try:
    btn_left = Button(22, pull_up=True, bounce_time=0.1)
    btn_right = Button(23, pull_up=True, bounce_time=0.1)
except Exception as e:
    print(f"[ERROR] Hindi ma-setup ang pins: {e}")
    exit()

def left_pressed():
    print("?? [LEFT VENDO] Button on GPIO 22 is PRESSED!")

def right_pressed():
    print("?? [RIGHT VENDO] Button on GPIO 23 is PRESSED!")

# I-connect ang physical press sa functions sa taas
btn_left.when_pressed = left_pressed
btn_right.when_pressed = right_pressed

print("--- ??? HARDWARE BUTTON TESTER ---")
print("Listening for button presses on GPIO 22 and 23...")
print("Pindutin mo na yung mga physical buttons mo!")
print("(Press CTRL+C para i-stop ang program)\n")

try:
    while True:
        sleep(1)
except KeyboardInterrupt:
    print("\n[STOP] Exiting button tester. Good job, boss!")