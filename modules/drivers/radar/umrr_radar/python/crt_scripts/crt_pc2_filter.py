#!/usr/bin/env python

# -*- coding: utf-8 -*-

import sensor_msgs.point_cloud2 as pc2
from math import pi, cos, sin

from dynamic_reconfigure.server import Server as DynamicReconfigureServer
from umrr_driver.cfg import pc2filterConfig as ConfigType

# CRT
from cyber_py import cyber

# toDo: make subscription dumb e.g. no parameter should be necessary
# print error if no appropiate topic is found in namespace


class crt_pc2_filter:
    """Node example class."""

    def __init__(self):
        # Create a dynamic reconfigure server.
        self.reconf_server = dyn_reconfigure()

        # CRT
        self.pc2_node = cyber.Node("pc2_filter")
        # setup subscriber to spehrical coordinates
        self.sub = self.pc2_node.create_reader("target_list", pc2.PointCloud2, self.mod_pcl, queue_size=5)
        # setup publisher for spherical coordinates    
        self.pub = self.pc2_node.create_writer("filtered_targets", pc2.PointCloud2, queue_size=5)

        self.pc2_node.spin()

    # this is the callback function for the subscriber (reader)  of the sensor data
    def mod_pcl(self, cloud):
        # toDo: modify to listen to spherical coordinates
        # setup temporary point list
        points = []
        # read in all information from msg
        for field, i in zip(cloud.fields, range(len(cloud.fields))):
            if field.name == "Azimuth":
                azimuth_index = i
            if field.name == "Range":
                range_index = i
            if field.name == "Elevation":
                elevation_index = i
            if field.name == "Speed_Radial":
                sp_index = i
            if field.name == "RCS":
                rcs_index = i
            if field.name == "Cycle_Duration":
                cycled_dur_index = i
            if field.name == "Number_Of_Objects":
                num_object_index = i
            if field.name == "Noise":
                noise_index = i
            if field.name == "Power":
                power_index = i


        for point in pc2.read_points(cloud):
            # calulate height in cartesian style
            z = sin(point[elevation_index] / 180.0 * pi) * point[range_index]
            # # check for each filter stage if enabled
            # apply selected filter value
            if self.reconf_server.filter_height:
                if z < self.reconf_server.height_min:
                    continue
                if z > self.reconf_server.height_max:
                    continue
            if self.reconf_server.filter_speed:
                if point[sp_index] < self.reconf_server.speed_min:
                    continue
                if point[sp_index] > self.reconf_server.speed_max:
                    continue
            if self.reconf_server.filter_rcs:
                if point[rcs_index] < self.reconf_server.rcs_min:
                    continue
                if point[rcs_index] > self.reconf_server.rcs_max:
                    continue
            if self.reconf_server.filter_range:
                if point[range_index] < self.reconf_server.range_min:
                    continue
                if point[range_index] > self.reconf_server.range_max:
                    continue
            if self.reconf_server.filter_azimuth:
                if point[azimuth_index] < 0:
                    # point lies to the left
                    if abs(point[azimuth_index]) > self.reconf_server.angle_left:
                        continue
                else:
                    # point lies to the right
                    if point[azimuth_index] > self.reconf_server.angle_right:
                        continue
            # if point passes all selected filter stages append it
            points.append(point)

        # create cloud message
        cloud_msg = pc2.create_cloud(cloud.header, cloud.fields, points)

        # publish message
        # CRT        
        self.pub.write(cloud_msg)

class dyn_reconfigure:
    """Reconfigure_demo example class."""

    def __init__(self):
        # setup up dynamic reconfigure server
        self.server = DynamicReconfigureServer(ConfigType, self.reconfigure_cb)

    def reconfigure_cb(self, config, dummy):
        """Create a callback function for the dynamic reconfigure server."""
        # Fill in local variables with values received from dynamic reconfigure
        self.filter_height = config["filter_height"]
        self.filter_rcs = config["filter_rcs"]
        self.filter_speed = config["filter_speed"]
        self.filter_range = config["filter_range"]
        self.filter_azimuth = config["filter_azimuth"]
        self.height_min = config["height_min"]
        self.height_max = config["height_max"]
        self.rcs_min = config["rcs_min"]
        self.rcs_max = config["rcs_max"]
        self.speed_min = config["speed_min"]
        self.speed_max = config["speed_max"]
        self.range_min = config["range_min"]
        self.range_max = config["range_max"]
        self.angle_left = config["FOV_left"]
        self.angle_right = config["FOV_right"]

        return config


# Main function.
if __name__ == '__main__':
    
    # CRT
    cyber.init() #TODO: I am not sure if this is necessary
    pcl = crt_pc2_filter()