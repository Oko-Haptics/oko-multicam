from time import sleep
from time import time
from picamera import PiCamera
from smbus2 import SMBus
import RPi.GPIO as GPIO

i2c_addr = "0x70"
channel_list = [4, 17]
camera = None

def init_gpios():
    # Want to use BCM numbering for the GPIOs
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(channel_list, GPIO.OUT, initial=GPIO.LOW)
    # GPIO.output(channel_list[0], 0)
    # GPIO.output(channel_list[1], 0)

def init_camera():
    # Want to make sure we start with Camera A
    with SMBus(1) as bus:
        # Write a byte to address 70, offset 0
        data = 1
        bus.write_byte_data(int(i2c_addr, 16), 0, data)

    global camera
    camera = PiCamera()
    camera.resolution = (1024, 768) # Check resolution
    sleep(2)

# Will take photos from both cameras "simultaneously"
def take_photos():
    start_time = time()
    flip_to_camera('A')
    camera.capture('testing_images/foo1.jpg')

    flip_to_camera('B')
    camera.capture('testing_images/foo2.jpg')
    end_time = time()
    print ("Took %s" % (end_time - start_time))

def flip_to_camera(cam):
    with SMBus(1) as bus:
        if cam == 'A':
            # Write a byte to address 70, offset 0
            data = 1
            GPIO.output(channel_list[0], GPIO.LOW)
        elif cam == 'B':
            data = 2
            GPIO.output(channel_list[0], GPIO.HIGH)
        else:
            print("Wrong camera setting")
        bus.write_byte_data(int(i2c_addr, 16), 0, data)

init_gpios()
init_camera()
take_photos()

# Cleanup channels that we've used
GPIO.cleanup()
