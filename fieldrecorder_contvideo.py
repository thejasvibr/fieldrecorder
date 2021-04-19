"""
Module that triggers short video recordings at a fixed duty cycle until 
interrupted. 
"""
from dateutil import parser
import os
import queue
import datetime as dt
import time
import numpy as np
import sounddevice as sd
from scipy import signal


duty_cycle = 0.5
recording_duration = 20 # in seconds


# start Output Stream 

# don't record for first 60 seconds or till scheduled start time, and FFC

# start recording, and FFC after a recording is done. 

# shuttle back and forth between recording and non-recording. 




class fieldrecorder_trigger():

    def __init__(self,expt_durn, duty_cycle = 0.5, device_name='ASIO',**kwargs):
        '''    
        Parameters
        ----------
        expt_durn : float >0
            Duration of the experiment in hours.
        duty_cycle : 0 < float < 1 
            Fraction of time that recording occupies
            Defaults to 0.5.
        device_name : str
            Unique part of the soundcard to be used for signal 
            outputs. Defaults to a soundcard with 'ASIO' in its name. 
            The available soundcards are listed using sd.query_devices()
        
        Keyword Arguments
        -----------------
        fs : float >  0
            Sampling rate in Hz. Defaults to 192kHz
        warmup_durn : float >0
            The duration for which the camera warms up before starting to record in seconds. 
            Defaults to 20 s. 
        rec_bout : float > 0
            Duration of recording in seconds. 
            Defaults to 10s.
        '''
        self.expt_durn = expt_durn
        self.recording = False
        self.sync_freq = 25
        self.device_name = device_name
        self.output_chs = 3
        self.FFC_interval = 2
        self.fs = kwargs.get('fs',192000)
        self.duty_cycle = kwargs.get('duty_cycle', 0.5)
        self.warmup_durn = kwargs.get('warmup_durn', 20) # seconds

        self.num_rests = 0  # num of resting periods
        self.num_recordings = 0 # num of recording periods
        self.num_triggers =  0 # number off recording triggers

        if self.device_name  is None:
            self.tgt_ind = None
        else:
            self.get_device_indexnumber(self.device_name)

        self.rec_bout = kwargs.get('rec_bout',10) # seconds
            
        self.duty_cycle = kwargs.get('duty_cycle', 0.5)
        self.rest_bout = ((1-duty_cycle)/duty_cycle)*self.rec_bout
        
        # Prepare the output signals going to the sync and trigger channels 
        one_cycledurn = 1.0/self.sync_freq
        num_cycles = 1
        sig_durn = num_cycles*one_cycledurn
        t = np.linspace(0,sig_durn,int(self.fs*sig_durn))
        sine_fn = 2*np.pi*self.sync_freq*t + np.pi

        self.sync_signal = np.float32( signal.square(sine_fn,0.5) )
        self.sync_signal *= 0.25

        trigger_freq = 20*10**3
        
        # generate the FFC signal - which is a 20 KHz sine wave
        ffc_duration = 0.035
        t_ffc = np.linspace(0,ffc_duration, int(self.fs*ffc_duration))
        ffc_freq = 20000
        sine_ffc = np.sin(2*np.pi*ffc_freq*t_ffc)
        self.ffc_signal = np.float32(np.zeros(self.sync_signal.size))
        self.ffc_signal[:sine_ffc.size]  = sine_ffc
                
        # generate the signals across all channels that will be delivered

        # conv to 32 bit so sounddevice can take the signals as inputs
        self.trigger_signal = np.float32(np.sin(2*np.pi*t*trigger_freq))
        self.empty_signal = np.float32(np.zeros(self.sync_signal.size))

        self.only_sync = np.column_stack((self.sync_signal, self.empty_signal, self.empty_signal))
        self.trig_and_sync = np.column_stack((self.sync_signal, self.trigger_signal, self.empty_signal))       
        self.sync_and_FFC = np.column_stack((self.sync_signal, self.empty_signal, self.ffc_signal))

    def cameras_rolling(self):
        '''

        '''
        
        self.S = sd.OutputStream(samplerate=self.fs,blocksize=self.sync_signal.size,
                           channels=self.output_chs,device=self.tgt_ind)

        start_time = np.copy(self.S.time)
        rec_time = np.copy(self.S.time)
        expt_end_time =  start_time + self.expt_durn*3600
        warmup_end_time = start_time + self.warmup_durn
        self.S.start()

        # Run the cameras for warm up time and end with an FFC
        print(f'...Warming up the cameras for {self.warmup_durn} seconds')
        while self.S.time < warmup_end_time:
            self.S.write(self.only_sync)
        self.S.write(self.sync_and_FFC)
        print('.....done with warmup....')

        try:
            # Now begin recording in intervals with FFC in between 
            while self.S.time < expt_end_time:

                self.start_recording = self.decide_when_to_trigger()

                if self.start_recording:
                    print('recording....')
                    self.recbout_start_time = np.copy(self.S.time)
                    self.recbout_end_time = self.recbout_start_time + self.rec_bout
                    i = 0
                    while  self.recbout_end_time >= self.S.time:   
                        self.S.write(self.trig_and_sync)
                    self.num_recordings += 1     
                else:
                    print('resting....')
                    rest_start_time = np.copy(self.S.time)
                    rest_end_time = rest_start_time + self.rest_bout
                    self.S.write(self.sync_and_FFC)
                    while self.S.time < rest_end_time:
                        self.S.write(self.only_sync)
                    self.num_rests += 1 
            

        except (KeyboardInterrupt, SystemExit):
            print('Stopping recording ..exiting ')

        self.S.stop()

    def decide_when_to_trigger(self):
        if self.num_recordings==self.num_rests:
            return False
        elif self.num_recordings <self.num_rests:
            return True
        elif self.num_recordings >self.num_rests:
            raise Exception('There are more recordings than rests!!!')

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

    device_name = 'Fireface USB'
    expt_duration = 0.1 # in hours
    recording_duration = 3 # in seconds
    # When the experiment should start -- remember to account for warm up time 
    # where no recording takes place s
    experiment_start_time = "16 April 2021  22:00"
    experiment_initiation = parser.parse(experiment_start_time)
    
    sleep_expt = fieldrecorder_trigger(expt_durn=expt_duration,
                                       duty_cycle = 0.5,
                                       device_name= device_name, 
                                       rec_bout = recording_duration)

    while  dt.datetime.now() < experiment_initiation:
            time.sleep(5.0)
            print('...waiting for experiment start time ....')
   
    sleep_expt.cameras_rolling()