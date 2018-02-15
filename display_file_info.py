# -*- coding: utf-8 -*-
"""
Created on 2018-02-06

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

    print(each_wav,'\n', rec.shape,'\n Duration: ',rec.shape[0]/float(fs),
          '\n Num exp frames',25*rec.shape[0]/float(fs))