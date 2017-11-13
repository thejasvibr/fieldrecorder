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
import wave
import matplotlib.pyplot as plt
plt.rcParams['agg.path.chunksize'] = 10000
from pynput.keyboard import  Listener



class fieldrecorder():

    def __init__(self,rec_durn,device_name=None,input_output_chs=(2,2),target_dir = '~\\Desktop\\',**kwargs):
        self.rec_durn = rec_durn
        self.press_count = 0
        self.recording = False
        self.sync_freq = 25
        self.device_name = device_name
        self.input_output_chs = input_output_chs
        self.target_dir = target_dir

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


        self.q = Queue.Queue()

        self.S.start()

        kb_input = Listener(on_press=self.on_press)

        kb_input.start()

        try:

            while rec_time < end_time:


                if self.recording:
                    self.q.put(self.S.read(self.trig_and_sync.shape[0]))
                    self.S.write(self.trig_and_sync)

                else :
                    self.S.write(self.only_sync)

                rec_time = self.S.time

            kb_input.stop()

        except :

            print('Error encountered ..exiting ')

            kb_input.stop()


        self.S.stop()

        print('Queue size is',self.q.qsize())

        return(fs,self.rec)



    def on_press(self,key):

        print('button pressed....\n')
        self.press_count += 1

        if self.press_count == 1:
            self.recording = True
            print('recording started')

        elif self.press_count == 2:
            self.recording = False
            self.press_count = 0
            print('recording stopped')

            self.empty_qcontentsintolist()

            self.save_qcontents_aswav()

            #   empty q contents into a np array

            # save numpy array as a WAV file
            # and proceed

        pass

    def empty_qcontentsintolist(self):
        try:
            self.q_contents = [ self.q.get()[0] for i in range(self.q.qsize()) ]

        except:
            raise IOError('Unable to empty queue object contents')

        pass

    def save_qcontents_aswav(self):

        print('Saving file now...')

        self.rec = np.concatenate(self.q_contents)

        timenow = dt.datetime.now()
        self.timestamp = timenow.strftime('%Y-%m-%d-%H_%M_%S')

        main_filename = self.target_dir + 'MULTIWAV_' + self.timestamp +'.WAV'

        #        wavfile = wave.open(main_filename,'w')
        #        wavfile.setnchannels(self.rec.shape[1])
        #        wavfile.setframerate(fs)


        pass


        try:
            print('trying to save MOCK !! ')

            #scipy.io.wavfile.write(main_filename,fs,self.rec)
            print('File saved')

            pass

        except:
            raise IOError('Could not save file !!')


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


    a = fieldrecorder(150,input_output_chs=(4,2),device_name='USB' )
    fs,rec= a.thermoacousticpy()
    plt.plot(np.linspace(0,rec.shape[0]/float(fs),rec.shape[0]),rec);plt.ylim(-1,1)

