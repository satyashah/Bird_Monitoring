import pandas as pd
import cv2
import matplotlib.pyplot as plt
import os
from matplotlib import gridspec
import numpy as np
import math
import time
import pygame
import random
import threading
from queue import Queue
import msvcrt
import datetime
import settings
from numpy import polyfit
from collections import deque

global PARAMS
global RUNNINGVARS
global DATA 
global FRAME_CENTER
global FEED
global TOP_PLOT, CAM_PLOT, DATA_PLOT 
global SOUNDSET
global SOUND_PROB_ARR
global ANGLE_HISTORY 


# USER PARAMS [CHANGE THESE]
PARAMS = settings.PARAMS

# SYSTEM VARS
RUNNINGVARS = {
    "start_time": time.time(),
    "speaker_side_playing": "left",
    "sound_playing": ("blank", None),
    "trial_num": 0,
    "cur_angle": 0,
    "pause": True,
    "cam_center": (0, 0),
    "is_stable": True,
}

# Dataframe to store data
DATA = pd.DataFrame()

# Set up camera feed
class Feed:
    def __init__(self, FRAME_SIZE):
        self.frame_size = FRAME_SIZE
        self.feed = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        [self.feed.read(0) for _ in range(2)]  # Remove first two frames
        RUNNINGVARS["cam_center"] = (FRAME_SIZE // 2, FRAME_SIZE // 2)

    def get_frame(self):
        _, frame = self.feed.read()
        return frame
    
    def get_cropped_frame(self):
        assert FRAME_CENTER is not None, "Frame Center is not set"
        frame = self.get_frame()
        half_size = self.frame_size // 2
        crop_x1 = max(0, FRAME_CENTER[0] - half_size)
        crop_x2 = min(frame.shape[1], FRAME_CENTER[0] + half_size)
        crop_y1 = max(0, FRAME_CENTER[1] - half_size)
        crop_y2 = min(frame.shape[0], FRAME_CENTER[1] + half_size)

        # Crop the frame using NumPy slicing
        cropped_frame = frame[crop_y1:crop_y2, crop_x1:crop_x2]

        return cropped_frame

FEED = Feed(150)  # FRAME_SIZE = 450

# Camera Center Set Up
def set_up_cam():
    frame = FEED.get_frame()
    
    clicked_coordinates = []  # List to store clicked coordinates

    def onclick(event):
        if event.inaxes is not None:
            print(f'Selected Bird Center: ({int(event.xdata)}, {int(event.ydata)})')
            clicked_coordinates.append((int(event.xdata), int(event.ydata)))  # Append clicked coordinates
            plt.close()

    plt.title('Click on the Center of Bird')
    plt.imshow(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), cmap='gray')
    plt.gcf().canvas.mpl_connect('button_press_event', onclick)
    plt.show() # Show the plot, wait for the user to click

    # This return is executed after the user clicks and the plot is closed
    return clicked_coordinates[-1][0], clicked_coordinates[-1][1] # Return the last clicked coordinates


FRAME_CENTER = set_up_cam() # Set manually (300,200) or use set_up_cam()

# Sound Set Up
pygame.init()
pygame.mixer.init(channels=2)

SOUNDSET = {}
for sound_index in range(len(PARAMS["sound_names"])):
    name = PARAMS["sound_names"][sound_index]
    path = PARAMS["sound_paths"][sound_index]
    SOUNDSET[name] = pygame.mixer.Sound(path)

pygame.mixer.Channel(0).set_volume(1.0, 0.0)  # Full volume on left, mute on right
pygame.mixer.Channel(1).set_volume(0.0, 1.0)  # Mute on left, full volume on right


def build_sound_prob_arr():
    SOUND_PROB_ARR = [0] * (100 - PARAMS["target_prob"])

    for i in range(1, len(PARAMS["sound_names"])+1):
        SOUND_PROB_ARR += [i] * (PARAMS["target_prob"]//len(PARAMS["sound_names"]))
    
    return SOUND_PROB_ARR

SOUND_PROB_ARR = build_sound_prob_arr()

# Stability
ANGLE_HISTORY = deque(maxlen=30)

# Create a figure with two subplots and top section
fig = plt.figure(figsize=(10, 6))
gs = gridspec.GridSpec(3, 2, width_ratios=[3, 4], height_ratios=[1, 10, 10])
TOP_PLOT = fig.add_subplot(gs[0, :])  # Top plot for general info
CAM_PLOT = fig.add_subplot(gs[1:, 0])  # Camera plot on the left
DATA_PLOT = fig.add_subplot(gs[1, 1])  # Data plot on the right
SUM_PLOT = fig.add_subplot(gs[2, 1])  # Data plot on the right

plt.tight_layout(pad=3)
plt.ion()

def write2plot(text):
    TOP_PLOT.clear()
    TOP_PLOT.axis("off")
    TOP_PLOT.text(0.5, 0.5, text, fontsize=20, ha="center", va="center")

def on_click(event):
    if event.inaxes:
        RUNNINGVARS["cam_center"] = (int(event.xdata), int(event.ydata))

plt.connect('button_press_event', on_click)

def set_data_plot():
    DATA_PLOT.clear()
    DATA_PLOT.set_ylim(-45, 45)
    DATA_PLOT.set_ylabel('Movement (degrees)')
    DATA_PLOT.set_xlabel('Time (s)')
    DATA_PLOT.set_title('Movement Per Sound')

def set_sum_plot():
    SUM_PLOT.clear()
    SUM_PLOT.set_ylim(-45, 45)
    SUM_PLOT.set_ylabel('Movement (degrees)')
    SUM_PLOT.set_xlabel('Time (s)')
    SUM_PLOT.set_title('Movement Per Sound')

set_data_plot()
set_sum_plot()

# EVENTS
STOP_SOUND_EVENT = pygame.USEREVENT + 1
PLAY_SOUND_EVENT = pygame.USEREVENT + 2


# Threading
DATA_BUS = Queue()
print("Globals Loaded")


