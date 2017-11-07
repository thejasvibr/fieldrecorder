# -*- coding: utf-8 -*-
"""
Playback and record sound for the field setup :

Created on Mon Nov 06 18:10:01 2017

@author: tbeleyur
"""
import Queue
import numpy as np
import sounddevice as sd
import pygame
from pygame.locals import *
from scipy import signal
import matplotlib.pyplot as plt
plt.rcParams['agg.path.chunksize'] = 10000







def thermoacousticpy(rec_durn = 3):
    '''

    '''

    fs = 192000
    sync_freq = 25
    one_cycledurn = 1.0/sync_freq
    num_cycles = 1
    sig_durn = num_cycles*one_cycledurn
    t = np.linspace(0,sig_durn,int(fs*sig_durn))
    sine_fn = 2*np.pi*sync_freq*t + np.pi

    sync_signal = np.float32( signal.square(sine_fn,0.5) )

    trigger_freq = 2.0*10**3
    trigger_signal = np.float32( np.sin(2*np.pi*t*trigger_freq) )

    empty_signal = np.float32(np.zeros(sync_signal.size))
    only_sync = np.column_stack((empty_signal,sync_signal))
    trig_and_sync = np.column_stack((trigger_signal,sync_signal))

    S = sd.Stream(samplerate=fs,blocksize=sync_signal.size,channels=(2,2))


    pygame.init()


    start_time = np.copy(S.time)
    rec_time = np.copy(S.time)
    end_time =  start_time + rec_durn


    q = Queue.Queue()

    S.start()

    recording = False

    kb_event = 0

    while rec_time < end_time:

        for event in pygame.event.get():

            if event.type() == KEYDOWN :
                kb_event += 1
                print('recording...')
                recording = True

                if kb_event == 2:
                    print('stopping recording...')
                    recording = False
                    kb_event = 0

        # if keyboard hit then enter recording state
        # kb_event += 1

        # if keyboard hit again then revert to no recording



        if not recording:
            S.write(only_sync)



        if recording:
            S.write(trig_and_sync)
            q.put (S.read(sync_signal.size))

        rec_time = S.time



    S.stop()

    q_contents = [ q.get()[0] for i in range(q.qsize()) ]

    rec = np.concatenate(q_contents)


    return(fs,rec)






if __name__ == '__main__':
    fs,rec = thermoacousticpy(10)
    plt.plot(np.linspace(0,rec.shape[0]/float(fs),rec.shape[0]),rec);plt.ylim(-1,1)

