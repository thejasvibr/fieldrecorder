# -*- coding: utf-8 -*-
"""
Created on 2018-02-06

@author: tbeleyur
"""
import glob
import easygui as eg
import numpy as np
import pandas as pd
import scipy.io.wavfile as WAV


folder = str(eg.diropenbox())

files_in_folder = glob.glob(folder+'\\'+'*.WAV')

cols = ['file_name', 'expected_numframes', 'rec_durn',
                     'bat_presence', 'notes', 'video_file']
file_data = pd.DataFrame(index = range(len(files_in_folder)),
                         columns = cols)

for row_num, each_wav in enumerate(files_in_folder):
    fs, rec = WAV.read(each_wav)

    print(each_wav,'\n', rec.shape,'\n Duration: ',rec.shape[0]/float(fs),
          '\n Num exp frames',25*rec.shape[0]/float(fs))
    
    file_data['file_name'][row_num] = each_wav
    file_data['expected_numframes'][row_num] = int(25*rec.shape[0]/float(fs))
    file_data['rec_durn'][row_num] = rec.shape[0]/float(fs)
    
file_data.to_csv(folder+'\\wav_information.csv')
    
    