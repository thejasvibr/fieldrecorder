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

        self.rec_durn = 0.8
        self.multich_rec = np.random.normal(0,0.5,int(self.rec_durn*fs*16)).reshape((-1,16))

        self.t = np.linspace(0,self.rec_durn,int(self.rec_durn*fs))
        FPS = 25
        self.sine_t = np.sin(2*np.pi*self.t*FPS - np.pi)
        self.sync_signal = signal.square(self.sine_t)

        self.adc_delay = 300 # the delay in AD conversion between the two devices
        self.pbk_delay = int(0.2*fs) # simulate the delay due to the DAC of the playback

        #assign channels 7 and 15 to the sync signal and mimic the experimental delays induced
        # during recording
        self.multich_rec[:,7] = np.roll(self.sync_signal,self.pbk_delay)
        self.multich_rec[:self.pbk_delay,7] = 0
        self.multich_rec[:,15] = np.roll(self.sync_signal,self.pbk_delay+self.adc_delay)
        self.multich_rec[:self.adc_delay+self.pbk_delay,15] = 0




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

        # now test with real wav files of the square sync signals:

        actual_delay = estimate_delay(self.rec2,self.rec1,10**5)

        known_delay = -28

        self.assertEqual(known_delay,actual_delay)

        pass


    def test_detect_firstrisingedge(self):

        print('test_detect_firstrisingedge \n')

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

        print('test_alignchannels \n')

        #align_channels(multichannel_rec, channel2device,cut_points={'ADC1':0,'ADC2':0})
        print('test_alignchannels')

        ch2device = {'1':range(8),'2':range(8,16)}

        cutpoints = {'1':self.pbk_delay,'2':self.pbk_delay+self.adc_delay}

        timealigned_rec = align_channels(self.multich_rec,ch2device,cutpoints)

        # check if the values of the sync signal are the same - to make sure they are time aligned !
        try:
            np.testing.assert_array_almost_equal(timealigned_rec[:,7],timealigned_rec[:,15])
        except:
            raise ValueError('The sync channels are not lined up! ')
        #self.assertEqual(timealigned_rec[index_common,7],timealigned_rec[index_common,15])

        pass

    def test_timealign_channels(self):
        '''
        check how all of the functions behave together and see if it throws any
        errors
        '''

        print('test_timealign_channels \n')

        fs = 192000

        nchannels = 16
        multich_rec2 = np.random.normal(0,0.5,int(self.rec_durn*fs*nchannels)).reshape((-1,nchannels))

        adc_delay2 = 50
        pbk_delay2 = int(0.1*fs)

        multich_rec2[:,7] = np.roll(self.sync_signal,pbk_delay2)
        multich_rec2[:pbk_delay2,7] = 0
        multich_rec2[:,15] = np.roll(self.sync_signal,pbk_delay2+adc_delay2)
        multich_rec2[:adc_delay2+pbk_delay2,15] = 0


        ch2devs = {'1':range(8),'2':range(8,16)}
        sync2devs = {'1':7,'2':15}

        ta_channels  = timealign_channels(multich_rec2,192000, ch2devs,sync2devs,with_sync=True)
        try:
            np.testing.assert_array_almost_equal(ta_channels[:,7],ta_channels[:,15])
        except:
            raise ValueError('The sync channels are not lined up! ')

    def test_checkifconcatenationworksproperly(self):
        '''
        Are the channels getting cut and assembled properly back together ?

        Assign all values in each column their channel number and recreate
        playback delay + ADC delay across 2 devices.

        Recreate the sync signal playback delay and ADc delay.

        Run through time_align and check if the first samples of all channels
        (without the sync signal) are returned in the expected order

        '''
        print('\n test_ifconcatenationworks')
        fs = 192000
        nchannels = 16
        unique_channel_rec  = np.zeros((fs,nchannels))
        channels2devs = {'1':range(8),'2':range(8,16)}
        audiochannels2devs = { '1': range(7),'2': range(8,15)}
        syncchannels2devs ={'1':7,'2':15}

        pbk_delay = int(0.2*fs)
        adc_delay = 40

        delays2devs = {'1':pbk_delay,'2':adc_delay+pbk_delay}

        #assign channel values to all the audio channels

        i = 0
        for device,device_channels in audiochannels2devs.items():
            samples_delay = delays2devs[device]

            for each_channel in device_channels:
                unique_channel_rec[samples_delay:,each_channel] = i
                i += 1

        # create sync channels:
        t = np.linspace(0,1,fs)
        sine = np.sin(2*np.pi*25*t - np.pi)
        sync = signal.square(sine)

        for device,ch_index in syncchannels2devs.items():

            unique_channel_rec[ delays2devs[device]:,ch_index] = sync[:-delays2devs[device]]

        print(' \n '+str(unique_channel_rec[0,:]))

        test_timealign = timealign_channels(unique_channel_rec,fs,channels2devs,syncchannels2devs)

        expected_firstsamples = np.array(range(nchannels-2))
        same_arrays = expected_firstsamples == test_timealign[0:,:]

        self.assertTrue(np.all(same_arrays))

    def test_checkforoverlaps_list(self):

        print('\n test_checkforoverlaps_list')
        ch1 = [0,1,2,3,4]
        ch2 = [5,6,7,8]
        ch2dev_test1 = {'1':ch1,'2':ch2}

        self.assertFalse(check_for_overlaps(ch2dev_test1))

        ch2dev_test2 = {'1':[0,1,2,3],'2':[2,3]} # with overlap

        try:
            check_for_overlaps(ch2dev_test2)
        except ValueError, E:
            self.assertEquals('Some channels may have been specified twice across different devices!',
                              E.message)

        pass

    def  test_checkforoverlaps_int(self):
        sync2dev_case1 = {'1':1,'2':2}

        self.assertFalse(check_for_overlaps(sync2dev_case1))

        sync2dev_case2 = {'1':1,'2':1}

        try:
            check_for_overlaps(sync2dev_case2)
        except ValueError, E:
            self.assertEquals('Some channels may have been specified twice across different devices!',
                              E.message)











if __name__ == '__main__':
    unittest.main()