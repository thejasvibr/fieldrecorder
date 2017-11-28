# -*- coding: utf-8 -*-
"""
TODO:
 > write function to save each file in the desired format


A bunch of functions which deal and compensate for the AD conversion delay
across the two Fireface UCs we're using

Created on Tue Nov 21 11:11:04 2017

@author: tbeleyur
"""
from __future__ import division
import itertools,os
import warnings
from scipy import signal
import scipy.io.wavfile
import numpy as np
import peakutils
import datetime,time
from matplotlib import pyplot as plt
plt.rcParams['agg.path.chunksize'] = 10000


def timealign_channels(multich_rec,fs=192000,channels2devices={'1':range(12),'2':range(12,24)},syncch2device={'1':7,'2':19},**kwargs):
    '''
    Temporally aligns channels recorded from multiple AD converters based on
    a commonly recorded sync signal from all the devices

    The total number of samples recorded across all devices must be the same !

    Inputs:
        multich_rec : nsamples x nchannels np.array. the recorded signal from
                      all devices

        fs : integer. sampling rate of the AD devices in Hertz.

        channesl2devices: dictionary. keys are names of the AD converters and entries
                          are array-like with the channel indices belonging to each AD
                          converter.

                          eg. if there was a 16 channel recording across 2 AD converters
                          with the first 8 channels by provided from AD device 1
                          and the next 8 by ADC2, then :

                          channels2devices ={ '1':range(8),'2':range(8,16)}

                          Defaults to the experimental settings used by Thejasvi Beleyur

        syncch2device: dictionay. keys are names of the AD converters and entries
                          are integers indicating the channels used to record the
                          common sync signal

                          eg.if sync signals were recorded on channel index 7 and 15, then:

                          sync_channels = {'1':7,'2':15}

                          Defaults to the experimental settings used by Thejasvi Beleyur
        **kwargs:

            template_signal: np.array. the template square wave signal to get the first index that
                             matches it

            with_sync : Boolean. defaults to False. If True, then returns all the channels
                        with the time-aligned sync channel too. Otherwise, only the
                        audio channels are returned


    '''
    num_recch = multich_rec.shape[1]
    num_synch = len(syncch2device)
    num_devices = len(channels2devices)

    if not multich_rec.shape[1] == num_recch:
        raise ValueError('All channels have not been assigned to an ADC device! \n There is a mismatch in the channel dimensions and input channels of channels2devices')

    if not num_synch == num_devices:
        raise ValueError('Incorrect number of sync channels or devices  have been assigned.')


#    check_for_overlaps(channels2devices)
#    check_for_overlaps(syncch2device)

    # estimate delay between different ADC devices

    sync_chlist = [ch_index for eachdevice,ch_index in syncch2device.items()]
    sync_channels = select_channels(sync_chlist,multich_rec)

#    rec_durn = multich_rec.shape[0]/fs

#    if rec_durn < 0.5:
#        samples2use = multich_rec.shape[0] -1
#    else:
#        samples2use = 10**5

    rising_edges = np.apply_along_axis(detect_first_rising_edge,0,sync_channels,fs)

    cutpoints= { devs: rising_edges[index] for index,devs in enumerate(channels2devices)}

    # remove the sync channels and select only the audio channels
    all_channels = set( range(multich_rec.shape[1]) )
    audio_chindex = list( all_channels - set(sync_chlist))

    # time align the audio channels

    timealigned_channels = align_channels(multich_rec,channels2devices,cutpoints)

    if 'with_sync' in kwargs and kwargs['with_sync']:
        return(timealigned_channels)

    else:
        timealigned_audio  = select_channels(audio_chindex,timealigned_channels)

        return(timealigned_audio)


def read_wavfile(fileaddress):
    '''
    read wav file and return a np array with -1 <= values <= 1
    '''

    fs,rec = scipy.io.wavfile.read(fileaddress)

    if not np.all(rec<=1) & np.all(rec>=-1):


        normalise_values = {'int16':lambda X : X/(-1 + 2.0**15) ,
                            'int32':lambda X : X/(-1 + 2.0**31),
                           }

        if rec.dtype in ['int16','int32']:
            norm_rec = np.float32(normalise_values[str(rec.dtype)](rec))

            return(fs,norm_rec)

        else:
            raise ValueError('dtype of this wav file cannot be converted into \
            -1 to +1 bounded np array - please try another function to \
            load this wav file')
    else :
        return(fs,rec)

def write_wavfile(input_nparray,fs,intended_name):

    if not input_nparray.dtype == 'float32':
        input_f32 = np.float32(input_nparray)
        scipy.io.wavfile.write(intended_name,fs,input_f32)

    pass


def select_channels(channel_list,multichannel_rec):
    '''
    selects only those channels which are in the channel list
    '''
    if not check_allare_int(channel_list):
        raise ValueError('channel list entries can only be integers!!')

    subset_channels = multichannel_rec[:,channel_list]

    return(subset_channels)

def estimate_delay(chB,chA,samples_to_use=10**5):
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


def cut_out_same_sections(channel,start_index,stop_index):
    '''
    Inputs:
        channel: array-like. one channel recording
        start_index,stop_index: integers.
    Outputs:
        trimmed_channel: array-like. output channel recording cut-out according to start and stop indices
    '''

    cut_points = (start_index,stop_index)

    if not all([ each<0for each in cut_points]):
        raise ValueError('The start and stop indices need to be >0')
    if not stop_index>start_index:
        raise ValueError('The stop index must be greater than the start index')


    trimmed_channel = channel[start_index:stop_index]


    return(trimmed_channel)


def detect_first_rising_edge(recording,fs=192000,**kwargs):
    '''
    Convolves the recording with an input template signal
    . The first peak arising from this convolved signal is output.

    When no template is given, a square wave signal
    with 50% duty cycle and 25 Hz frequency is assumed.

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
        print('fps argument found in kwargs, using '+str(kwargs['fps'])+' Hz fps')
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


def align_channels(multichannel_rec, channel2device,cut_points={'ADC1':0,'ADC2':0}):
    '''
    Cuts out the same portion of recording to compensate for AD conversion.

    Inputs:
        multichannel_rec : nsamples x Nchannels np,array. contains the multichannel recording from both devices

        channel2device: dictionary. Maps which channels belong to which device. Each entry has a
                         array like object with the channel indices in it.

        cut_points: dictionary. The sample index of the sync signals first rising edge. Defaults to zero delay across
                                channels of both AD converters. This is index from which the 'cut' will be made to
                                create a time-aligned recording across all ADC devices
    Outputs:
        rec_timealigned: n_alignedsamples x Nchannels np.array. The time-aligned
                             multi-channel recording

    '''

    commonstart_ch = {}
    #cut out the inequal multichannel snippets from the common sample onwards
    for each_device,cutpoint in cut_points.items():
        commonstart_ch[each_device] = multichannel_rec[cutpoint:,channel2device[each_device]]


    # now look at which rising edge occurs the latest, which device has the lowest samples recorded :
    numsamples = []
    for each_device,common_ch in commonstart_ch.items():
        numsamples.append(common_ch.shape[0])

    lowest_samples = min(numsamples)

    # and now make all the channels of the same size + column stack:
    nchannels = multichannel_rec.shape[1]
    rec_timealigned = np.zeros((lowest_samples,nchannels))

    for each_device,common_ch in commonstart_ch.items():

        device_channels = channel2device[each_device]
        rec_timealigned[:,device_channels] = common_ch[:lowest_samples,:]


    return(rec_timealigned)

def save_as_singlewav_timestamped(multichannel_rec, fs, file_start='Mic',**kwargs):
    '''
    receives an nsample x Nchannel array and saves all of them with the
    a progressive set of names

    The Default is to save each channel as single WAV files with the following
    pattern:

    MicNN_YYYY-MM-DD_HH-mm-SS_NNNNNNN.WAV (TOADSUITE FORMAT)

    Inputs:

    multichannel_rec : nsamples x Nchannels numpy array.
    file_start : string. the common string at the beginning of all channels.
                Defaults to 'Mic'

    **kwargs:
    file_timestamp : string. the common timestamp to be appended to all separate wav files.
                    Defaults to the current time stamp with the

    '''

    if not 'file_timestamp' in kwargs.keys():
        time_stamp = datetime.datetime.now()
        fmtd_timestamp = time_stamp.strftime('%Y-%m-%d_%H-%M-%S')
        unix_timestamp = int(time.mktime(time_stamp.timetuple()))
        saved_timestamp = str(fmtd_timestamp)+'_'+str(unix_timestamp)
    else:
        saved_timestamp = kwargs['file_timestamp']

    if  ('.WAV' in saved_timestamp) or ('.wav' in saved_timestamp):
        end_format = ''
    else:
        end_format = '.WAV'


    for each_column in range(multichannel_rec.shape[1]):
        filename_start = file_start
        mic_index = '%0.02d'%each_column
        filename_end = saved_timestamp
        saved_filename = filename_start+ mic_index +'_'+ filename_end + end_format

        write_wavfile(multichannel_rec[:,each_column],fs,saved_filename)

    pass


def check_for_overlaps(channels2something):
    '''
    checks if there are overlaps/double entries of channels between the values
    given across devices and raises an Error if there are any.

    If there are no overlaps - returns False - to indicate NO overlaps
    '''

    try:
        all_channels = [ channels  for each_device,channels in channels2something.items()]

        if check_allare_int(all_channels):
            all_channelsset = [  set([each_channel]) for each_channel in all_channels  ]
        else:
            all_channelsset = [set(every_channel) for every_channel in all_channels]

    except:

        raise TypeError('Unable to make a set out of the channels2device dictionary, please check the input channels')

    all_combins = list(itertools.combinations( range(len(all_channelsset)),2))

    for pair in all_combins:
        device1 = pair[0]
        device2 = pair[1]
        common_channels  = all_channelsset[device1].intersection( all_channelsset[device2])

        if len(common_channels) >0:
            raise ValueError('Some channels may have been specified twice across different devices!')

    return(False)


check_allare_int = lambda some_list: all(isinstance(item, int) for item in some_list)
# thanks Dragan Chupacabric : https://stackoverflow.com/questions/6009589/how-to-test-if-every-item-in-a-list-of-type-int
check_allare_np = lambda some_list: all(isinstance(item, np.ndarray) for item in some_list)

if __name__ == '__main__':
    os.chdir('C:\\Users\\tbeleyur\\Desktop\\test\\')
    fs,rec = read_wavfile('MULTIWAV_2017-11-28_15-42-03_1511880123.WAV')
    ch2dev = {'1':range(8),'2':range(8,16)}
    sync2dev = {'1':7,'2':15}
    rec_taligned = timealign_channels(rec,fs=192000,channels2devices=ch2dev,syncch2device=sync2dev)

    save_as_singlewav_timestamped(rec_taligned,fs,file_start='Mic',file_timestamp='2017-11-28_15-42-03_1511880123.WAV')

