# -*- coding: utf-8 -*-
"""
A dongle-free approach to control the thermal cameras and mics !!

Device control logic based on the AVR script series written by
Holger R. Goerlitz


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

    def __init__(self,rec_durn,device_name=None,input_output_chs=(2,2)):
        self.rec_durn = rec_durn
        self.press_count = 0
        self.recording = False
        self.sync_freq = 25
        self.device_name = device_name
        self.input_output_chs = input_output_chs

        if self.device_name  is None:
            self.tgt_ind = None
        else:
            self.get_device_indexnumber(self.device_name)



    def thermoacousticpy(self):
        '''

        '''

        fs = 192000
        one_cycledurn = 1.0/self.sync_freq
        num_cycles = 3
        sig_durn = num_cycles*one_cycledurn
        t = np.linspace(0,sig_durn,int(fs*sig_durn))
        sine_fn = 2*np.pi*self.sync_freq*t + np.pi

        self.sync_signal = np.float32( signal.square(sine_fn,0.5) )
        trigger_freq = 20*10**3

        # conv to 32 bit so sounddevice can take the signals as inputs
        self.trigger_signal = np.float32(np.sin(2*np.pi*t*trigger_freq))
        self.empty_signal = np.float32(np.zeros(self.sync_signal.size))

        self.only_sync = np.column_stack((self.sync_signal, self.empty_signal))
        self.trig_and_sync = np.column_stack((self.sync_signal, self.trigger_signal, ))


        self.S = sd.Stream(samplerate=fs,blocksize=self.sync_signal.size,
                           channels=self.input_output_chs,device=self.tgt_ind)

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
                    q.put(self.S.read(self.trig_and_sync.shape[0]))
                    self.S.write(self.trig_and_sync)

                else :
                    self.S.write(self.only_sync)

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


    def get_device_indexnumber(self,device_name):
        '''
        Check for the device name in all of the recognised devices and
        return the index number within the list.

        '''
        self.device_list = sd.query_devices()

        self.tgt_dev_name = device_name
        self.tgt_dev_bool = [self.tgt_dev_name in each_device['name'] for each_device in self.device_list]

        if not True in self.tgt_dev_bool:

            print (sd.query_devices())

            raise ValueError('The input device \n' + self.tgt_dev_name+
            '\n could not be found, please look at the list above'+
                             ' for all the recognised devices'+
                             ' \n Please use sd.query_devices to check the recognised'
                             +' devices on this computer')

        if sum(self.tgt_dev_bool) > 1 :
           raise ValueError('Multiple devices with the same string found'
           + ' please enter a more specific device name'
           ' \n Please use sd.query_devices to check the recognised'+
           ' devices on this computer')

        else:
            self.tgt_ind = int(np.argmax(np.array(self.tgt_dev_bool)))







if __name__ == '__main__':


    a = fieldrecorder(150,input_output_chs=(2,2),device_name='USB' )
    fs,rec= a.thermoacousticpy()
    #plt.plot(np.linspace(0,rec.shape[0]/float(fs),rec.shape[0]),rec);plt.ylim(-1,1)

