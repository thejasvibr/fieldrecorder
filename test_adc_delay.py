# -*- coding: utf-8 -*-
"""
Created on Tue Nov 21 11:34:59 2017

@author: tbeleyur
"""
from os import path
import unittest
from scipy import signal
import numpy as np
from ADC_delay import *


class TestADC_delay(unittest.TestCase):

    def setUp(self):

        fs,self.rec1 = read_wavfile('DEVICE1_2017-11-21-10_44_20.wav')
        fs,self.rec2 = read_wavfile('DEVICE2_2017-11-21-10_44_20.wav')

        # create a 16 channel recording with 30 samples delay between device 1
        # (channels 0:7, and device 2, channels 8:15)

        self.multich_rec = np.random.normal(0,0.5,fs*16).reshape((-1,16))

        t = np.linspace(0,1,fs)
        FPS = 25
        sine_t = np.sin(2*np.pi*t*FPS - np.pi)
        sync_signal = signal.square(sine_t)

        self.adc_delay = 30 # the delay in AD conversion between the two devices
        self.pbk_delay = int(0.2*fs) # simulate the delay due to the DAC of the playback
        self.multich_rec[:,7] = np.roll(sync_signal,self.pbk_delay)
        self.multich_rec[:pbk_delay,7] = 0
        self.multich_rec[:,15] = np.roll(sync_signal,self.pbk_delay+self.adc_delay)
        self.multich_rec[:adc_delay+pbk_delay,15] = 0





    def test_delayestimation(self)  :
        '''
        has to have a test_ otherwise the method won't be run !!
        '''
        # test with two exact replicas of a signal shifted by a few indices
        x = np.random.normal(0,1,10000)

        y = np.copy(x)

        delay_inds = 3

        y = np.roll(y,delay_inds);

        delay = estimate_delay(y,x)

        self.assertEqual(delay_inds,delay)

        # now test with real wav files of the sync signals:

        self.current_folder = os.path.abspath(__file__)
        print(self.current_folder)


        actual_delay = estimate_delay(self.rec2,self.rec1)

        known_delay = -28

        self.assertEqual(known_delay,actual_delay)

        pass


    def test_detect_firstrisingedge(self):

        fs = 192000
        sync_freq = 25

        one_cycledurn = 1.0/sync_freq
        t = np.linspace(0,one_cycledurn,int(fs*one_cycledurn))
        sine_fn = 2*np.pi*sync_freq*t + np.pi

        sync_signal = np.float32( signal.square(sine_fn,0.5) )

        continuous_sync = np.tile(sync_signal,10)
        samples_silence = 1000
        test_signal = np.concatenate((np.zeros(samples_silence),continuous_sync))

        first_peak_notemplate = detect_first_rising_edge(test_signal, fs=192000)

        risingedge_index = t.size/2 + samples_silence

        self.assertEqual(first_peak_notemplate,risingedge_index)

        first_peak_withtemplate = detect_first_rising_edge(test_signal,fs=192000,template=sync_signal)

        self.assertEqual(first_peak_withtemplate,risingedge_index)


        # now try with a weird sync signal - it should throw a warning but still
        # return the correct first rising edge:

        jittered_syncsignal = np.concatenate((test_signal,np.zeros(samples_silence),test_signal))
        peak1_wjittered  = detect_first_rising_edge(jittered_syncsignal,fs=192000)

        self.assertEqual(peak1_wjittered,risingedge_index)

        pass

    def test_alignchannels(self):

        #align_channels(multichannel_rec, channel2device,cut_points={'ADC1':0,'ADC2':0})

        ch2device = {'1':range(8),'2':range(8,16)}

        cutpoints = {'1':self.pbk_delay,'2':self.pbk_delay+self.adc_delay}

        timealigned_rec = align_channels(self.multich_rec,ch2device,cutpoints)

        # check if the values of the sync signal are the same - to make sure they are time aligned !
        self.assertEqual(timealigned_rec[1,7],timealigned_rec[1,15])


        pass



if __name__ == '__main__':
    unittest.main()