import sys
import os
import os.path as osp

import numpy as np
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
import tqdm

import argparse

import json

from .cylinder_cluster import cylinder_cluster

from .RTCnet import RTCnet

from scipy.spatial import distance


class RTCRunner(object):

    def __init__(self):
        
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        result_DIR = osp.join(BASE_DIR, osp.pardir, 'results', 'RTCtrain_info')
        config_list = os.listdir(result_DIR)
        config_list.sort()
        
        parser = argparse.ArgumentParser()
        parser.add_argument("-config", default = osp.join(result_DIR, config_list[-1]), type = str, help=" The default configuration file is the first configuration file in results folder")
        parser.add_argument("-test", default = None, type = str)
        parser.add_argument("-batch_size", type=int, default = 1024, help = "The version of networks. 1: RTC 2: RTC2 3: Multi-layer perceptron for only high-level" ) 
        parser.add_argument("-node_config", type=str) 
        
        print(parser.parse_args())
        
        args = parser.parse_args()
        
        cfg_path        = args.config
        test_data_path  = args.test

        with open(cfg_path) as fp:
            cfg = json.load(fp)
        data_path       = cfg["data_path"]
        self.use_gpu         = cfg['use_gpu']
        result_folder   = cfg['result_folder']
        weights_all     = cfg['weights']
        use_set         = ["train", "val", "test"]
        weights_factor  = cfg["weights_factor"]
        dropout         = cfg['dropout']
        weights_factor  = np.array(weights_factor)
        weights_all     = np.array(weights_all)
        binary_class    = cfg['binary']
        input_size      = cfg['input_size']
        rm_cars         = cfg["rm_cars"]
        speed_limit     = cfg["speed_limit"]
        dist_near       = cfg["dist_limit"]
        dist_far        = cfg["data_x_limit"]

        weights_all = np.multiply(weights_factor, weights_all)

        self.models = []

        ################### Ped VS ALL ###########
        self.models.append(self.load_model(result_folder, dropout, input_size, weights_all, is_ova=True, class_positive=1, class_negative=-1, use_gpu=True))
        
        ################### Biker VS ALL ###########
        self.models.append(self.load_model(result_folder, dropout, input_size, weights_all, is_ova=True, class_positive=2, class_negative=-1, use_gpu=True))
        
        ################### Car VS ALL ###########
        self.models.append(self.load_model(result_folder, dropout, input_size, weights_all, is_ova=True, class_positive=3, class_negative=-1, use_gpu=True))
        
        ################### Others VS ALL ###########
        self.models.append(self.load_model(result_folder, dropout, input_size, weights_all, is_ova=True, class_positive=0, class_negative=-1, use_gpu=True))
        
        ################### Ped VS Biker ###########
        self.models.append(self.load_model(result_folder, dropout, input_size, weights_all, is_ova=False, class_positive=1, class_negative=2, use_gpu=True))
        
        ################### Ped VS Car ###########
        self.models.append(self.load_model(result_folder, dropout, input_size, weights_all, is_ova=False, class_positive=1, class_negative=3, use_gpu=True))
        
        ################### Biker VS Car ###########
        self.models.append(self.load_model(result_folder, dropout, input_size, weights_all, is_ova=False, class_positive=2, class_negative=3, use_gpu=True))
        
        ################### Others VS Ped ###########
        self.models.append(self.load_model(result_folder, dropout, input_size, weights_all, is_ova=False, class_positive=0, class_negative=1, use_gpu=True))
        
        ################### Others VS Biker ###########
        self.models.append(self.load_model(result_folder, dropout, input_size, weights_all, is_ova=False, class_positive=0, class_negative=2, use_gpu=True))
        
        ################### Others VS Car ###########
        self.models.append(self.load_model(result_folder, dropout, input_size, weights_all, is_ova=False, class_positive=0, class_negative=3, use_gpu=True))
        

    def load_model(self, result_folder, dropout, input_size, weights_all, is_ova, class_positive, class_negative, use_gpu):

        model = RTCnet(
            num_classes=2,
            Doppler_dims=32,
            high_dims=4,
            dropout=dropout,
            input_size=input_size)

        class_list = ['others', 'ped', 'biker', 'car']
        
        if True == is_ova:
            append_str = "{}_vs_All".format(class_list[class_positive])
            weights = torch.tensor(np.array([np.sum(weights_all) - weights_all[1], weights_all[1]])) if not use_gpu else \
                torch.tensor(np.array([np.sum(weights_all) - weights_all[1], weights_all[1]])).cuda()
        else:
            append_str = "{}_vs_{}".format(class_list[class_positive], class_list[class_negative])
            weights = torch.tensor(np.array([weights_all[class_negative], weights_all[class_positive]]))
            if use_gpu:
                weights = weights.cuda()
            
        self.loss_func = nn.CrossEntropyLoss(weight = weights)

        model_path = osp.join(result_folder, 'best_checkerpoint_{}.pth'.format(append_str))
        model.load_state_dict(torch.load(model_path))
        model.eval()
        
        if True == use_gpu:
            model.cuda()
        
        model.double()

        return model
    
    
    def execute_ensemble(self, frame):
        scores_all = []
        for idx in range(len(self.models)):
            scores = self.run_for_single_model(frame, idx).cpu().numpy()
            scores_all.append(scores)
        
        
        final_score1 = np.reshape(scores_all[4] * (scores_all[0] + scores_all[1]) \
                    + scores_all[5] * (scores_all[0] + scores_all[2]) \
                    + (1 - scores_all[7]) * (scores_all[0] + scores_all[3]), (-1, 1))
        final_score2 = np.reshape(( 1 - scores_all[4]) * (scores_all[1] + scores_all[0])\
                        + scores_all[6] * (scores_all[1] + scores_all[2])\
                        + (1 - scores_all[8]) * (scores_all[1] + scores_all[3]), (-1, 1))
        final_score3 = np.reshape((1 - scores_all[5]) * (scores_all[2] + scores_all[0])\
                        + (1-scores_all[6]) * (scores_all[2] + scores_all[1])\
                        + (1-scores_all[9]) * (scores_all[2] + scores_all[3]), (-1, 1))
        final_score0 = np.reshape(scores_all[7] * (scores_all[3] + scores_all[0])\
                        + scores_all[8] * (scores_all[3] + scores_all[1])\
                        + scores_all[9] * (scores_all[3] + scores_all[2]), (-1, 1))
        final_score = np.concatenate([final_score0, final_score1, final_score2, final_score3], axis=1)
        pred_labels_all = np.argmax(final_score, axis=1)
        
        
        return pred_labels_all, final_score

    
    def run_for_single_model(self, frame, idx):
        """  
        Single iteration for testing. Only scores not labels are returned
        """
        self.models[idx].eval()
        self.models[idx].zero_grad()
        scores = self._farward_pass(frame, idx)
        return scores
    

    def _farward_pass(self, frame, idx):
        inputs = frame['data']
        if self.use_gpu:
            inputs = inputs.cuda()
        preds = self.models[idx](inputs)
        with torch.no_grad():
            scores = nn.functional.softmax(preds,dim = 1)[:, 1]
        return scores
    


class Trainer(object):
    """
    Helper class for model training
    """

    def __init__(self,
                 model,
                 loss_func,
                 optimizer,
                 lr_scheduler=None,
                 eval_frequency=-1,
                 use_gpu=False,
                 lr_decay_step=0,
                 lr_decay_f=0.5,
                 lr_clip=1e-4,
                 save_checkerpoint_to='',
                 append_str=''):
        """
        Constructor for trainer

        Parameters
        ----------
        model: RTCnet
               The RTC model
        loss_func: torch.nn.CrossEntropyLoss
                   Loss function in torch.nn
        optimizer: torch.optim.Adam
                   Optimizer provided by Pytorch
        lr_scheduler: torch.optim.lr_scheduler.StepLR
                      Scheduler for training
        eval_frequency: int
                        How frequency the model is evaluated, -1 means evaluating the model after every epoch
        use_gpu: bool
                 Whether GPU is used
        lr_decay_step: int
                       The training step after which the learning rate is lowered
        lr_decay_f: float
                    The factor for the decay of learning rate
        lr_clip: float
                 The clip value after which the learning rate stops decaying
        save_checkerpoint_to: string
                              Path to save the trained model
        append_str: string
                    The string appeded for illustrating more details after the saved model
        """
        self.model = model
        self.loss_func = loss_func
        self.optimizer = optimizer
        self.lr_scheduler = lr_scheduler
        self.eval_frequency = eval_frequency
        self.use_gpu = use_gpu
        self.lr_decay_step = lr_decay_step
        self.lr_decay_f = lr_decay_f
        self.lr_clip = lr_clip
        self.save_checkerpoint_to = save_checkerpoint_to
        self.trace_loss = []
        self.trace_loss_train = []
        self.append_str = append_str
        if self.use_gpu:
            self.model.cuda()

    def _train_it(self, it, batch):
        """
        Single iteration for training
        """
        self.model.train()
        self.optimizer.zero_grad()
        _, loss, res_dict = self._farward_pass(self.model, batch)
        loss.backward()
        self.optimizer.step()
        return res_dict

    def _farward_pass(self, model, batch):
        """
        Forward pass for single iteration
        """
        inputs, labels = batch['data'], batch['label']
        if self.use_gpu:
            inputs = inputs.cuda()
            labels = labels.cuda()
        preds = model(inputs)
        loss = self.loss_func(preds.view(labels.numel(), -1), labels.view(-1))
        res_dict = {
            "loss": loss.item()
        }
        return preds, loss, res_dict

    def _val_epoch(self, val_loader):
        """
        One epoch for validation
        """
        self.model.eval()
        eval_dict = {}
        total_loss = 0.0
        cnt = 0
        for i, data in tqdm.tqdm(enumerate(val_loader, 0), total=len(val_loader), leave=False, desc='val'):
            with torch.no_grad():
                _, loss, res_dict = self._farward_pass(self.model, data)
                total_loss += loss.item()
            cnt += 1
        return total_loss/cnt

    def _train_epoch(self, train_loader):
        """
        One epoch for training
        """
        self.model.eval()
        eval_dict = {}
        total_loss = 0.0
        cnt = 0
        for i, data in tqdm.tqdm(enumerate(train_loader, 0), total=len(train_loader), leave=False, desc='test_by_train'):
            with torch.no_grad():
                _, loss, res_dict = self._farward_pass(self.model, data)
                total_loss += loss.item()
            cnt += 1
        return total_loss/cnt

    def _save_checkerpoint(self, is_best, path=''):
        """
        Save the trained model
        """
        if self.append_str == '':
            torch.save(self.model.state_dict(),
                       osp.join(path, "checkerpoint.pth"))
        else:
            torch.save(self.model.state_dict(), osp.join(
                path, "checkerpoint_{}.pth".format(self.append_str)))
        if is_best:
            torch.save(self.model.state_dict(), osp.join(
                path, "best_checkerpoint_{}.pth".format(self.append_str)))

    def train(self,
              n_epochs,
              train_loader,
              val_loader=None,
              best_loss=1e5,
              start_it=0):
        """
        Wrapper for training

        Parameters
        ----------
        n_epochs: int
                  Number of epochs
        train_loader: dataloader
                      The dataloader for the training dataset
        val_loader: dataloader
                    The dataloader for the validation dataset
        best_loss: fload
                   The lowest loss until now
        start_it: int
                  The index of iteration from where the training continues. This is used for resuming training from a saved model.
        """
        eval_frequency = (
            self.eval_frequency if self.eval_frequency > 0 else len(
                train_loader)
            # Default choice: evaluate the model after every single epoch
        )
        it = start_it
        if val_loader is not None:
            val_init_loss = self._val_epoch(val_loader)
            self.trace_loss.append(val_init_loss)
            train_loss = self._train_epoch(train_loader)
            self.trace_loss_train.append(train_loss)
            tqdm.tqdm.write("initial_validation_loss:{}".format(val_init_loss))
        with tqdm.trange(0, n_epochs, desc='epochs') as tbar, \
                tqdm.tqdm(total=eval_frequency, leave=False, desc='train') as pbar:
            for epoch in tbar:
                for batch in train_loader:
                    res_dict = self._train_it(it, batch)
                    it += 1
                    pbar.update()
                    pbar.set_postfix(
                        dict(total_it=it, loss="{:.2f}".format(res_dict['loss'])))
                    tbar.refresh()

                    if it % eval_frequency == 0:
                        pbar.close()
                        if val_loader is not None:
                            val_loss = self._val_epoch(val_loader)
                            self.trace_loss.append(val_loss)
                            is_best = val_loss < best_loss
                            best_loss = min(best_loss, val_loss)
                            self._save_checkerpoint(
                                is_best, path=self.save_checkerpoint_to)
                            tqdm.tqdm.write(
                                "validation loss is:{}".format(val_loss))
                        else:
                            raise "No validation data loader"
                        pbar = tqdm.tqdm(
                            total=eval_frequency, leave=False, desc='train'
                        )
                        pbar.set_postfix(
                            dict(total_it=it, loss=res_dict['loss']))
        return best_loss
    

class Clustifier(object):
    
    def cluster_labels(self, targets, frame_id, pred_labels, scores):
        
        speed_threshold = 0.3
        speed_threshold_to_change_label = 0

        labels_pred = pred_labels
        
        targets_rav = targets
        
        target_scores = scores


        targets_xyv = np.zeros(targets_rav.shape)
        targets_xyv[:,0] = targets_rav[:,0]*np.cos(targets_rav[:,1])
        targets_xyv[:,1] = targets_rav[:,0]*np.sin(targets_rav[:,1])
        targets_xyv[:,2] = targets_rav[:,2]
        targets_v = np.abs(targets_rav[:, 2])
        labels_pred[targets_v < speed_threshold_to_change_label] = 0
        labels_pred = labels_pred[targets_v > speed_threshold]
        
        target_scores = target_scores[targets_v > speed_threshold]
        frame_id = frame_id[targets_v > speed_threshold]
        targets_rav = targets_rav[targets_v>speed_threshold, :]
        targets_xyv = targets_xyv[targets_v > speed_threshold, :]
        
        instance_id_pred, labels_pred = self.post_clustering(targets_xyv, labels_pred, frame_id, target_scores = target_scores)
        
        return labels_pred, instance_id_pred
         
    
    def cal_precision_recall_single(self, labels_true, labels_pred, instance_id_true, instance_id_pred, class_label=0, targets_for_debug=None):

        """
        Parameters
        ------------- 
        This function deals with single frame precision and recall calculation
        labels_true: 1-d array
            The true label of the targets of one single frame
        labels_pred: 1-d array
            The predicted label of the targets of one single frame
        instance_id_true: 1-d array
            The instance ID of the targets of one single frame from SSD bounding box
        instance_id_pred: 1-d array
            The instance ID of the post-clustering output
        class_label: an int
            The label of the class to calculation. 0 for background, 1 for pedestrian, 2 for cyclist, 3 for car
        
        Returns
        ------------
        num_TP: an int
            The number of true positives of the class_label
        """

        num_TP_in_pred = 0
        num_TP_in_true = 0
        num_instances_pred = 0
        num_instances_true = 0
        mask_class_label_pred = labels_pred == class_label
        mask_class_label_true = labels_true == class_label
        num_instances_pred = np.unique(instance_id_pred[labels_pred==class_label]).shape[0]
        num_instances_true = np.unique(instance_id_true[labels_true==class_label]).shape[0]
        intersection_sum = 0
        union_sum = 0

        if instance_id_pred.shape[0] >0:
            instance_id_pred_max = instance_id_pred.max()
        else:
            instance_id_pred_max = 0
        if instance_id_true.shape[0] >0:
            instance_id_true_max = instance_id_true.max()
        else:
            instance_id_true_max = 0

        intersection_sum = np.sum(np.logical_and(mask_class_label_pred, mask_class_label_true))
        union_sum = np.sum(np.logical_or(mask_class_label_pred, mask_class_label_true))
        num_TP_single_target = 0
        # calculate num_TP_in_pred (for precision)
        for i in np.arange(instance_id_pred_max + 1):
            indx_pred = np.logical_and(instance_id_pred == i, mask_class_label_pred)
            for j in np.arange(instance_id_true_max + 1):
                indx_true = np.logical_and(instance_id_true == j, mask_class_label_true)
                intersection = np.sum(np.logical_and(indx_pred, indx_true))
                union = np.sum(np.logical_or(indx_pred, indx_true))
                if intersection/union >= 0.5:
                    num_TP_in_pred += 1
                    break

        # calculate num_TP_in_true (for recall)
        for i in np.arange(instance_id_true_max + 1):
            indx_true = np.logical_and(instance_id_true == i, mask_class_label_true)
            for j in np.arange(instance_id_pred_max + 1):
                indx_pred = np.logical_and(instance_id_pred == j, mask_class_label_pred)
                intersection = np.sum(np.logical_and(indx_pred, indx_true))
                union = np.sum(np.logical_or(indx_pred, indx_true))
                num_true = np.sum(indx_true)
                num_pred = np.sum(indx_pred)

                if intersection/union >= 0.5:
                    num_TP_in_true += 1
                    if np.sum(indx_true) == 1:
                        num_TP_single_target +=1
                    break

                    

        return num_TP_in_pred, num_TP_in_true, num_instances_pred, num_instances_true, intersection_sum, union_sum, num_TP_single_target
    
    def cal_precision_recall_all(self, labels_true, labels_pred, instance_id_true, instance_id_pred, frame_id, num_class = 4, targets_for_debug=None):
        """ 
        Parameters
        -------------
        labels_true: 1-d array
            The true labels of the targets of all the frames
        labels_pared: 1-d array
            The predicted labels of the targets of all the frames 
        instance_id_true:
            The instance ID of the targets of all frames from SSD bounding box
        instance_id_pred:
            The instance ID of the post-clustering output
        frame_id: 1-d array
            The frame_id of each target. The size of frame_id should be equal to labels_true and labels_pred 

        Returns
        -------------
        precision: 1-d array 
            the precision of each class
        recall: 1-d array
            the recall of each class

        """

        num_TP_in_pred = np.zeros(num_class)
        num_TP_in_true = np.zeros(num_class)
        intersection_sum = np.zeros(num_class)
        union_sum = np.zeros(num_class)
        num_instance_pred = np.zeros(num_class)
        num_instance_true = np.zeros(num_class)
        precision = np.zeros(num_class)
        recall = np.zeros(num_class)
        num_TP_single_target_total = 0
        pbar = tqdm.tqdm(total = frame_id.max()+1, desc='calculate precision and recall')
        for i in np.arange(0, frame_id.max()+1):
            pbar.update()
            # if i<100:
            #     continue
            labels_true_single = labels_true[frame_id==i]
            labels_pred_single = labels_pred[frame_id==i]
            instance_id_pred_single = instance_id_pred[frame_id==i]
            instance_id_true_single = instance_id_true[frame_id==i]
            for j in np.arange(1, num_class):
                num_TP_in_pred_single, num_TP_in_true_single, num_instance_pred_single, num_instance_true_single, intersection_single, union_single, num_TP_single_target = cal_precision_recall_single(labels_true_single, 
                                                                                                                labels_pred_single, 
                                                                                                                instance_id_true_single, 
                                                                                                                instance_id_pred_single, 
                                                                                                                class_label=j)
                                                                                                                # targets_for_debug=targets_for_debug[frame_id==i,:])
                # print("num_TP_in_pred_single",num_TP_in_pred_single)
                # print("num_TP_in_true_single", num_TP_in_true_single)

                num_TP_in_pred[j] += num_TP_in_pred_single
                num_TP_in_true[j] += num_TP_in_true_single
                num_instance_pred[j] += num_instance_pred_single
                num_instance_true[j] += num_instance_true_single
                intersection_sum[j] += intersection_single
                union_sum[j] += union_single
                num_TP_single_target_total += num_TP_single_target
        precision = num_TP_in_pred / num_instance_pred
        recall    = num_TP_in_true / num_instance_true

        return precision, recall, intersection_sum/union_sum, num_TP_single_target_total

    eps_xy_list = [None, 0.5, 2 , 4]
    eps_v_list = [None, 2, 1.6, 1]
    min_targets_list = [None, 1, 2, 3]
    
    def post_clustering(self, targets_xyv, labels_pred, frame_id, DBSCAN_eps = 1.1, DBSCAN_min_samples=1, algorithm=1, target_scores = None, filter_objects = False):
        """  
        Parameters:
        ------------------
        targets_xyv: 2-d array
            The x, y coordinates and velocity of targets
        labels_pred: 1-d array
            The predicted labels of the targets of all the frames 
        frame_id: 1-d array 
            The frame_id of each target. The size of frame_id should be equal to labels_pred and targets_rav
        """
        color_LUT = np.array(['c','g','r','b'])
        min_scores_list = []
        post_clst_id = -1 * np.ones(targets_xyv.shape[0])
        pbar = tqdm.tqdm(total = frame_id.max()+1, desc='post_clustering')
        t = 0
        debug_mode = False
        filter_objects = True
        for i in np.arange(0, frame_id.max() + 1):
            pbar.update()
            if debug_mode and i < 3803:
                continue
            targets_xyv_single = targets_xyv[frame_id==i, :]
            labels_pred_single = labels_pred[frame_id==i]
            targets_xyv_ped = targets_xyv_single[labels_pred_single==1, :]
            targets_xyv_biker = targets_xyv_single[labels_pred_single==2, :]
            targets_xyv_car = targets_xyv_single[labels_pred_single==3, :]
            targets_scores_single = target_scores[frame_id == i, :] / np.reshape(np.linalg.norm(target_scores[frame_id == i, :] , ord=2, axis=1), (-1, 1))
            # first time
            if targets_xyv_ped.shape[0] > 0:
                post_clst_id_ped = cylinder_cluster(targets_xyv_ped[:, :3], eps_xy = self.eps_xy_list[1], eps_v = self.eps_v_list[1], min_targets=self.min_targets_list[1])
                max_clst_id_ped = post_clst_id_ped.max()
            else:
                post_clst_id_ped = np.array([])
                max_clst_id_ped = -1
            if targets_xyv_biker.shape[0] > 1:
                post_clst_id_biker = cylinder_cluster(targets_xyv_biker[:, :3], eps_xy = self.eps_xy_list[2], eps_v = self.eps_v_list[2], min_targets=self.min_targets_list[2])
                    
                max_clst_id_biker = max_clst_id_ped + 1 + post_clst_id_biker.max()
            else:
                post_clst_id_biker = -1 * np.ones([targets_xyv_biker.shape[0]])
                max_clst_id_biker = max_clst_id_ped 
            if targets_xyv_car.shape[0] > 2:
                post_clst_id_car = cylinder_cluster(targets_xyv_car[:, :3], eps_xy = self.eps_xy_list[3], eps_v = self.eps_v_list[3], min_targets=mself.in_targets_list[3])
                
            else:
                post_clst_id_car = -1 * np.ones([targets_xyv_car.shape[0]])

            post_clst_id_biker[post_clst_id_biker>-1] = post_clst_id_biker[post_clst_id_biker>-1] + max_clst_id_ped+1
            post_clst_id_car[post_clst_id_car>-1] = post_clst_id_car[post_clst_id_car>-1] + max_clst_id_biker + 1

            post_clst_id_single = -1 * np.ones(np.sum(frame_id == i))
            post_clst_id_single[labels_pred_single==1] = post_clst_id_ped 
            post_clst_id_single[labels_pred_single==2] = post_clst_id_biker
            post_clst_id_single[labels_pred_single==3] = post_clst_id_car
            labels_pred_single[post_clst_id_single==-1] = 0
            if debug_mode:
                plt.figure(figsize = (16, 16))
                plt.title("Frame:{}".format(i))
                ax1 = plt.subplot(221)
                ax1.set_title("cluster before refinement")
                sc1 = ax1.scatter(targets_xyv_single[:, 1], targets_xyv_single[:, 0], c = post_clst_id_single, s = 10*post_clst_id_single+7)
                plt.colorbar(sc1, ax=ax1)
                ax1.set_xlim([-25, 25])
                ax1.set_ylim([0, 40])
                ax2 = plt.subplot(222)
                ax2.set_title("labels before refinement")
                ax2.scatter(targets_xyv_single[:, 1], targets_xyv_single[:, 0], c = color_LUT[labels_pred_single])
                ax2.set_xlim([-25, 25])
                ax2.set_ylim([0, 40])

            space_threshold = 1
            speed_threshold = [0, 3, 2, 1.2]
            score_threshold = 0.6

            if post_clst_id_single.shape[0] > 0 and filter_objects:
                min_dist_mat = 10 * np.ones([int(post_clst_id_single.max() + 1), int(post_clst_id_single.max() + 1)])
                min_v_diff_mat = 10 * np.ones([int(post_clst_id_single.max() + 1), int(post_clst_id_single.max() + 1)])
                object_label_list = 5 * np.ones(int(post_clst_id_single.max() + 1))
                for k in np.arange(int(post_clst_id_single.max() + 1)):
                    for l in np.arange(int(post_clst_id_single.max() + 1)):
                        if k!=l and np.sum(post_clst_id_single == k) == 0 or np.sum(post_clst_id_single == l) == 0:
                            continue
                        object_label_list[k] = labels_pred_single[post_clst_id_single==k][0]
                        min_dist_pair = distance.cdist(targets_xyv_single[post_clst_id_single == k, :2], targets_xyv_single[post_clst_id_single == l, :2]).min()
                        min_dist_mat[k, l] = min_dist_pair 
                        min_v_diff_pair = distance.cdist(np.reshape(targets_xyv_single[post_clst_id_single == k, 2], (-1, 1)), np.reshape(targets_xyv_single[post_clst_id_single == l, 2], (-1, 1))).min()
                        min_v_diff_mat[k, l] = min_v_diff_pair
                        min_score_diff_pair = distance.cdist(targets_scores_single[post_clst_id_single == k, :], targets_scores_single[post_clst_id_single == l, :]).min()
                        if min_dist_pair < space_threshold:
                            label1 = labels_pred_single[post_clst_id_single == k][0] 
                            label2 = labels_pred_single[post_clst_id_single == l][0]
                            if (label1 == 2 and label2 == 3) or (label1 == 3 and label2 == 2):
                                min_scores_list.append(min_score_diff_pair)
                                # print(min_scores_list)
                                if min_v_diff_pair < speed_threshold[3]:
                                    num_targets1 = np.sum(post_clst_id_single == k)
                                    num_targets2 = np.sum(post_clst_id_single == l)
                                    if num_targets1 > num_targets2:
                                        label_refine = label1
                                    else:
                                        label_refine = label2 
                                    if label_refine == 3 and min_score_diff_pair < score_threshold:
                                        post_clst_id_single[post_clst_id_single == k] = l
                                        labels_pred_single[post_clst_id_single == k] = label_refine
                                        labels_pred_single[post_clst_id_single == l] = label_refine
                            elif (label1 == 1 and label2 == 3) or (label1 == 3 and label2 == 1):
                                if min_v_diff_pair < speed_threshold[3]:
                                    num_targets1 = np.sum(post_clst_id_single == k)
                                    num_targets2 = np.sum(post_clst_id_single == l)
                                    if num_targets1 > num_targets2:
                                        label_refine = label1
                                    else:
                                        label_refine = label2 
                                    if label_refine == 3  and min_score_diff_pair < score_threshold:
                                        post_clst_id_single[post_clst_id_single == k] = l
                                        labels_pred_single[post_clst_id_single == k] = label_refine
                                        labels_pred_single[post_clst_id_single == l] = label_refine
                            elif (label1 == 1 and label2 == 2) or (label1 == 2 and label2 == 1):
                                if min_v_diff_pair < speed_threshold[2]:
                                    num_targets1 = np.sum(post_clst_id_single == k)
                                    num_targets2 = np.sum(post_clst_id_single == l)
                                    if num_targets1 > num_targets2:
                                        label_refine = label1
                                    else:
                                        label_refine = label2 
                                    if label_refine == 2 and min_score_diff_pair < score_threshold:
                                        post_clst_id_single[post_clst_id_single == k] = l
                                        labels_pred_single[post_clst_id_single == k] = label_refine
                                        labels_pred_single[post_clst_id_single == l] = label_refine
                num_obj_around = np.sum(np.logical_and(min_dist_mat < space_threshold, min_v_diff_mat < speed_threshold[3]), axis = 1)
                id_list_of_cars_surrounded_by_a_lot_of_bikers = np.nonzero(np.logical_and(num_obj_around>2, object_label_list == 3))
                for id_of_cars_surrounded_by_a_lot_of_bikers in id_list_of_cars_surrounded_by_a_lot_of_bikers:
                    labels_pred_single[post_clst_id_single == id_of_cars_surrounded_by_a_lot_of_bikers] = 2

            # second time                     
            targets_xyv_ped = targets_xyv_single[labels_pred_single==1, :]
            targets_xyv_biker = targets_xyv_single[labels_pred_single==2, :]
            targets_xyv_car = targets_xyv_single[labels_pred_single==3, :]
            if targets_xyv_ped.shape[0] > 0:
                post_clst_id_ped = cylinder_cluster(targets_xyv_ped[:, :3], eps_xy = self.eps_xy_list[1], eps_v = self.eps_v_list[1], min_targets=self.min_targets_list[1])
                max_clst_id_ped = post_clst_id_ped.max()
            else:
                post_clst_id_ped = -1 * np.ones([targets_xyv_ped.shape[0]])
                max_clst_id_ped = -1
            if targets_xyv_biker.shape[0] > 1:
                post_clst_id_biker = cylinder_cluster(targets_xyv_biker[:, :3], eps_xy = self.eps_xy_list[2], eps_v = self.eps_v_list[2], min_targets=self.min_targets_list[2] )
                max_clst_id_biker = max_clst_id_ped + 1 + post_clst_id_biker.max()
            else:
                post_clst_id_biker = -1 * np.ones([targets_xyv_biker.shape[0]])
                max_clst_id_biker = max_clst_id_ped 
            if targets_xyv_car.shape[0] > 2:
                post_clst_id_car = cylinder_cluster(targets_xyv_car[:, :3], eps_xy = self.eps_xy_list[3], eps_v = self.eps_v_list[3], min_targets=self.min_targets_list[3])
                
            else:
                post_clst_id_car = -1 * np.ones([targets_xyv_car.shape[0]])

            post_clst_id_biker[post_clst_id_biker>-1] = post_clst_id_biker[post_clst_id_biker>-1] + max_clst_id_ped+1
            post_clst_id_car[post_clst_id_car>-1] = post_clst_id_car[post_clst_id_car>-1] + max_clst_id_biker + 1

            post_clst_id_single = -1 * np.ones(np.sum(frame_id == i))
            post_clst_id_single[labels_pred_single==1] = post_clst_id_ped 
            post_clst_id_single[labels_pred_single==2] = post_clst_id_biker
            post_clst_id_single[labels_pred_single==3] = post_clst_id_car
            labels_pred_single[post_clst_id_single==-1] = 0

            post_clst_id[frame_id==i] = post_clst_id_single
            labels_pred[frame_id==i] = labels_pred_single

        min_scores_list = np.array(min_scores_list)
        return post_clst_id, labels_pred
    
    def cal_f1(self, precision, recall):

        return 2*precision*recall/(precision+recall)
