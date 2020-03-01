import io
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

# https://raspberrypi.stackexchange.com/questions/22040/take-images-in-a-short-time-using-the-raspberry-pi-camera-module#22110
def init_camera():
    # Want to make sure we start with Camera A
    with SMBus(1) as bus:
        # Write a byte to address 70, offset 0
        data = 1
        bus.write_byte_data(int(i2c_addr, 16), 0, data)

    print('Successfully set up buses')
    global camera
    camera = PiCamera()
    camera.resolution = (640, 480)
    camera.framerate = 40
    sleep(2)
    print('Finished initing camera')

# Will take photos from both cameras "simultaneously"
def take_photos():
    start_time = time()
    flip_to_camera('A')
    camera.capture('testing_images/foo1.jpg')
    end_time = time()

    flip_to_camera('B')
    camera.capture('testing_images/foo2.jpg')
    print ("Took %s" % (end_time - start_time))

# https://picamera.readthedocs.io/en/release-1.3/recipes2.html#rapid-capture-and-processing
def filenames(frames):
    frame = 0
    while frame < frames:
        if frame % 2 == 0:
            flip_to_camera('A')
        else:
            flip_to_camera('B')
        yield 'testing_images/image%02d.jpg' % frame
        frame += 1

def take_n_photos(n):
    print('Starting to take photos')
    # Set up 40 in-memory streams
    start = time()
    camera.capture_sequence(filenames(n), use_video_port=True)
    finish = time()
    # How fast were we?
    print('Captured 40 images at %.2ffps' % (n / (finish - start)))

def flip_to_camera(cam):
    print('Fliping camera')
    # sleep(0.2)
    if cam == 'A':
        i2c_write(data=1)
        GPIO.output(channel_list[0], GPIO.LOW)
    elif cam == 'B':
        i2c_write(data=2)
        GPIO.output(channel_list[0], GPIO.HIGH)
    else:
        print("Wrong camera setting")

def i2c_write(data):
    successful_write = False
    retries = 1
    # Write a byte to address 70, offset 0
    while(successful_write == False and retries < 2):
        with SMBus(1) as bus:
            try:
                print('Writing to I2Cbus')
                bus.write_byte_data(int(i2c_addr, 16), 0, data)
                successful_write = True
            except IOError:
                # Want to handle Remote I/O
                # Error (EREMOTEIO) from I2C bus
                print('Error with I2C write, retrying...')
                sleep(0.5 * retries)
                retries += 1

def test_i2c_writes(writes):
    count = 0
    for i in range(0, writes):
        try:
            i2c_write(i % 2 + 1)
            count+=1
            sleep(0.5)
        except IOError:
            print('Error at cycle %d' % count)

def cleanup():
    global camera
    camera.close()
    GPIO.cleanup()

init_gpios()
init_camera()
# take_photos()
take_n_photos(20)
# test_i2c_writes(40)
cleanup()
