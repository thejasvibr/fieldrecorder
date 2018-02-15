# -*- coding: utf-8 -*-
"""
Created on Fri Dec 15 14:53:59 2017

@author: tbeleyur
"""
import glob
import numpy as np
import peakutils as pk
import scipy.io.wavfile as WAV
import matplotlib.pyplot as plt
plt.rcParams['agg.path.chunksize'] = 100000

folder = 'C://Users//tbeleyur//Desktop//test//'

files_in_folder = glob.glob(folder+'*.WAV')

for each_wav in files_in_folder:
    fs, rec = WAV.read(each_wav)

    normaliseint16 = lambda X : X/(2**15-1.0)

    sync_ch = normaliseint16(rec[:,7])

    pks = pk.indexes(sync_ch,thres=0.8,min_dist =7000)
    print(each_wav, pks.size)