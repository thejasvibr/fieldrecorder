# fieldrecorder
### A set of modules that allow for dongle-free recording and playback triggered by keyboard presses or automatic threshold based triggering.

## The recording setup : 
### *fieldrecorder* relies on the [sounddevice library](https://python-sounddevice.readthedocs.io/en/0.3.7/#) to interface with ASIO based soundcards and perform simultaneous playbacks and recordings. 
### *fieldrecorder* was specifically designed to collect time synchronised audio-video data with a three camera and 12 microphone recording system used to record audio-video data on bat echolocation in the field. The cameras (TeAx ThermalCapture 25Hz) continuously receive a 25 Hz square wave signal to keep the video stream going, and are triggered to record through a 20kHz sinusoid wave that is additionally sent on a separate channel based on user triggering or automated threshold crossing. 

## Multichannel + multidevice recording capabilities and challenges:
In its current default form the module records data from 24 audio channels from two ASIO based soundcards (Fireface UC). In our case the two soundcards do not show a complete synchronicity in AD conversion. To overcome this there is a third channel that outputs a copy of the 25 Hz square wave onto both devices. Thus two of the 24 channels are required to time-match the audio channels later. In house tests have shown that this time-matching procedure is sufficiently accurate for our sound source localisation purposes. 

## The Modules:
*fieldrecorder* : this module when run requires the user to trigger the start and stop of the recording through keyboard key presses. Please be aware that *any* key press will activate the start/stop of the recording, irrespective of whether the python commandline/ Spyder window is minimised or not. 

*fieldrecorder_trigger* : this module allows the user to pre-define a threshold in dB rms for a set of 'monitor channels'. The dB rms of the audio data across the 'monitor channels' are calculated for each arriving buffer. If the dB rms crosses the threshold in any one of the 'monitor channels' recording is triggered for a fixed period of time (default of 10 seconds). The user can also bandpass the audio data in the monitor channels to decrease non-target sound triggering (eg. for bats an ultrasound bandpass between 20-90 kHz). 

*ADC_delay* : this module contains a set of helper functions to time-synchronise the audio channels digitised across multiple AD converters.
Included are functions to estimate delay in digitisation, cut and time-align channels and save them into individual WAV files. 

*tests_adc_delay* : basic unit tests to check if *ADC_delay* is working fine. 

## Other files:
> DEVICE1_2017-11-21-10_44_20.wav
> DEVICE1_2017-11-21-10_44_20.wav
These WAV files are required for the *tests_adc_delay* to work. Do not download these files if you're not interested in running the tests yourself. 

## The fieldrecorder set of modules were written and tested with Python 2.7.12 and sounddevice 0.3.5




