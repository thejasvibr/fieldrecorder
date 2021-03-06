# -*- coding: utf-8 -*-
"""
VERSION 0.000
TODO :
    > fix the default output channel number

A completely dongle-free approach to control the thermal cameras
and mics based on the sounddevice library !!

The current script is tailored for use in the audio-thermal recording array
to be used in the field to record bats.

Based on the AVR Soundmexpro based scripts written with
Holger R. Goerlitz

Usage instructions :

Press F5 to run the script start the sync signal playback, you should now have
camera live feed

    To begin recording press any key

    To stop recording press any key again

    To end the session , either :
        a) Interrupt with a system exit : CTRL+c (creates a tiny file at the end because of keyboard triggering)
        b) Press the interrupt button with the mouse (doesn't create an extra file )
            This only works on the IPython shell

The program records N input channels simultaneously and outputs 3 signals when
triggered for recording:

    channel 1: sync. a square 25 Hz signal . The rising edge causes all Thermalcapture
                cameras to capture a frame
    channel 2: trigger. a 20KHz sine wave. when this signal is played the frames
                captured by the cameras are saved to disk.
    channel 3: cross-device sync signal. A copy of the sync signal is played back
                through split BNC cables fed into two Fireface UCs. This allows
                an estimation of the AD conversion delay between the devices


By default, even though data is being collected from all channels, only some channels
are saved into the wav file.

Created on Mon Nov 06 18:10:01 2017

 Version 0.0.0 ( semantic versioning number)

@author: Thejasvi Beleyur
"""
import os
import Queue
import datetime as dt
import time
import numpy as np
import sounddevice as sd
from scipy import signal
import soundfile
import matplotlib.pyplot as plt
plt.rcParams['agg.path.chunksize'] = 10000
from pynput.keyboard import  Listener



class fieldrecorder():

    def __init__(self,rec_durn,device_name=None,input_output_chs=(2,2),target_dir = '~\\Desktop\\',**kwargs):
        '''

        Inputs:
        rec_durn : float. duration of the whole session in seconds
        device_name : string. name of the device as shown by sd.query_devices()
                    Defaults to None - which will throw an error if there are not at
                    least 3 output channels

        input_output_chs: tuple with integers. Number of channels for recording and playback.

        target_dir : file path. place where the output WAV files will be saved

        **kwargs:
            exclude_channels: list with integers. These channels will not be saved
                              into the WAV file. Defaults to the digital channels
                              in the double Fireface UC setup



        '''
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

        try:
            expanded_path = os.path.expanduser(target_dir)
            os.chdir(expanded_path)
        except:
            raise ValueError('Unable to find the target directory: ' + target_dir)


        # unless stated specifically exclude the digital input channels
        # from both Firefaces;
        #Device 1: 9:12 , Device 2: 21:24

        self.all_recchannels = range(self.input_output_chs[0])

        if 'exclude_channels' not in kwargs:
            self.exclude_channels = [8,9,10,11,20,21,22,23]
        else:
            self.exclude_channels = kwargs['exclude_channels']

        self.save_channels  = list(set(self.all_recchannels) - set(self.exclude_channels))



    def thermoacousticpy(self):
        '''
        Performs the synchronised recording of thermal cameras and audio.

        '''

        self.fs = 192000
        one_cycledurn = 1.0/self.sync_freq
        num_cycles = 1
        sig_durn = num_cycles*one_cycledurn
        t = np.linspace(0,sig_durn,int(self.fs*sig_durn))
        sine_fn = 2*np.pi*self.sync_freq*t + np.pi

        self.sync_signal = np.float32( signal.square(sine_fn,0.5) )
        self.sync_signal *= 0.25

        trigger_freq = 20*10**3

        # conv to 32 bit so sounddevice can take the signals as inputs
        self.trigger_signal = np.float32(np.sin(2*np.pi*t*trigger_freq))
        self.empty_signal = np.float32(np.zeros(self.sync_signal.size))

        self.only_sync = np.column_stack((self.sync_signal, self.empty_signal,
                                          self.empty_signal))

        self.trig_and_sync = np.column_stack((self.sync_signal, self.trigger_signal,
                                                  self.sync_signal))


        self.S = sd.Stream(samplerate=self.fs,blocksize=self.sync_signal.size,
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

        except (KeyboardInterrupt, SystemExit):

            print('Stopping recording ..exiting ')

            kb_input.stop()


        self.S.stop()

        print('Queue size is',self.q.qsize())

        return(self.fs,self.rec)



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

        self.rec2besaved = self.rec[:,self.save_channels]

        timenow = dt.datetime.now()
        self.timestamp = timenow.strftime('%Y-%m-%d_%H-%M-%S')
        self.idnumber =  int(time.mktime(timenow.timetuple())) #the unix time which provides a 10 digit unique identifier

        main_filename = 'MULTIWAV_' + self.timestamp+'_'+str(self.idnumber) +'.WAV'

        try:
            print('trying to save file... ')

            soundfile.write(main_filename,self.rec2besaved,self.fs)

            print('File saved')

            pass

        except:
            raise IOError('Could not save file !!')


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
                             ' \n Please use sd.query_devices to check the  recognised'
                             +' devices on this computer')

        if sum(self.tgt_dev_bool) > 1 :
           raise ValueError('Multiple devices with the same string found'
           + ' please enter a more specific device name'
           ' \n Please use sd.query_devices to check the recognised'+
           ' devices on this computer')

        else:
            self.tgt_ind = int(np.argmax(np.array(self.tgt_dev_bool)))


  

if __name__ == '__main__':

    dev_name = 'Fireface USB'
    in_out_channels = (28,3)
    tgt_direcory = 'C:\\Users\\tbeleyur\\Documents\\fieldwork_2018_002\\actrackdata\\wav\\2018-08-19_003\\'
    #tgt_direcory = 'C:\\Users\\tbeleyur\\Documents\\figuring_out\\Uschichka_testing\\Scarlett_ADAT_channels_simultaneous\\'


    a = fieldrecorder(1500, input_output_chs= in_out_channels, device_name= dev_name,
                      target_dir= tgt_direcory, exclude_channels=[] )
    fs,rec= a.thermoacousticpy()
    #plt.plot(np.linspace(0,rec.shape[0]/float(fs),rec.shape[0]),rec[:,7]);plt.ylim(-1,1)


