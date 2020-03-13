import atexit
import io
import threading
import RPi.GPIO as GPIO
from cv2
from time import sleep
from time import time
from picamera import PiCamera
from picamera.array import PiRGBArray
from smbus2 import SMBus

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
        self.right_photo = io.BytesIO()
        self.left_photo = io.BytesIO()

        # Exit runs twice with this, need to
        # figure out how to get clean exits from
        # failures and normal shutdown
        atexit.register(self.cleanup)

        print(self)
        # Starts background thread dedicated to taking images
        self.processor = CaptureImages(self, self.camera)

    # Get the most recently taken photo
    # from the left camera
    def get_left_photo(self):
        # print(f"Get left photo")
        return self.left_photo

    # Get the most recently taken photo
    # from the right camera
    def get_right_photo(self):
        # print(f"Get right photo")
        return self.right_photo

    def cleanup(self):
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

        self.right_count = 0;
        self.left_count = 0;

        self._init_gpios()
        self._init_camera()

        self.raw_output_left = PiRGBArray(self.camera)
        self.raw_output_right = PiRGBArray(self.camera)

        atexit.register(self._cleanup)

        self.start()

    # The thread stops being alive when the run()
    # method returns (intentionally or not)
    def run(self):

        start = time()
        while not self.terminated:
            self.left_count += 1
            self._use_camera('A')

            # OpenCV uses the 'bgr'
            # f_left = 'testing_images/multithread_L_%02d.jpg' % self.owner.left_photo
            # self.camera.capture(f_left)
            self.camera.capture(self.raw_output_left, format='bgr')
            print('Captured Left %dx%d image' % (
                self.raw_output_left.array.shape[1], self.raw_output_left.array.shape[0]))
            imwrite('./testing_images/left_cv2.jpg', self.raw_output_left.array)


            self.right_count += 1
            self._use_camera('B')
            # f_right = 'testing_images/multithread_R_%02d.jpg' % self.right_count
            self.camera.capture(self.raw_output_right, format='bgr')
            print('Captured Right %dx%d image' % (
                self.raw_output_right.array.shape[1], self.raw_output_right.array.shape[0]))
            imwrite('./testing_images/right_cv2.jpg', self.raw_output_right.array)

            # TODO: Remove
            break;

        end = time()
        delta = end - start
        print(f'Took {self.right_count} {self.left_count} photos in {delta} seconds')
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
            GPIO.output(self.channel_list[0], GPIO.LOW)
        elif cam == 'B':
            self._write_i2c(data=2)
            GPIO.output(self.channel_list[0], GPIO.HIGH)
        else:
            print("Wrong camera setting")
        sleep(0.1)

    def _cleanup(self):
        print("Cleaning up camera and GPIOs")
        self.camera.close()
        GPIO.cleanup()

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
