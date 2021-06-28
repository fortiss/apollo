#!/usr/bin/env python

# license removed for brevity

import sensor_msgs.point_cloud2 as pc2
from math import pi, cos, sin

# CRT
from cyber_py import cyber

# Define the fields of the output point cloud message
fields = [pc2.PointField('x',             0, pc2.PointField.FLOAT32, 1),
          pc2.PointField('y',             4, pc2.PointField.FLOAT32, 1),
          pc2.PointField('z',             8, pc2.PointField.FLOAT32, 1),
          pc2.PointField('Speed_Radial', 12, pc2.PointField.FLOAT32, 1),
          pc2.PointField('RCS' ,         16, pc2.PointField.FLOAT32, 1)]

# publisher for the pointcloud with the cartesian coordinates
# CRT
spherical_node = cyber.Node("target_list_2_pointcloud")
pub = spherical_node.create_writer("target_list_cartesian", pc2.PointCloud2, queue_size=10)


def callback(data):
    points = []

    # Get the index of the needed fields
    for field, i in zip(data.fields, range(len(data.fields))):
        if field.name == "Range":
            range_index = i
        if field.name =="Azimuth":
            azimuth_index = i
        if field.name == "Elevation":
            elevation_index = i
        if field.name == "Speed_Radial":
            speed_rad_index = i
        if field.name == "RCS":
            rcs_index = i    

    for point in pc2.read_points(data):
        # compute cartesian coordinates from range, azimuth and elevation
        dist = point[range_index]
        azimuth_phi = point[azimuth_index] / 180.0 * pi
        elevation_theta = point[elevation_index] / 180.0 * pi

        x = dist * cos(elevation_theta) * cos(azimuth_phi)
        y = dist * cos(elevation_theta) * sin(azimuth_phi)
        z = dist * sin(elevation_theta)

        # add the point with all fields to the points list
        points.append([x, y, z, point[speed_rad_index], point[rcs_index]])

    # create pointcloud message and publish it
    cloud_msg = pc2.create_cloud(data.header, fields, points)
    # CRT
    pub.write(cloud_msg)


def target_list_2_pointcloud():

    # CRT
    cyber.init() #TODO: I am not sure if this is necessary
    # spherical_node is created at the beginning, because it is needed to create writer
    spherical_node.create_reader("filtered_targets", pc2.PointCloud2, callback)
    spherical_node.spin()

if __name__ == '__main__':
    target_list_2_pointcloud()
