import time
import atexit
import csv
# from queue import Queue
from collections import deque

from apscheduler.schedulers.background import BackgroundScheduler


ghost_cars = [deque(), deque(), deque(), deque(), deque()]


def load_file(i):
    with open('./ghost_data/car_'+str(i)+'.csv') as csv_file:
        csv_reader = csv.reader(csv_file)
        next(csv_reader)
        for row in csv_reader:
            ghost_cars[i].append((row[1], row[2]))


def get_current_pos():
    # print('')
    # print(time.strftime("%A, %d. %B %Y %I:%M:%S %p"))
    positions = []
    for i in range(5):
        if not len(ghost_cars[i]):
            load_file(i)
        positions.append(ghost_cars[i].popleft())
    return positions
    # print(ghost_cars[0].qsize())
    # print(len(ghost_cars[0]))
    


scheduler = BackgroundScheduler()
scheduler.add_job(func=get_current_pos, trigger="interval", seconds=2)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())