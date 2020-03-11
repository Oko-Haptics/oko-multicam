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

        # Exit runs twice with this, need to
        # figure out how to get clean exits from
        # failures and normal shutdown
        atexit.register(self._cleanup)

        print(self)
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

    def _cleanup(self):
        # self.camera.close()
        # GPIO.cleanup()
        print(f'Pre-Cleanup Termination {self.processor.terminated}')
        self.processor.terminated = True
        print(f'Post-Cleanup Termination {self.processor.terminated}')
        self.processor.join()

class CaptureImages(threading.Thread):
    def __init__(self, owner, camera):
        print("Init Capture Images")
        super(CaptureImages, self).__init__()

        self.terminated = False
        self.owner = owner # Owner is the MultiCam library

        self.camera = None
        self.i2c_addr = "0x70"
        self.channel_list = [4, 17]

        self._init_gpios()
        self._init_camera()

        self.start() # Will call the run method

    # The thread stops being alive when the run()
    # method returns (intentionally or not)
    def run(self):
        while not self.terminated:
            self.owner.left_photo += 1
            self._use_camera('A')
            f_left = 'testing_images/multithread_L_%02d.jpg' % self.owner.left_photo
            self.camera.capture(f_left)
            sleep(1)

            self.owner.right_photo += 1
            self._use_camera('B')
            f_right = 'testing_images/multithread_R_%02d.jpg' % self.owner.right_photo
            self.camera.capture(f_right)
            sleep(1)

        print("He ded")
        self._cleanup()

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
        sleep(0.1)

    def _use_camera(self, cam):
        if cam == 'A':
            self._write_i2c(data=1)
            print("Flipping GPIO A")
            print(f"GPIO Mode A {GPIO.getmode()}")
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.channel_list, GPIO.OUT, initial=GPIO.LOW)
            GPIO.output(self.channel_list[0], GPIO.LOW)
        elif cam == 'B':
            self._write_i2c(data=2)
            print("Flipping GPIO B")
            print(f"GPIO Mode B {GPIO.getmode()}")
            GPIO.output(self.channel_list[0], GPIO.HIGH)
        else:
            print("Wrong camera setting")
        sleep(0.1)

    def _cleanup(self):
        self.camera.close()
        GPIO.cleanup()
