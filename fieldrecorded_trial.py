# -*- coding: utf-8 -*-
"""
Playback and record sound for the field setup :

Created on Mon Nov 06 18:10:01 2017

@author: tbeleyur
"""
import Queue
import numpy as np
import sounddevice as sd

from pygame.locals import *
from scipy import signal
import matplotlib.pyplot as plt
plt.rcParams['agg.path.chunksize'] = 10000
from pynput.keyboard import Key, Listener



class fieldrecorder():

    def __init__(self,rec_durn):
        self.rec_durn = rec_durn
        self.recording = 0




    def thermoacousticpy(self):
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

        self.S = sd.Stream(samplerate=fs,blocksize=sync_signal.size,channels=(2,2))



        start_time = np.copy(self.S.time)
        rec_time = np.copy(self.S.time)
        end_time =  start_time + self.rec_durn


        q = Queue.Queue()

        self.S.start()

        recording = False

        kb_input = Listener(on_press=self.on_press)

        kb_input.start()


        try:

            while rec_time < end_time:


                if self.recording == 1:
                    q.put(self.S.read(trig_and_sync.shape[0]))
                    self.S.write(trig_and_sync)

                elif self.recording == 0 :
                    self.S.write(only_sync)


                rec_time = self.S.time

            kb_input.stop()

        except :

            print('Error encountered ..exiting ')

            kb_input.stop()


        self.S.stop()

        print(q.qsize())

        q_contents = [ q.get()[0] for i in range(q.qsize()) ]

        rec = np.concatenate(q_contents)



        return(fs,rec)



    def on_press(self,key):

        print('button pressed - recording')

        if self.recording == 0 :
            return(self.recording = 1)

        if self.recording == 1 :
            return(self.recording == 0)



        print(self.recording)

        pass





if __name__ == '__main__':
    #fs,rec = thermoacousticpy(10)
    #plt.plot(np.linspace(0,rec.shape[0]/float(fs),rec.shape[0]),rec);plt.ylim(-1,1)

    a = fieldrecorder(10)
    a.thermoacousticpy()

