import sys 
import os 
import os.path as osp 
import numpy as np 
import json 
from sklearn.cluster import DBSCAN
import tqdm
import matplotlib.pyplot as plt 
from scipy.spatial import distance
from copy import deepcopy
from cylinder_cluster import cylinder_cluster


# This class to large extend is a copy of instance_seq.py file
class PostProcessor(object):
    
    def cluster_objects(self):
        """
            This function performs objects clustering basaed on individually classified target points            
        """
        