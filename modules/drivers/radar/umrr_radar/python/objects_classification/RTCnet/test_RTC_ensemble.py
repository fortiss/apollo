# Python Libraries
import os 
import sys 
import os.path as osp 
import argparse

# Pytorch
import torch 
from torchvision import transforms
from torch.utils.data import DataLoader
import torch.nn as nn 

# Third-party libraries
import numpy as np 
import json
import tqdm

from RTCnet_utils import RTCRunner
from RTCnet_utils import Clustifier

from TargetLoader import TargetModeDataset, ToTensor

def main():
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    result_DIR = osp.join(BASE_DIR, osp.pardir, 'results', 'RTCtrain_info')
    config_list = os.listdir(result_DIR)
    config_list.sort()
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-config", default = osp.join(result_DIR, config_list[-1]), type = str, help=" The default configuration file is the first configuration file in results folder")
    parser.add_argument("-test", default = None, type = str)
    parser.add_argument("-batch_size", type=int, default = 1024, help = "The version of networks. 1: RTC 2: RTC2 3: Multi-layer perceptron for only high-level" ) 
    args = parser.parse_args()
    
    cfg_path        = args.config
    test_data_path  = args.test
    
    with open(cfg_path) as fp:
        cfg = json.load(fp)
    data_path       = cfg["data_path"]
    result_folder   = cfg['result_folder']
    speed_limit     = cfg["speed_limit"]
    dist_near       = cfg["dist_limit"]
    binary_class    = cfg['binary']
    rm_cars         = cfg["rm_cars"]
    dist_far        = cfg["data_x_limit"]
    
    if "rm_position" in cfg:
        rm_position = cfg['rm_position']
    else:
        rm_position = False
    if "rm_speed" in cfg:
        rm_speed = cfg["rm_speed"]
    else:
        rm_speed = False
    if "rm_rcs" in cfg:
        rm_rcs = cfg["rm_rcs"]
    else:
        rm_rcs = False
    if rm_position:
        high_dims = 2
        dist_far = 100
    else:
        high_dims = 4
    if test_data_path is None:
        test_data_path = data_path
    
    feature_type = "high"
    only_slow = False
    only_fast = False
    
    batch_size = args.batch_size
    
    ################### transforms ###################
    to_tensor = ToTensor()
    composed_trans = transforms.Compose([to_tensor])

    test_data = TargetModeDataset(
                test_data_path, composed_trans, 
                mode='test', high_dims=high_dims, 
                normalize=True, feature_type= feature_type,
                norms_path=result_folder,
                speed_limit=speed_limit,
                dist_near=dist_near,
                binary_class=binary_class,
                dist_far=dist_far,
                rm_cars=rm_cars,
                rm_position=rm_position,
                zero_low=False,
                only_slow=only_slow,
                only_fast=only_fast,
                rm_speed=rm_speed,
                rm_rcs=rm_rcs)
    data_loader = DataLoader(test_data, batch_size=batch_size, shuffle=False, num_workers=1)
    np.save(osp.join(result_folder, "valid_indx_test"), test_data.indx_valid)
    
    pred_labels_all = []
    final_scores_all = []
    
    runner = RTCRunner()
    clustifier = Clustifier()
    
    # data for testing is loaded batch by bach - where batch_size is specified
    # we could load all targets (without dividing them on batches) and run ensemble on them, but this would be less efficient
    with tqdm.tqdm(total=len(data_loader), leave=False, desc='test') as pbar:
        for batch in data_loader:
            pbar.update()
            data_frame = batch
            pred_labels, final_scores = runner.execute_ensemble(data_frame)
            pred_labels_all.extend(pred_labels)
            final_scores_all.extend(final_scores)
            print('\n\n################# Predicted Labels ################')
            print('Length: ' + str(len(pred_labels)))
            print(pred_labels)
           

    # calling clustering on all predicted labels
    # for this testing we are assuming that all the labels that are fed to the clusting alg. are coming from the same frame 
    # Grouping into different frames is done within clustering algorithm
    # For the car, each time we get pointcloud they are from the same frame
    pred_labels_all = np.array(pred_labels_all)
    final_scores_all = np.array(final_scores_all)
    
    # creating array representing frames ids. To make it the easiest we assume that all frames all 0, i.e. all the targets come from the
    # same frame of id 0.
    frame_id = np.array([0] * len(pred_labels_all))
    clustered_pred_labels, instance_id_pred = clustifier.cluster_labels(data_loader.dataset.features, frame_id, pred_labels_all, final_scores_all)
    
    print('\n\n############# ALL Clustered Predicted Labels ################')
    print('Length: ' + str(len(clustered_pred_labels)))

    # instance_id_pred is an array that provides information about elements that are merged together (they will have the same id)
    '''Examples
    --------
    >>> from sklearn.cluster import DBSCAN
    >>> import numpy as np
    >>> X = np.array([[1, 2], [2, 2], [2, 3],
    ...               [8, 7], [8, 8], [25, 80]])
    >>> clustering = DBSCAN(eps=3, min_samples=2).fit(X)
    >>> clustering.labels_
    array([ 0,  0,  0,  1,  1, -1])
    >>> clustering
    DBSCAN(eps=3, min_samples=2)

    See also
    --------
    '''

    print(instance_id_pred)
    
    
if __name__ == "__main__":
    main()