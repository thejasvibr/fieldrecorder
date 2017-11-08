# -*- coding: utf-8 -*-
"""
Playback and record sound for the field setup :

Created on Mon Nov 06 18:10:01 2017

@author: tbeleyur
"""
import Queue
import datetime as dt
import numpy as np
import sounddevice as sd
from scipy import signal
import matplotlib.pyplot as plt
plt.rcParams['agg.path.chunksize'] = 10000
from pynput.keyboard import  Listener



class fieldrecorder():

    def __init__(self,rec_durn):
        self.rec_durn = rec_durn
        self.press_count = 0
        self.recording = False
        self.sync_freq = 25



    def thermoacousticpy(self):
        '''

        '''

        fs = 192000
        one_cycledurn = 1.0/self.sync_freq
        num_cycles = 1
        sig_durn = num_cycles*one_cycledurn
        t = np.linspace(0,sig_durn,int(fs*sig_durn))
        sine_fn = 2*np.pi*self.sync_freq*t + np.pi

        sync_signal = np.float32( signal.square(sine_fn,0.5) )
        trigger_freq = 15*10**3

        # conv to 32 bit so sounddevice can take the signals as inputs
        trigger_signal = np.float32(np.sin(2*np.pi*t*trigger_freq))
        empty_signal = np.float32(np.zeros(sync_signal.size))

        only_sync = np.column_stack((empty_signal, sync_signal))
        trig_and_sync = np.column_stack((trigger_signal, sync_signal))

        self.S = sd.Stream(samplerate=fs,blocksize=sync_signal.size,channels=(2,2))

        start_time = np.copy(self.S.time)
        rec_time = np.copy(self.S.time)
        end_time =  start_time + self.rec_durn


        q = Queue.Queue()

        self.S.start()

        kb_input = Listener(on_press=self.on_press)

        kb_input.start()

        try:

            while rec_time < end_time:


                if self.recording:
                    q.put(self.S.read(trig_and_sync.shape[0]))
                    self.S.write(trig_and_sync)

                else :
                    self.S.write(only_sync)

                rec_time = self.S.time

            kb_input.stop()

        except :

            print('Error encountered ..exiting ')

            kb_input.stop()


        self.S.stop()

        print('Queue size is',q.qsize())

        q_contents = [ q.get()[0] for i in range(q.qsize()) ]

        rec = np.concatenate(q_contents)



        return(fs,rec)



    def on_press(self,key):

        print('button pressed')
        self.press_count += 1

        if self.press_count == 1:
            self.recording = True
            print('recording started')

        elif self.press_count == 2:
            self.recording = False
            self.press_count = 0
            print('recording stopped')

            #   empty q contents into a np array

            # save numpy array as a WAV file
            # and proceed

        pass

    def empty_qcontents():

        pass

    def save_qcontents_aswav():

        # if an error in saving occurs - print a statement and make a BIG
        # error

        pass





if __name__ == '__main__':


    a = fieldrecorder(10)
    fs,rec= a.thermoacousticpy()
    plt.plot(np.linspace(0,rec.shape[0]/float(fs),rec.shape[0]),rec);plt.ylim(-1,1)

