# -*- coding: utf-8 -*-
"""
Part of the fieldrecorder python modules written to handle sychronised audio-video recordings 
with ASIO based soundcards and the TeAx ThermalCapture cameras. 

This version is built with the express purpose of making recordings for the series of Phyllo experiments carried out 
at the lab over the summer of 2020. 

The output of the recordings need have the following features:

1. Direct disk saving of the data as it is captured from device. 
2. Recordings are triggered by a keyboard touch, and cannot be stopped until the designated time is over. 
   All recordings need to of a fixed length  +/- some time (few seconds offset on purpose, to allow easy
   correspondence matching between audio and video files).
3. Every file will have a unique counter number, with the counter number increasing by 1 per recording - this number is dependent on the 
computer which is running the whole setup. 


@author: Thejasvi Beleyur, August 2020
Code released under an MIT License
"""
import os
import Queue
import datetime as dt
import time
import numpy as np
import pandas as pd
import sounddevice as sd
from scipy import signal
import soundfile as sf
from pynput.keyboard import  Listener



class fieldrecorder_phyllo():

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

            one_recording_duration
            one_recording_pm

        '''
        self.rec_durn = rec_durn
        self.press_count = 0
        self.start_recording = False
        self.sync_freq = 25
        self.device_name = device_name
        self.input_output_chs = input_output_chs
        self.target_dir = target_dir
        
        self.one_recording_duration = kwargs.get('one_recording_duration',300) # seconds
        self.one_recording_pm = kwargs.get('one_recording_pm', np.arange(0,5,0.25)) # the additional range with which all recordings are expected to vary.
        try:
            self.counter_file = kwargs['counter_file']
        except:
            raise ValueError('The path of the counter file has not been declared!!')

        if self.device_name  is None:
            self.tgt_ind = None
        else:
            self.get_device_indexnumber(self.device_name)

        try:
            expanded_path = os.path.expanduser(target_dir)
            os.chdir(expanded_path)
        except:
            raise ValueError('Unable to find the target directory: ' + target_dir)

        self.all_recchannels = range(self.input_output_chs[0])
        
        self.exclude_channels = kwargs.get('exclude_channels', [])

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
                           channels=self.input_output_chs,device=self.tgt_ind,
                           latency='low')

        start_time = np.copy(self.S.time)
        session_time = np.copy(self.S.time)
        session_end_time =  start_time + self.rec_durn
        

        self.q = Queue.Queue()

        self.S.start()

        kb_input = Listener(on_press=self.on_press)

        kb_input.start()
        print('Trying to initiate recordings...')
        try:

            while session_time < session_end_time:
                if self.start_recording:
                    audiofilename = self.make_filename()
                    
                    
                    now = time.time() 
                    recording_endtime = now + self.one_recording_duration + float(np.random.choice(self.one_recording_pm,1))
                    print('Approx. end time of recording:', time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(recording_endtime)))
                    with sf.SoundFile(audiofilename, mode='x', samplerate=self.fs,
                                                    channels=len(self.save_channels)) as file:
                        while time.time() < recording_endtime:
                        
                            data, success = self.S.read(self.trig_and_sync.shape[0])
                            file.write(data[:,self.save_channels])
                            self.S.write(self.trig_and_sync)
                        self.start_recording = False
                    print('Recording done- press any key to trigger the next recording... \n'+'The saved filename is: ' +  audiofilename)
                    self.increment_filecounter()

                else :
                    self.S.write(self.only_sync)

                session_time = self.S.time

            kb_input.stop()

        except (KeyboardInterrupt, SystemExit):

            print('Stopping recording ..exiting ')

            kb_input.stop()


        self.S.stop()

        print('Queue size is',self.q.qsize())

        return(self.fs,self.rec)

    def make_filename(self):
        '''
        Creates a file name that begins with MULTIWAV_YYYY-MM-DD_hh-mm-ss_UNIQUENUMBER
        '''
        timenow = dt.datetime.now()
        self.timestamp = timenow.strftime('%Y-%m-%d_%H-%M-%S')
        self.idnumber =  int(time.mktime(timenow.timetuple())) #the unix time which provides a 10 digit unique identifier

        prefix_filename = 'MULTIWAV_' + self.timestamp+'_'+str(self.idnumber) 
        print('UNIQUE COUNTER NOT IMPLEMENTED YET!!!..................')
        
        try:
            self.unique_number = int(pd.read_csv(self.counter_file, delimiter=',')['recording_number'])
        except:
            self.unique_number = int(pd.read_csv(self.counter_file, delimiter=';')['recording_number'])
        
        final_filename = prefix_filename+'_'+str(self.unique_number)+'.wav'
        return final_filename
    
    def increment_filecounter(self):
        '''
        Increments filenumber count and saves the data into the counter file. 
        '''
        new_df = pd.DataFrame(data={'recording_number':[self.unique_number+1]})
        new_df.to_csv(self.counter_file)

    def on_press(self,key):

        # if a recording has already been initiated then don't do anything
        if self.start_recording:
            print('Recording underway - wait till current recording is done!!')
            pass
        else:
            print('button pressed....\n')
            self.start_recording = True
            print('recording started.....')


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
    print('Starting recording session.....................')

    dev_name = 'ASIO'
    in_out_channels = (32,3)
    tgt_direcory = 'C:\\Users\\batmobil\\Documents\\phyllo_expts_july2020\\experiment_audio\\'

    channels_to_exclude = [12,13,14,15, 28,29,30,31]
    a = fieldrecorder_phyllo(9000, input_output_chs= in_out_channels, device_name= dev_name,
                      target_dir= tgt_direcory, exclude_channels=channels_to_exclude,one_recording_duration=300,
                      one_recording_pm =np.arange(0,0.5,0.05),
                      counter_file='~\\Desktop\\recording_counter.csv')
    fs,rec= a.thermoacousticpy()

