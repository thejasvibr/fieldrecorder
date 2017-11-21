# -*- coding: utf-8 -*-
"""
Loads a multichannel wav file and compares two channels with a synchronising
signal to estimate the AD conversion delay between the two channels

Created on Tue Nov 21 11:11:04 2017

@author: tbeleyur
"""
import os
from scipy import signal
import scipy.io.wavfile
import numpy as np
import peakutils
from matplotlib import pyplot as plt
plt.rcParams['agg.path.chunksize'] = 10000




def read_wavfile(fileaddress):

    fs,rec = scipy.io.wavfile.read(fileaddress)

    return(fs,rec)


def select_channels(channel_list,multichannel_rec):
    '''
    selects only those channels which are in the channel list
    '''
    if not check_allare_int(channel_list):
        raise ValueError('channel list entries can only be integers!!')

    subset_channels = multichannel_rec[:,channel_list]

    return(subset_channels)

def estimate_delay(chB,chA,samples_to_use=10**3):
    '''
    estimates delay by looking at the peak in the cross-correlation function
    The function provides the delay in samples wrt channel A.

    eg. if estimate_delay gives +3, this means chB is +3 indices delay with ref
    -erence to channel A.

    Inputs:
        chA,chB : array-like.
        samples_to_use: integer. number of samples to use for the actual cross correlation
    '''

    chB_chunk, chA_chunk = chB[:samples_to_use], chA[:samples_to_use]

    cross_corn = np.correlate(chB_chunk,chA_chunk,mode='same')

    peak_index = np.argmax(cross_corn)
    delay = peak_index - (cross_corn.size/2.0 )

    return(delay)


def cut_out_same_sections():

    pass

def detect_first_rising_edge(recording,fs=192000,fps=25.0):
    '''
    Detects the first rising edge and returns index
    '''
    minsamples_pk2pk = (1.0/fps)*fs -1




    return(first_peak)

check_allare_int = lambda some_list: all(isinstance(item, int) for item in some_list)
# thanks Dragan Chupacabric : https://stackoverflow.com/questions/6009589/how-to-test-if-every-item-in-a-list-of-type-int







