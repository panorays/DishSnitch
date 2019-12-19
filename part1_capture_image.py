import os

import cv2

import config


def take_sink_photo():
    try:
        webcam = cv2.VideoCapture(config.sink_camera_index)
        check, frame = webcam.read()
        cv2.imshow("Capturing", frame)
        cv2.imwrite(os.path.join(config.saved_images_dir , 'saved_img.jpg'), img=frame)
        webcam.release()
    except:
        print("Turning off camera.")
        webcam.release()
        print("Camera off.")
        print("Program ended.")
