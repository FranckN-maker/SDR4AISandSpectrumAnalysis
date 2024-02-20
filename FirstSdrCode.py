from matplotlib import pyplot as plt
import matplotlib.animation as animation
from rtlsdr import RtlSdr
import numpy as np
import scipy
from matplotlib.patches import Rectangle
import signal

sdr = RtlSdr()
# configure device
foffset = 100e3 #250000 # 250 kHz
fo = 162.0e6
Fc = fo + foffset
FsampleRate = int(3.2e6)
sdr.sample_rate = FsampleRate  # Hz
sdr.center_freq = Fc # Hz
sdr.freq_correction = 140   # PPM
sdr.gain = 'auto'



fig, graph_out = plt.subplots(2,1)
# graph_out = fig.add_subplots(2, 1)

TFAC1 = np.zeros(24)
TFAC2 = np.zeros(24)
TFAC1[0:10] = 1 
TFAC2[14::] = 1
A = sum(TFAC1)
B = sum(TFAC2)
DetectRemain = np.zeros(1024)
BoolDetect = np.zeros(1024)
f_bw = 10000



def animate(i):
    global DetectRemain
    graph_out[0].clear()
    graph_out[1].clear()
    #samples = sdr.read_samples(1024*1024)
    samples = sdr.read_samples(128*1024)
    x1 = np.array(samples).astype("complex64")
    fc1 = np.exp(-1.0j * 2.0 * np.pi * (foffset)/FsampleRate*np.arange(len(samples)))
    x2 = x1 * fc1
   
    # # use matplotlib to estimate and plot the PSD
    SpectPSD, Freq  = graph_out[0].psd(x2, NFFT=1024, Fs=sdr.sample_rate /
                  1e6, Fc=sdr.center_freq/1e6)
    SpectPSDdB = 10*np.log10(SpectPSD)
  
    Detect1 = (scipy.signal.fftconvolve(SpectPSDdB, TFAC1, mode = 'same', axes = None))
    Detect2 = (scipy.signal.fftconvolve(SpectPSDdB, TFAC2, mode = 'same', axes = None))
    Detect = (np.minimum(Detect1, Detect2))
    # graph_out.psd(samples, NFFT=1024, Fs=sdr.sample_rate /
    #               1e6, Fc=sdr.center_freq/1e6)
    
    # graph_out.plot(Freq, SpectPSDdB)
    graph_out[0].plot(Freq, Detect/A + 3)
    Detections = np.full_like(SpectPSD, np.nan)
    FreqDetect = np.full_like(Freq, np.nan)
    Detections = (np.where(SpectPSD > (Detect/A + 3), SpectPSD, np.nan ))
    # # Bool =np.isfinite(Detections)
    
    graph_out[0].plot(Freq, Detect/A + 3) 
    graph_out[0].plot(Freq[SpectPSDdB> (Detect/A + 3)], 
                   SpectPSDdB[SpectPSDdB > (Detect/A + 3)], 'r+')  
    graph_out[0].set_xlabel('Frequency (MHz)', fontsize=20)
    graph_out[0].set_ylabel('Relative power (dB)' , fontsize=20)
    # DetectRemain = SpectPSDdB > (Detect/A + 3)
    DetectRemain = np.logical_or(DetectRemain, (SpectPSDdB > (Detect/A + 3)))
    #add rectangle to plot
    graph_out[0].add_patch(Rectangle((161.950, -20), 0.1, 10, alpha = 0.3, label="AIS Band"))
    graph_out[0].axvline(x=162.025, ymin=-41, ymax=3, color = 'red', label="AIS1")
    graph_out[0].axvline(x=161.975, ymin=-41, ymax=3, color = 'red', label="AIS2")
    graph_out[0].legend(loc="upper left")
    

    # graph_out[0].axvline(x=156.480, ymin=-50, ymax=40, color = 'black', label="Navire-Navire")
    # graph_out[0].axvline(x=156.625, ymin=-50, ymax=40, color = 'black', label="Navire-Navire")
    # graph_out[0].axvline(x=156.875, ymin=-50, ymax=40, color = 'black', label="Navire-Navire")
    # graph_out[0].axvline(x=156.800, ymin=-50, ymax=40, color = 'blue', label="Securité")
    # graph_out[0].axvline(x=156.525, ymin=-50, ymax=40, color = 'blue', label="Securité")
    


    # Time = np.arange(len(x1)) *  1/FsampleRate  

    graph_out[1].plot(Freq, DetectRemain)
    graph_out[1].set_xlabel('Frequency (MHz)', fontsize=20)
    graph_out[1].set_ylabel('Detections (Boolean)' , fontsize=20)
    graph_out[1].grid()


    del Detections,

try:
    ani = animation.FuncAnimation(fig, animate, interval=10)
    plt.show()
except KeyboardInterrupt:
    pass
finally:
    # Set up formatting for the movie files
    Writer = animation.writers['ffmpeg']
    # writer = Writer(fps=15, metadata=dict(artist='Me'), bitrate=1800)
    # ani.save('im.mp4', writer=writer)
    sdr.close() 