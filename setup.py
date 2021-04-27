from setuptools import setup, find_packages
import fieldrecorder

 # link to test upload and fresh install on Test PyPi https://packaging.python.org/guides/using-testpypi/
 
version_number = fieldrecorder.__version__

setup(name='fieldrecorder',
     version=version_number,
     description='Identify, Track and Segment sounds by Frequency and its Modulation',
     long_description=open('README.md').read(),
     long_description_content_type="text/markdown",
     url='https://github.com/thejasvibr/fieldrecorder',
     author='Thejasvi Beleyur',
     author_email='thejasvib@gmail.com',
     license='MIT',
     packages=find_packages(),
     install_requires=['numpy','python-dateutil','soundfile',
        'scipy','matplotlib', 'sounddevice'],
     zip_safe=False,
	 include_package_data=True,
     classifiers=[
        'Intended Audience :: Science/Research',
        'Topic :: Multimedia :: Sound/Audio :: Analysis',
        'Topic :: Multimedia :: Sound/Audio',
		'Programming Language :: Python :: 2.7',
		'Programming Language :: Python :: 3'
		])