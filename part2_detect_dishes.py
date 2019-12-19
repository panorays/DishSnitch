import copy
import os
import time

import cv2
import numpy as np
from playsound import playsound
import pygame as pg

import config
import global_vars

## Define our config values

# What is our min dish count to alarm on?
min_dishes = 1

# Define areas we want to ignore
# First value is the x range, second is the y range
ignore_list = ["339-345,257-260"]

# Set our timestamp
time_stamp = time.strftime("%Y%m%d%H%M%S")

# Set our circle detection variables
circle_sensitivity = 40  # Larger numbers increase false positives
#circle_sensitivity = 60  # Larger numbers increase false positives

min_rad = 30  # Tweak this if you're detecting circles that are too small
max_rad = 75  # Tweak if you're detecting circles that are too big (Ie: round sinks)

# Cropping the image allows us to only process areas of the image
# that should have images. Set our crop values
crop_left = 0
crop_right = 360
crop_top = 150
crop_bottom = 850


def should_ignore(ignore_list, x, y):
    # Loop through our ignore_list and check for this x/y
    ignore = False
    for range in ignore_list:
        x_range = range.split(',')[0]
        y_range = range.split(',')[1]
        x_min = int(x_range.split('-')[0])
        x_max = int(x_range.split('-')[1])
        y_min = int(y_range.split('-')[0])
        y_max = int(y_range.split('-')[1])

        if (x >= x_min and x <= x_max and y >= y_min and y <= y_max):
            ignore = True

    return ignore


def play_music(music_file, volume=0.8):
    '''
    stream music with mixer.music module in a blocking manner
    this will stream the sound from disk while playing
    '''
    # set up the mixer
    freq = 44100     # audio CD quality
    bitsize = -16    # unsigned 16 bit
    channels = 2     # 1 is mono, 2 is stereo
    buffer = 2048    # number of samples (experiment to get best sound)
    pg.mixer.init(freq, bitsize, channels, buffer)
    # volume value 0.0 to 1.0
    pg.mixer.music.set_volume(volume)
    clock = pg.time.Clock()
    try:
        pg.mixer.music.load(music_file)
        #print("Music file {} loaded!".format(music_file))
    except pg.error:
        print("File {} not found! ({})".format(music_file, pg.get_error()))
        return
    pg.mixer.music.play()
    while pg.mixer.music.get_busy():
        # check if playback has finished
        clock.tick(30)


def check_if_dishes_exist():
    # Note: Larger images require more processing power and have more false positives

    image_original = cv2.imread(os.path.join(config.saved_images_dir, 'saved_img.jpg'))

    #print("Cropping image to limit processing to just the sink")
    image = image_original[crop_left:crop_right, crop_top:crop_bottom]

    #print("Copying image")
    output = copy.copy(image)

    #print("Blurring image")
    blurred = cv2.GaussianBlur(image, (9, 9), 2, 2)
    cv2.imwrite(os.path.join(config.saved_images_dir, 'blurred.jpg'), blurred)

    #print("Converting to grey")
    gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
    cv2.imwrite(os.path.join(config.saved_images_dir, 'gray.jpg'), gray)

    #print("Detecting circles in blurred and greyed image")
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, 20,
                               param1=100,
                               param2=circle_sensitivity,
                               minRadius=min_rad,
                               maxRadius=max_rad)

    #print("Checking if we found images")
    if circles is not None:
        dish_count = 0
        print("Dishes Found!")
        # convert the (x, y) coordinates and radius of the circles to integers
        circles = np.round(circles[0, :]).astype("int")

        # loop over the (x, y) coordinates and radius of the circles
        for (x, y, r) in circles:
            # draw the circle in the output image, then draw a rectangle
            # corresponding to the center of the circle
            cv2.circle(output, (x, y), r, (0, 255, 0), 4)
            cv2.rectangle(output, (x - 5, y - 5), (x + 5, y + 5), (0, 128, 255), -1)
            # Check our ignore_list
            if (should_ignore(ignore_list, x, y)):
                print("Circle in ignore_list: Ignoring")
            else:
                dish_count += 1
                print("Dish count:%s" % (str(dish_count)))

        cv2.imwrite(os.path.join(config.saved_images_dir, 'detected.jpg'), output)

        if dish_count >= min_dishes:
            print("Playing dirty dishes sound..")
            global_vars.current_sink_status = "dirty"
            # optional volume 0 to 1.0
            volume = 1.0
            play_music(config.left_dirty_dishes_mp3_path, volume)
    else:
        print("No Dishes Found!")
        global_vars.current_sink_status = "clean"
        # optional volume 0 to 1.0
        volume = 1.0
        play_music(config.cleaned_dishes_mp3_path, volume)


if __name__ == "__main__":
    main()
