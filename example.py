from MultiCam import multi_cam
from time import sleep

mc = multi_cam.MultiCam()

i = 0
while (i < 10):
    print("Starting example.py")
    left =  mc.get_left_photo()
    print(f'Left {left}')
    right =  mc.get_right_photo()
    print(f'Right {right}')
    print("")
    sleep(2)
    i = i + 1

mc._cleanup()
