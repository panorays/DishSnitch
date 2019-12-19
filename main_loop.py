import datetime
import os
import pprint
import time

import cv2
import face_recognition
import numpy as np
import pygame as pg
import pymongo

import global_vars
import config
from part1_capture_image import take_sink_photo
from part2_detect_dishes import check_if_dishes_exist
from part3_notify import post_slack


mongo_client = pymongo.MongoClient(host=config.mongo_host, port=config.mongo_port)
targets_db = mongo_client.targets
employees_pull = targets_db.employees

known_face_encodings = []
known_face_names = []
last_sin = {}
# Initialize some variables
face_locations = []
face_encodings = []
face_names = []
process_this_frame = True
total_time = []
cooldown = 10  # 3600 seconds between detection of targets = 1 hour


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
        print("Music file {} loaded!".format(music_file))
    except pg.error:
        print("File {} not found! ({})".format(music_file, pg.get_error()))
        return
    pg.mixer.music.play()
    while pg.mixer.music.get_busy():
        # check if playback has finished
        clock.tick(30)

for employee in employees_pull.distinct("full_name"):
    for fetch_info in employees_pull.find({"full_name": employee}):
        last_sin[fetch_info.get("full_name")] = (time.time() - cooldown)
        known_face_names.append(fetch_info.get("full_name"))
        #print ('starting to encode {} '.format(employee))
        start_time = time.time()
        known_face_encodings.append(
            face_recognition.face_encodings(face_recognition.load_image_file(fetch_info.get("image")))[0])
        end_time = time.time()
        finish_time = end_time - start_time
        #print ('{} has been encoded and took {} '.format(employee, finish_time))
        total_time.append(finish_time)
print (known_face_names)
print ('total tine for the process {} '.format(round(sum(total_time))))

# Get a reference to webcam for capturing people
video_capture = cv2.VideoCapture(config.person_camera_index)

while True:
    # Grab a single frame of video
    ret, frame = video_capture.read()

    # Resize frame of video to 1/2 size for faster face recognition processing
    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)

    # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
    rgb_small_frame = small_frame[:, :, ::-1]

    # Only process every other frame of video to save time
    if process_this_frame:
        # Find all the faces and face encodings in the current frame of video
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        face_names = []
        for face_encoding in face_encodings:
            # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            name = "Unknown"

            # # If a match was found in known_face_encodings, just use the first one.
            # if True in matches:
            #     first_match_index = matches.index(True)
            #     name = known_face_names[first_match_index]

            # Or instead, use the known face with the smallest distance to the new face
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = known_face_names[best_match_index]
                for check in known_face_names:
                    if check == name:
                        pprint.pprint("We found you..." + name)
                        # optional volume 0 to 1.0
                        volume = 1.0
                        play_music(config.found_someone_mp3_path, volume)

                        if face_distances[best_match_index] < 0.49:
                            if time.time() > (last_sin[name] + cooldown):
                                last_sin[name] = time.time()
                                print ("target found at {}  ".format(check) + time.strftime("(%H:%M:%S - %d/%m/%Y)"))
                                global_vars.current_suspect = name
                                pprint.pprint("current_suspect after detected:" + global_vars.current_suspect)

                                #get sink status
                                #check_if_dishes_exist()
                                pprint.pprint("sink status when face detected:" + global_vars.current_sink_status)
                                pprint.pprint("current suspect when face detected:" + global_vars.current_suspect)
                            else:
                                cooldown_remain = ((last_sin[name] + cooldown) - time.time())
                                print ('{} you have more {} for cool-down'.format(name, str(
                                    datetime.timedelta(seconds=cooldown_remain))))
            face_names.append(name)
        else:
            pprint.pprint("unknown person or person left... did someone leave the sink?")

            # take sink photo
            pprint.pprint("taking photo of sink..")
            take_sink_photo()

            # get sink status
            check_if_dishes_exist()
            pprint.pprint("sink status with unknwon:" + global_vars.current_sink_status)
            pprint.pprint("current suspect with unknwon:" + global_vars.current_suspect)

            if global_vars.current_sink_status == "dirty":
                pprint.pprint("Someone left DIRTY dishes!")
                pprint.pprint("last person: " + global_vars.current_suspect)

                if global_vars.current_suspect != "unknown":
                    post_slack(global_vars.current_suspect)
                    global_vars.current_sink_status = "dirty_notification_sent"
                    global_vars.current_sink_status = "unknown"

                    pprint.pprint("sink status after notification:" + global_vars.current_sink_status)
                    pprint.pprint("current suspect after notification:" + global_vars.current_suspect)
            else:
                pprint.pprint("Someone left CLEAN dishes!")
                pprint.pprint("last person: " + global_vars.current_suspect)

            global_vars.current_suspect = "unknown"

    process_this_frame = not process_this_frame

    #Display the results
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        # Scale back up face locations since the frame we detected in was scaled to 0.5 size
        top *= 2
        right *= 2
        bottom *= 2
        left *= 2

        # Draw a box around the face
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

        # Draw a label with a name below the face
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 3, bottom - 3), font, 0.5, (255, 255, 255), 1)

    # Display the resulting image
    cv2.imshow('Video', frame)

    # Hit 'q' on the keyboard to quit!
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release handle to the webcam
video_capture.release()
cv2.destroyAllWindows()
