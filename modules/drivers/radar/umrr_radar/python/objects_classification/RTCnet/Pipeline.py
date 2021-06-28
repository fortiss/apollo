import sys 
import os 
import os.path as osp 

import numpy as np 
import matplotlib.pyplot as plt 

import torch
import torch.nn as nn 
import tqdm

# This class executes ensemble of networks (similarly as the test class) and then it runs the post processing
class Executor(object):
    
    def execute_chain(self, frame):
        """
            Args:
            
            frame - single frame of data, i.e. targets
        """
        
        # Execute ensamble - look into test_RTC_ensemble, starting from main function
        
        # Run the post processing, i.e. objects clustering