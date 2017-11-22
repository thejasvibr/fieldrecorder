# -*- coding: utf-8 -*-
"""
A bunch of functions which deal and compensate for the AD conversion delay
across the two Fireface UCs we're using

Created on Tue Nov 21 11:11:04 2017

@author: tbeleyur
"""
import os
import warnings
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
        chA,chB : np.array. the two signals to be compared
        samples_to_use: integer. number of samples to use for the actual cross correlation

    '''

    chB_chunk, chA_chunk = chB[:samples_to_use], chA[:samples_to_use]

    cross_corn = np.correlate(chB_chunk,chA_chunk,mode='same')

    peak_index = np.argmax(cross_corn)
    delay = peak_index - (cross_corn.size/2.0 )

    return(delay)


def cut_out_same_sections():

    pass

def detect_first_rising_edge(recording,fs=192000,**kwargs):
    '''
    Detects the first rising edge of a square wave signal
    and returns its index.

    Inputs:
        recording: np.array with signal
        fs: int. sampling rate 192000

    **kwargs:
        template: np.array. a template signal which is convolved with the
                        chA and chB, and the first peaks are then identified
                        Defaults to  a 25 Hz square wave with 50% duty cycle,
                        that starts with the signal equal to -1. (sine wave shifted
                        by pi radians)
        fps : integer. frames per second in Hertz, this is the frequency at which the
                        template signal repeats itself.
    Output:
        first_peak: integer. index of the the first rising edge

    '''
    if not 'template' in kwargs.keys():
        print('no template signal found, creating default template signal')
        template = create_default_template(25,fs)
    else :
        print('template signal found..proceeding with convolution')
        template = kwargs['template']

    if not 'fps' in kwargs.keys():
        print('no fps arguments found in kwargs, using 25 fps')
        mindist_pk2pk = (1.0/25)*fs -1
    else:
        print('fps argument found in kwargs, using '+str(kwargs[fps])+' Hz fps')
        mindist_pk2pk = (1.0/kwargs['fps'])*fs -1

    conv_sig = np.convolve(template[::-1],recording,'same')
    conv_sig *= 1.0/np.max(conv_sig)

    pks_conv = peakutils.indexes(conv_sig,thres=0.6,min_dist=mindist_pk2pk)

    # check if the pks_conv are all regularly spaced - indicates a well recorded
    # signal

    pk2pk_spacing = np.unique( np.diff(pks_conv) )

    if pk2pk_spacing.size > 1:
        print(pk2pk_spacing)
        line1 = 'There may be some variation in the sync signals peak-to-peak spacing, there may gaps in the recording'
        line2 = '\n Here are the unique peak to peak distances detected'
        warn_msg = line1+line2
        warnings.warn(warn_msg)

    first_peak = pks_conv[0]


    return(first_peak)

def create_default_template(sync_freq,fs=192000):
    '''
    Creates a phase shifted 50% duty cycle square wave.
    Inputs:
        sync_freq: integer. frequency of the output square wave in Hertz.
    Output:
        template: np.array. one cycle of the template signal
    '''

    one_cycledurn = 1.0/sync_freq
    t = np.linspace(0,one_cycledurn,int(fs*one_cycledurn))
    sine_fn = 2*np.pi*sync_freq*t + np.pi

    template = np.float32( signal.square(sine_fn,0.5) )

    return(template)


check_allare_int = lambda some_list: all(isinstance(item, int) for item in some_list)
# thanks Dragan Chupacabric : https://stackoverflow.com/questions/6009589/how-to-test-if-every-item-in-a-list-of-type-int
check_allare_np = lambda some_list: all(isinstance(item, np.ndarray) for item in some_list)

if __name__ == '__main__':
    r1,r2 = read_wavfile('DEVICE1_2017-11-21-10_44_20.wav'), read_wavfile('DEVICE2_2017-11-21-10_44_20.wav')
    fs,rec1 = r1

    sync_freq = 25

    one_cycledurn = 1.0/sync_freq
    t = np.linspace(0,one_cycledurn,int(fs*one_cycledurn))
    sine_fn = 2*np.pi*sync_freq*t + np.pi

    sync_signal = np.float32( signal.square(sine_fn,0.5) )

    conv_r1 = np.convolve(sync_signal[::-1],rec1,'same')
    plt.plot(conv_r1/np.max(conv_r1))
    plt.plot(rec1)

    pks = peakutils.indexes(conv_r1/np.max(conv_r1),thres=0.6,min_dist=t.size-1)
    plt.plot(pks,rec1[pks],'r*')





