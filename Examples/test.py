# -*- coding: utf8 -*-
#
#  CyKIT  2020.06.05
#  ________________________
#  example_epoc_plus.py       
#  
#  Written by Warren
#
"""
   
  usage:  python.exe .\example_epoc_plus.py
  
  ( May need to adjust the key below, based on whether 
    device is in 14-bit mode or 16-bit mode. )
  
"""

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy import stats

import numpy as np
import time

import os
import sys
print(str(sys.path))
sys.path.insert(0, '..//py3//cyUSB//')
sys.path.insert(0, '..//py3')

import cyPyWinUSB as hid
import queue
from cyCrypto.Cipher import AES
from cyCrypto import Random
import requests

tasks = queue.Queue()

class EEG(object):
    
    def __init__(self):
        self.hid = None
        self.delimiter = ", "
        
        devicesUsed = 0
    
        for device in hid.find_all_hid_devices():
                if device.product_name == 'EEG Signals':
                    devicesUsed += 1
                    self.hid = device
                    self.hid.open()
                    self.serial_number = device.serial_number
                    device.set_raw_data_handler(self.dataHandler)                   
        if devicesUsed == 0:
            os._exit(0)
        sn = self.serial_number
        
        # EPOC+ in 16-bit Mode.
        k = ['\0'] * 16
        k = [sn[-1],sn[-2],sn[-2],sn[-3],sn[-3],sn[-3],sn[-2],sn[-4],sn[-1],sn[-4],sn[-2],sn[-2],sn[-4],sn[-4],sn[-2],sn[-1]]
        
        # EPOC+ in 14-bit Mode.
        #k = [sn[-1],00,sn[-2],21,sn[-3],00,sn[-4],12,sn[-3],00,sn[-2],68,sn[-1],00,sn[-2],88]
        
        self.key = str(''.join(k))
        self.cipher = AES.new(self.key.encode("utf8"), AES.MODE_ECB)

    def dataHandler(self, data):
        join_data = ''.join(map(chr, data[1:]))
        data = self.cipher.decrypt(bytes(join_data,'latin-1')[0:32])
        if str(data[1]) == "32": # No Gyro Data.
            return
        tasks.put(data)

    def convertEPOC_PLUS(self, value_1, value_2):
        edk_value = "%.8f" % (((int(value_1) * .128205128205129) + 4201.02564096001) + ((int(value_2) -128) * 32.82051289))
        return edk_value

    def get_data(self):
       
        data = tasks.get()
        #print(str(data[0])) COUNTER


        try:
            packet_data = ""
            for i in range(2,16,2):
                packet_data = packet_data + str(self.convertEPOC_PLUS(str(data[i]), str(data[i+1]))) + self.delimiter

            for i in range(18,len(data),2):
                packet_data = packet_data + str(self.convertEPOC_PLUS(str(data[i]), str(data[i+1]))) + self.delimiter

            packet_data = packet_data[:-len(self.delimiter)]
            return str(packet_data)

        except Exception as exception2:
            print(str(exception2))

def post(value):
    url = 'https://2a16-79-173-189-36.ngrok-free.app/post-response'
    data = {'response': f'{value}'}
    response = requests.post(url, json=data)
    if response.status_code == 200:

        print("Data sent successfully!")

    else:
        print("Error:", response.status_code)

    return None




cyHeadset = EEG()


start_time = time.time()
i=0
data_total=np.empty((0,14))


plt.ion()

o=0

responses = []

test_gamma=np.array([])
while True:
    while tasks.empty():
        pass

    data = cyHeadset.get_data()
    data_list = [float(x) for x in data.split(',')]
    data_array = np.array(data_list)

    data_total=np.vstack([data_total,data_array])
    X = np.array([])
    y = np.array([])
    
    if len(data_total[:,0])>=256 and len(data_total[:,0])%64==0:
        #print(o)
        #print(data_total[o*64:(o*64)+256,1])
        fft = np.fft.fft(data_total[o*64:o*64+256,2])
        freqs = np.fft.fftfreq(len(fft))*256
        #fft = np.fft.fft(data_total[i:i+256,1])
        power = np.log(np.abs(fft)**2)
        

        if o%80 not in range(60,80,1):
            power=np.append(power,0)
        else:
            power=np.append(power,1)


        o+=1
        #print(power[-1])
        X= np.append(X,power[0:-1])
        y= np.append(y,power[-1])
        freq_gamma=freqs[20:50]
        power_gamma=power[20:50]
        test_gamma=np.append(test_gamma,power_gamma)

        if np.mean(power_gamma)>13:
            print('yes')
            if len(responses) <= 20:
                responses.append('yes')
            else:
                majority = stats.mode(responses)
                post(majority)
                responses = []
        else:
            print('no')
            if len(responses) <= 20:
                responses.append('no')
            else:
                majority = stats.mode(responses)
                post(majority)
                responses = []
            # post('no')
        plt.plot(freq_gamma,power_gamma)
        plt.ylim(-5,20)
        plt.draw()
        plt.pause(0.0001)
        plt.clf()



        #line1.set_xdata(np.linspace(0,1,len(power)))
        #line1.set_ydata(power)
        #ax.relim()
        #ax.autoscale_view()
        #fig.canvas.draw()
        #fig.canvas.flush_events()

    #if time.time() - start_time >= 20:
    #    break

print(test_gamma)
print(f'testgamma mean = {np.mean(test_gamma)}')
#np.save(X, X)
#np.save(y, y)
#plt.ioff()
#plt.show()

# Create an animation

#ani = FuncAnimation(fig, update, frames=None, blit=True, interval=1)

#plt.show()

#data = cyHeadset.get_data()








