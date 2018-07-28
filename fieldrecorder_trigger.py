# -*- coding: utf-8 -*-
"""
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



class fieldrecorder_trigger():

    def __init__(self,rec_durn, duty_cycle = None, device_name=None,input_output_chs=(2,2),
                 target_dir = '~\\Desktop\\',**kwargs):
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
            
            rec_bout : integer. Number of seconds each recording bout should be 
                       Defaults to 10 seconds.
            
            trigger_level : integer <=0. The dB rms for the level at which the recordings
                        get triggered.
            monitor_channels : array like with integers. Channel indices that will be 
                               used for monitoring
            
            bandpass_freqs : tuple. Highpass and lowpass frequencies for the trigger calculation
                       Defaults to the whole frequency spectrum.

        '''
        self.rec_durn = rec_durn
        self.press_count = 0
        self.recording = False
        self.sync_freq = 25
        self.device_name = device_name
        self.input_output_chs = input_output_chs
        self.target_dir = target_dir
        self.FFC_interval = 2
        self.fs = 192000
        self.duty_cycle = duty_cycle

        

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

        if 'exclude_channels' not in kwargs.keys():
            self.exclude_channels = [8,9,10,11,20,21,22,23]
        else:
            self.exclude_channels = kwargs['exclude_channels']

        self.save_channels  = list(set(self.all_recchannels) - set(self.exclude_channels))
        
        # set the recording bout duration : 
        if 'rec_bout' not in kwargs.keys():
            self.rec_bout = 10
        else : 
            self.rec_bout = kwargs['rec_bout']

        if 'trigger_level' not in kwargs.keys():
            self.trigger_level = -50 # dB level ref max
        else:
            self.trigger_level = kwargs['trigger_level']
        
        if 'monitor_channels' not in kwargs.keys():
            self.monitor_channels = [0,1,2,3]
        else:
            self.monitor_channels = kwargs['monitor_channels']
        
        if 'bandpass_freqs' in kwargs.keys():
            self.highpass_freq, self.lowpass_freq = kwargs['bandpass_freqs']
            nyq_freq = self.fs/2.0
            self.b, self.a = signal.butter(4, [self.highpass_freq/nyq_freq,
                                               self.lowpass_freq/nyq_freq],
                                btype='bandpass')
            self.bandpass = True
        else:
            self.bandpass = False
            
        if duty_cycle is None:
            self.minimum_interval = 0
        else:
            self.minimum_interval = ((1-duty_cycle)/duty_cycle)*self.rec_bout
            

    def thermoacousticpy(self):
        '''
        Performs the synchronised recording of thermal cameras and audio.

        '''

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

        self.only_sync = np.column_stack((self.sync_signal, self.empty_signal,
                                          self.empty_signal, self.empty_signal,
                                          self.empty_signal))

        self.trig_and_sync = np.column_stack((self.sync_signal, self.trigger_signal,
                                              self.sync_signal,self.empty_signal,
                                              self.empty_signal,))
        
        self.sync_and_FFC = np.column_stack((self.sync_signal, self.empty_signal,
                                          self.empty_signal, self.empty_signal,
                                          self.ffc_signal))


        self.S = sd.Stream(samplerate=self.fs,blocksize=self.sync_signal.size,
                           channels=self.input_output_chs,device=self.tgt_ind)

        start_time = np.copy(self.S.time)
        rec_time = np.copy(self.S.time)
        end_time =  start_time + self.rec_durn


        self.q = Queue.Queue()

        self.S.start()
        num_recordings = 0
        ffc_recnum = -999
        prev_rectime = 0.0
        
        try:

            while rec_time < end_time:
                
                self.mic_inputs = self.S.read(self.trig_and_sync.shape[0])
                self.ref_channels = self.mic_inputs[0][:,self.monitor_channels]
                self.ref_channels_bp = self.bandpass_sound(self.ref_channels)
                self.above_level = self.check_if_above_level(self.ref_channels_bp)
                
                # if duty cycle recording implemented:
                if self.above_level:
                    self.start_recording = self.minimum_interval_passed(self.S.time,
                                                                    prev_rectime,
                                                                    self.minimum_interval)
                else:
                    self.start_recording = False
                
                if self.start_recording:
                    print('starting_recording')
                    self.recbout_start_time = np.copy(self.S.time)
                    self.recbout_end_time = self.recbout_start_time + self.rec_bout
                    i = 0
                    print(self.S.time)
                    while  self.recbout_end_time >= self.S.time:   
                        if i != 0:
                            self.q.put(self.S.read(self.trig_and_sync.shape[0]))
                        else:
                            self.q.put(self.mic_inputs)
                        
                        self.S.write(self.trig_and_sync)
                        i += 1
                        
                    print(self.S.time)    
                    self.empty_qcontentsintolist()
                    self.save_qcontents_aswav()
                    self.start_recording = False    

                    num_recordings += 1 
                    prev_rectime = np.copy(self.S.time)
                else :
                    
                    ffc_initiate = np.remainder(num_recordings,
                                                self.FFC_interval) == 0                    
                    if ffc_initiate:
                        # check if FFC has already taken place:
                        if ffc_recnum != num_recordings:
                            self.S.write(self.sync_and_FFC)    
                            ffc_recnum = np.copy(num_recordings)                               
                
                    self.S.write(self.only_sync)
            

        except (KeyboardInterrupt, SystemExit):
            print('Stopping recording ..exiting ')

        self.S.stop()
        print('Queue size is',self.q.qsize())
        return(self.fs,self.rec)

    def minimum_interval_passed(self,timenow,last_recordingtime,
                                minimum_interval):
        ''' Calculates the time difference between the time at which the threshold
        is crossed and the last made recording to see if the elapsed time is
        beyond a minimum interval
        '''
        interval = timenow - last_recordingtime
        if interval < 0 :
            raise ValueError('Time elapsed cannot be <0!')

        if interval >= minimum_interval:            
            return(True)
        else:
            return(False)
    

    def bandpass_sound(self, rec_buffer):
        """
        """
        if self.bandpass:
            rec_buffer_bp = np.apply_along_axis(lambda X : signal.lfilter(self.b, self.a, X),
                                                0, rec_buffer)
            return(rec_buffer_bp)
        else:
            return(rec_buffer)

    def check_if_above_level(self, mic_inputs):
        """Checks if the dB rms level of the input recording buffer is above
        threshold. If any of the microphones are above the given level then 
        recording is initiated. 
        
        Inputs:
            
            mic_inputs : Nsamples x Nchannels np.array. Data from soundcard
            
            level : integer <=0. dB rms ref max . If the input data buffer has an
                    dB rms >= this value then True will be returned. 
                    
        Returns:
            
            above_level : Boolean. True if the buffer dB rms is >= the trigger_level
        """

        dBrms_channel = np.apply_along_axis(self.calc_dBrms, 0, mic_inputs)        
        above_level = np.any( dBrms_channel >= self.trigger_level)
        return(above_level)
        
    def calc_dBrms(self, one_channel_buffer):
        """
        """
        squared = np.square(one_channel_buffer)
        mean_squared = np.mean(squared)
        root_mean_squared = np.sqrt(mean_squared)
        try:
            dB_rms = 20.0*np.log10(root_mean_squared)
        except:
            dB_rms = -999.
        return(dB_rms)


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
            self.tgt_ind = int(np.argmax(3np.array(self.tgt_dev_bool)))






if __name__ == '__main__':

    dev_name = 'Fireface USB'
    in_out_channels = (24,5)
    tgt_directory = 'C:\\Users\\tbeleyur\\Documents\\fieldwork_2018\\actrackdata\\wav\\2018-07-25_002\\'
    #tgt_directory = 'C:\\Users\\tbeleyur\\Desktop\\test\\'

    a = fieldrecorder_trigger(3500, input_output_chs= in_out_channels,
                              device_name= dev_name, target_dir= tgt_directory,
                              trigger_level=-1.0, duty_cycle=0.18,
                              monitor_channels=[0,1,4], rec_bout = 15.0,
                              bandpass_freqs = [20000.0, 60000.0]
                              )
    fs,rec= a.thermoacousticpy()


