# -*- coding: utf-8 -*-
"""
Created on Tue Nov 21 11:34:59 2017

@author: tbeleyur
"""
from os import path
import unittest
import numpy as np
from ADC_delay import *


class TestADC_delay(unittest.TestCase):

    def setUp(self):

        fs,self.rec1 = read_wavfile('DEVICE1_2017-11-21-10_44_20.wav')
        fs,self.rec2 = read_wavfile('DEVICE2_2017-11-21-10_44_20.wav')





        #self.25Hztemplate


    def test_delayestimation(self)  :
        '''
        has to have a test_ otherwise the method won't be run !!
        '''
        x = np.random.normal(0,1,10000)

        y = np.copy(x)

        delay_inds = 3

        y = np.roll(y,delay_inds);

        delay = estimate_delay(y,x)

        self.assertEqual(delay_inds,delay)

        # now test with real wav files of the sync signals:

        self.current_folder = os.path.abspath(__file__)


        actual_delay = estimate_delay(self.rec2,self.rec1)

        expected_delay = -42

        self.assertEqual(expected_delay,actual_delay)

        pass



    def test_delay(self)  :
        '''
        has to have a test_ otherwise the method won't be run !!
        '''

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






if __name__ == '__main__':
    unittest.main()