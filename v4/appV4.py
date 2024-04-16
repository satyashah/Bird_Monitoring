from funcV4 import *
import keyboard
import pygame
import pandas as pd
import datetime

from tabulate import tabulate
import msvcrt
import os
from set_up_cam import center_cords as cc

# # Params
x,y = set_up_cam()
center_cords = (x, y)
FRAME_SIZE = 400

tone_sound_path = "test_sounds/ABCD_perry.wav" #"test_sounds/pu995_ABCDEFG.wav"
test_sound_paths = ["test_sounds/ABCD_perry.wav", "test_sounds/CanaryAB.wav"]

sound_duration = 1000
data_collection_duration = 3000 # note this is including sound duration

data_file_name = "test_data"

# Setup Sound

assert len(test_sound_paths) < 8, "Error: Too many test sounds. Max 7 allowed"
tone, sound_arr = set_up_sound(tone_sound_path, test_sound_paths)

sound_names = create_sound_set(tone_sound_path, test_sound_paths)
print("Sound Loaded:",sound_names)


# Application

sound_playing = "None"
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

print(f"Application started... {timestamp}")
# Live Feed
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
print("Error: Could not open video.") if not cap.isOpened() else None
ret, frame = cap.read(0) # Remove first frame

frame_num = 0
data_dict = {}
start_time = time.time()

STOP_SOUND_EVENT = pygame.USEREVENT + 1
SUMMARIZE_EVENT = pygame.USEREVENT + 2
clear_terminal = lambda: os.system('cls')

while True:
    frame_num += 1
    
    try:
        cropped_frame, angle, beak_center = display_camara(cap, center_cords, FRAME_SIZE)
        plot_bird(cropped_frame, beak_center, angle, FRAME_SIZE)
    except Exception as e:
        print(f"Error: {e}")
        continue
    # Save Data
    data_dict[frame_num] = {}
    data_dict[frame_num]["time"] = round(time.time() - start_time,2)
    data_dict[frame_num]["angle"] = round(angle,2)
    data_dict[frame_num]["X"] = beak_center[0] - FRAME_SIZE//2
    data_dict[frame_num]["Y"] = beak_center[1] - FRAME_SIZE//2
    data_dict[frame_num]["sound"] = sound_playing


    for event in pygame.event.get():
        if event.type == STOP_SOUND_EVENT:
            pygame.mixer.stop()

        if event.type == SUMMARIZE_EVENT:
            summarize_data(data_dict, sound_playing)
            sound_playing = "None"
    
    if msvcrt.kbhit():  # Check if a key has been pressed
        clear_terminal()
        key = msvcrt.getch()
        if key.isdigit():
            key_num = int(key)
        
            if key_num == 0:
                print("Exiting...")
                pygame.mixer.stop()
                break

            if key_num == 1:

                if sound_playing == "Tone":
                    data_dict[frame_num] = {'time': round(time.time() - start_time,2), 'angle': round(angle,2), 'X': beak_center[0] - FRAME_SIZE//2, 'Y': beak_center[1] - FRAME_SIZE//2, 'sound': "None"}
                    frame_num += 1

                print(f"{sound_names[0]} Starting...\n")
                print(f"Initial \n\tAngle => {round(angle,2)} \n\tX => {beak_center[0] - FRAME_SIZE//2}\n")
                play_sound(tone, "left", sound_duration, STOP_SOUND_EVENT, data_collection_duration, SUMMARIZE_EVENT)
                sound_playing = "Tone"
            
            
            if key_num > 1 and key_num <= len(sound_arr) + 1:

                if sound_playing == sound_names[key_num-1]:
                    data_dict[frame_num] = {'time': round(time.time() - start_time,2), 'angle': round(angle,2), 'X': beak_center[0] - FRAME_SIZE//2, 'Y': beak_center[1] - FRAME_SIZE//2, 'sound': "None"}
                    frame_num += 1
                
                print(f"{sound_names[key_num-1]} Starting...\n")
                print(f"Initial \n\tAngle => {round(angle,2)} \n\tX => {beak_center[0] - FRAME_SIZE//2}\n")
                play_sound(sound_arr[key_num-2], "right", sound_duration, STOP_SOUND_EVENT, data_collection_duration, SUMMARIZE_EVENT)
                sound_playing = sound_names[key_num-1]
            
            key = -1

    #time.sleep(0.1)


    

        
# Save Data
df = pd.DataFrame(data_dict).T
# df.to_csv(f"data/{data_file_name}_{timestamp}.csv", index=False)

# Calculate mean and standard deviation for each sound group
sound_stats = df.groupby('sound').agg({'angle': ['mean', 'std']})
# Rename columns for clarity
sound_stats.columns = ['mean_angle', 'std_dev_angle']

print(sound_stats)