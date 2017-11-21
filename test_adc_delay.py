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



        fs,rec1 = read_wavfile('DEVICE1_2017-11-21-10_44_20.wav')
        fs,rec2 = read_wavfile('DEVICE2_2017-11-21-10_44_20.wav')

        actual_delay = estimate_delay(rec2,rec1)

        expected_delay = -42

        self.assertEqual(expected_delay,actual_delay)

        pass



    def test_delay(self)  :
        '''
        has to have a test_ otherwise the method won't be run !!
        '''
        # miaow
        pass





if __name__ == '__main__':
    unittest.main()