# -*- coding: utf-8 -*-
"""Testing how the Stream works in Sounddevice
Created on Wed Dec 06 16:16:46 2017

@author: tbeleyur
"""
import sounddevice as sd
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
plt.rcParams['agg.path.chunksize'] = 10000

dev_id = 42
inout_ch = [24,3]
fs = 192000


sync_freq = 25
one_cycledurn = 1.0/sync_freq
full_durn = 15
num_cycles = np.around(full_durn/one_cycledurn)
sig_durn = num_cycles*one_cycledurn
t = np.linspace(0,sig_durn,int(fs*sig_durn))
sine_fn = 2*np.pi*sync_freq*t + np.pi

sync_signal = np.float32( signal.square(sine_fn,0.5) )
sync_signal *= 0.25


# play the trigger for 1 second
trigger_freq = 20*10**3
trig_signal = np.sin(sine_fn[:fs])
noise_signal = np.random.normal(0,0.1,trig_signal.size)

pbk_data = np.zeros((sync_signal.shape[0],3))
pbk_data[:,0] += sync_signal.flatten()
pbk_data[9*fs:10*fs,1] = trig_signal
pbk_data[9*fs:10*fs,2] = noise_signal.flatten()

test_rec = sd.playrec(pbk_data,channels=8,device=56,blocking=True,samplerate=fs)
plt.plot(test_rec[:,0])

cc =  np.correlate(test_rec[9*fs:10*fs,7],pbk_data[9*fs:10*fs,2],'same')