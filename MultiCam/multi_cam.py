import atexit
import io
import threading
from time import sleep
from time import time
from picamera import PiCamera
from smbus2 import SMBus
import RPi.GPIO as GPIO

# Might need a custom `write` impl here
# But that would only be used if the caller
# used capture_sequence(MultiCam Obj)
# Maybe we can have a wrapper class
class MultiCam:

    # I want a thread that continually
    # updates the left and right photos
    def __init__(self):
        self.camera = None
        # 'A' => False
        # 'B' => True
        self.curr_camera = False
        self.right_photo = 0 # None
        self.left_photo = 0 #None

        self.i2c_addr = "0x70"
        self.channel_list = [4, 17]

        self._init_gpios()
        self._init_camera()

        atexit.register(self._cleanup)

        # Starts background thread dedicated to taking images
        self.processor = CaptureImages(self, self.camera)

    # Get the most recently taken photo
    # from the left camera
    def get_left_photo(self):
        print(f"Get left photo {self.left_photo}")
        return self.left_photo

    # Get the most recently taken photo
    # from the right camera
    def get_right_photo(self):
        print(f"Get right photo {self.right_photo}")
        return self.right_photo

    def take_photo(self):
        self.camera.capture('testing_images/multicam.jpg')

    def take_photos(self, n):
        print("Taking photos")
        self.camera.capture('testing_images/multicam1.jpg')

        self._write_i2c(2)
        GPIO.output(self.channel_list[0], GPIO.HIGH)
        self.camera.capture('testing_images/multicam2.jpg')

    # https://raspberrypi.stackexchange.com/questions/22040/take-images-in-a-short-time-using-the-raspberry-pi-camera-module#22110
    def _init_camera(self):
        # Want to make sure we start with Camera A
        with SMBus(1) as bus:
            # Write a byte to address 70, offset 0
            data = 1
            bus.write_byte_data(int(self.i2c_addr, 16), 0, data)

        self.camera = PiCamera()
        self.camera.resolution = (640, 480)
        self.camera.framerate = 10
        sleep(2)

    def _init_gpios(self):
        # Want to use BCM numbering for the GPIOs
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.channel_list, GPIO.OUT, initial=GPIO.LOW)

    def _write_i2c(self, data):
        successful_write = False
        retries = 1
        # Write a byte to address 70, offset 0
        while(successful_write == False and retries < 3):
            with SMBus(1) as bus:
                try:
                    print('Writing to I2Cbus')
                    bus.write_byte_data(int(self.i2c_addr, 16), 0, data)
                    successful_write = True
                except IOError:
                    # Want to handle Remote I/O
                    # Error (EREMOTEIO) from I2C bus
                    print('Error with I2C write, retrying...')
                    sleep(0.5 * retries)
                    retries += 1

    def _switch_camera(self):
        print("Switching camera")
        data = int(self.curr_camera) + 1
        print(f"Data {data}")
        self._write_i2c(data)
        print(f"GPIO Output / Input {GPIO.input(self.channel_list[0])}")
        GPIO.output(self.channel_list[0], not GPIO.input(self.channel_list[0]))
        print("Curr Camera")
        self.curr_camera = not self.curr_camera
        sleep(0.2)

    # Useful for using a specific camera
    def _use_camera(self, cam):
        if cam == 'A':
            write_i2c(data=1)
            GPIO.output(channel_list[0], GPIO.LOW)
        elif cam == 'B':
            write_i2c(data=2)
            GPIO.output(channel_list[0], GPIO.HIGH)
        else:
            print("Wrong camera setting")
        sleep(0.1)

    def _cleanup(self):
        self.camera.close()
        GPIO.cleanup()

        self.processor.terminated = True
        self.processor.join()

class CaptureImages(threading.Thread):
    def __init__(self, owner, camera):
        print("Init Capture Images")
        super(CaptureImages, self).__init__()

        self.terminated = False
        self.camera = camera
        self.owner = owner # Owner is the MultiCam library

        print(f"Init Owner Left: {self.owner.left_photo}")
        print(f"Init Owner Right: {self.owner.right_photo}")

        self.start() # Will call the run method

    def run(self):
        while not self.terminated:
            self.owner.left_photo += 1
            # sleep(1)
            self.owner.right_photo += 1
            sleep(1)

            # image_L = self.camera.capture()
            # self.owner.left = image_L
            # MultiCam.left = image_L
            # # Maybe have a delay here
            # image_R = self.camera.capture()
            # MultiCam.right = image_R
            # self.owner.right = image_R

# Will take photos from both cameras "simultaneously"
def take_photos():
    start_time = time()
    switch_cam(GPIO.LOW, 1)
    camera.capture('testing_images/foo1.jpg')
    end_time = time()

    switch_cam(GPIO.HIGH, 2)
    camera.capture('testing_images/foo2.jpg')
    print ("Took %s" % (end_time - start_time))

def take_photos_stream():
    temp_streamA = io.BytesIO()
    temp_streamB = io.BytesIO()

    start_time = time()
    switch_cam(GPIO.LOW, 1)
    camera.capture(temp_streamA, 'jpeg')

    switch_cam(GPIO.HIGH, 2)
    camera.capture(temp_streamB, 'jpeg')
    end_time = time()
    print ("Stream Took %s" % (end_time - start_time))
    print(f'{str(temp_streamA) == str(temp_streamB)}')

def switch_cam(gpio, i2c):
    sleep(0.2)
    GPIO.output(channel_list[0], gpio)
    write_i2c(i2c)

# https://picamera.readthedocs.io/en/release-1.3/recipes2.html#rapid-capture-and-processing
def filenames(frames):
    frame = 0
    while frame < frames:
        yield gimme_file(frame)
        frame += 1
        print(f'Updating frame {frame}')

def gimme_file(frame):
    if frame % 2 == 0:
        switch_cam(GPIO.LOW, 1)
    else:
        switch_cam(GPIO.HIGH, 2)
    return 'testing_images/image%02d.jpg' % frame

def take_n_photos(n):
    print('Starting to take photos')
    # Set up 40 in-memory streams
    start = time()
    camera.capture_sequence(filenames(n), use_video_port=False)
    finish = time()
    # How fast were we?
    print('Captured %d images at %.2ffps' % (n / (finish - start), n + 1))

def test_i2c_writes(writes):
    count = 0
    for i in range(0, writes):
        try:
            write_i2c(i % 2 + 1)
            count+=1
            sleep(0.5)
        except IOError:
            print('Error at cycle %d' % count)

# init_gpios()
# init_camera()
# take_photos()
# take_photos_stream()
# take_n_photos(40)
# test_i2c_writes(40)
# cleanup()
