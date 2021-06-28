import sys
sys.path.insert(1, '/apollo/modules/drivers/radar/umrr_radar/python/crt_proto/')
sys.path.insert(1, '/apollo/modules/common/proto/')
sys.path.insert(1, '/apollo/modules/drivers/proto/')
# CRT
# from cyber_py import cyber
from cyber_py3 import cyber
from cyber_py3 import cyber_time

# these imports support reading of a configuration
import json
from google.protobuf.json_format import MessageToJson
from google.protobuf import json_format

from RTCnet.RTCnet_utils import RTCRunner
from RTCnet.RTCnet_utils import Clustifier

from umrr_radar_conf_pb2 import SetupConf

# this incoming radar pointcloud data
import pointcloud_pb2 as pc_2

# this is outgoing classified radar data
import umrr_radar_objects_pb2 as umrro_2

import numpy as np


# this is used to get execution arguments
import sys


class umrr_objects_classifier:

    def __init__(self):

        # CRT
        self.ummrr_objects_classifier_node = cyber.Node(
            "umrr_objects_classifier")
        self.seq = 0

        if len(sys.argv) != 3:
            print("Usage:", sys.argv[0],
                  "Config file for radar object classifier")
            sys.exit(-1)

        self.setup_conf = SetupConf()

        with open(sys.argv[2], 'r') as myfile:
            data = myfile.read()

        json_format.Parse(data, self.setup_conf, ignore_unknown_fields=False)
        
        # create an instance of a model ensemble
        self.runner = RTCRunner()
        
        # create an instance for the clustifier
        self.clustifier = Clustifier()
        
        # create the writer for sending object information
        self.publisher = self.ummrr_objects_classifier_node.create_writer(self.setup_conf.write_channel, pc_2.PointCloud, qos_depth=2)

        # subscribe to channel for getting radar pointcloud data, and specify a callback function
        self.subscriber = self.ummrr_objects_classifier_node.create_reader(
            self.setup_conf.read_channel, pc_2.PointCloud, self.frame_reception_callback)

    def frame_reception_callback(self, data):

        print("=" * 80)
        print("py:reader callback msg->:")
        # data shall be of type PointCloud
        print(data)
        print("=" * 80)                            


        # Create targets list to be used as an input for classification pipeline
        
        for single_point in data.point:
            targets = np.concatenate([single_point.x, single_point.y, single_point.vel, single_point.rcs], axis=1)

        # Get the classification result and transform it into proto output data
        pred_labels, final_scores = self.runner.execute_ensemble(targets)
        
        # run the clustering
        # all the points are of the same radar frame, therefore here I will use frame_id as 0
        frame_id = np.array([0] * len(pred_labels))
        clustered_pred_labels, instance_id_pred = self.clustifier.cluster_labels(targets, frame_id, pred_labels, final_scores)
        
        
        obj_msg = umrro_2.UmrrRadar()

        obj_msg.header.timestamp_sec = cyber_time.Time.now().to_sec()
        obj_msg.header.radar_timestamp = int(cyber_time.Time.now().to_sec())
        obj_msg.header.module_name = "Objects UMMR CAN Publisher"
        obj_msg.header.sequence_num = self.seq
        obj_msg.header.frame_id = data.header.frame_id

        obj_msg.frame_id = data.frame_id
        
        # now we need to create objects from obtained labels and clusters
        for i in range(clustered_pred_labels.max() + 1):
            single_object_targets = targets[instance_id_pred == i]
            label = clustered_pred_labels[instance_id_pred == i]
            
            try:                       
                #adding UmrrObject
                idt_obj = obj_msg.umrrobs.add()
                
                idt_obj.header = obj_msg.header
                idt_obj.obstacle_id = i
                
                # TODO - possibly calculate an average position - center of all the targets contributing to single object
                idt_obj.longitude_dist = single_object_targets[0][0]
                idt_obj.lateral_dist = single_object_targets[0][1]
                
                # TODO - calculate longitudinal and lateral velocity based on spehrical velocity
                idt_obj.longitude_vel = single_object_targets[0][2]
                idt_obj.lateral_vel = single_object_targets[0][2]
                
                # TODO - do I need length
                idt_obj.length = single_object_targets[0][3]
                
                # TODO - where do we project information about object type?
                idt_obj.obstacle_type = label[0]

            except KeyError:
                # CRT
                logging.warning("Incomplete object data received. Skipping result.")
                
        # sending a message with classified objects
        self.publisher.write(self, obj_msg)
            
            
            

        

if __name__ == '__main__':
    # CRT
    cyber.init()
    umrr_objects_classifier()
