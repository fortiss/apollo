# Perception
This file documents all the details about changes and implementations in the apollo framework to get the perception up 
and running. 

## Run the perception

### Commands
For running the perception (currently only the [point cloud object detection](../../modules/perception/README.md)) you need to start the following scripts 

Could also be in one launch file, order is not relevant

after entering the docker container:

1. ```$ cyber_launch start modules/transform/launch/static_transform_fortiss_with_umrr.launch```
2. ```$ cyber_launch start modules/drivers/velodyne/launch/velodyne32_fortuna.launch```
3. ```$ cyber_launch start modules/perception/production/launch/perception_fortiss.launch```

### Explanations
Some explanations what these launch files do:

1. [Static transform](../../modules/transform/launch/static_transform_fortiss.launch) launches transformation 
information: __imar2localization__ and __imar2velodyne32__.
2. [Velodyne driver](../../modules/drivers/velodyne/launch/velodyne32_fortuna.launch) publishes the point cloud from the 
top Velodyne-VLC32 and compensates the point cloud with pose information.
3. The [perception module](../../modules/drivers/velodyne/launch/velodyne32_fortuna.launch) segments the incoming point cloud, 
clusters the point cloud, classifies it and tracks the classified objects.

### Input/output topics
| Node            | Input | Output                                            |
| --------------- | ----  | --------------------------------------------------|
| static_transform | None | /tf_static |
| velodyne_driver | None  | /apollo/sensor/velodyne32/compensator/PointCloud2 |
| perception_module | /apollo/sensor/velodyne32/compensator/PointCloud2  | /apollo/perception/obstacles |

## Config files
Important config files to look at are located in:
1. [modules/transform/conf/](../../modules/transform/conf)
2. [modules/perception/production/conf/perception/lidar](../../modules/perception/production/conf/perception/lidar)
3. [modules/perception/production/conf/perception/fusion](../../modules/perception/production/conf/perception/fusion)
4. [modules/perception/production/conf/perception/perception_common_fortiss.flag](../../modules/perception/production/conf/perception/perception_common_fortiss.flag)
5. [modules/common/adapters/adapter_gflags.cc](../../modules/common/adapters/adapter_gflags.cc)

Especially in 5. we changed the pointcloud_topic to __/apollo/sensor/velodyne32/compensator/PointCloud2__ for visualizing in dreamview in the commit 83e2022e78d519b62db77383a1eed251afdd8583. 

## Coordinate frames
The perception currently needs 3 frames: 
1. world2localization: Published by the [imar node](../../modules/drivers/imar35/launch/imar35.launch)
2. localization2imar: Published by the [static transform node](../../modules/transform/launch/static_transform_fortiss.launch)
3. imar2velodyne32: Published by the [static transform node](../../modules/transform/launch/static_transform_fortiss.launch)

## Visualize everything
For visualization you can either call for only point cloud and images:

```$ cyber_visualizer```

or start dreamview for also show the detected objects and the compensated poitn cloud by calling:

```$ bash scripts/bootstrap.sh start```

then in the top select fortiss and as vehicle fav. Switch to layer menu and activate the pointcloud. 

Note: Dreamview only shows compensated point clouds

## Known issues and possible solutions
- No points from velodyne driver: 
1. Find out the velodyne IP-adress (Normally for the top one: 192.168.140.201) 
2. Type it into a browser. 
3. Set the target to broadcast (192.168.140.255). Set and save.
4. Set the target back to your computer (For PC1: 192.168.140.158). Set and save.

- Point cloud is classified wrongly
1. Apollo does not provide a trained model for the VLP-32C.
2. Either wait for apollo to do that
3. Or train an own model

- Transform is looking into the future
1. The velodyne driver needs GPS time which is currently not provided by our valodyne(s) (gps is not wired the the valodyne fusion box)
2. Hotfix by setting the GPS time to current cyber time in line 76 and line 105 of [velodyne32_parser.cc](../../modules/drivers/velodyne/parser/velodyne32_parser.cc)
3. Changes were made in commits 6cac88f4ad70ca2e2046edd1d1c4a5ba754eea18 and 853d00fdc34b8f3f4581822d5ad3067af106f98a

- Cannot start dreamview and concurrently run the [perception module](../../modules/drivers/velodyne/launch/velodyne32_fortuna.launch)
1. Our fortiss Lenovo Thinkpads with a GeForce 940MX does not have enough GPU memory available for running dreamview and the pipeline
2. If you have a better GPU it should work
3. TODO does it work in the car?

- Starting the Perception Component:

This is not an error and shall not be corrected. (if you provide NVBLAS CONFIG FILE correctly you end up with other errors!)
`[lidar_perception_fortiss]  [NVBLAS] NVBLAS_CONFIG_FILE environment variable is NOT set : relying on default config filename 'nvblas.conf'
[lidar_perception_fortiss]  [NVBLAS] Cannot open default config file 'nvblas.conf'
[lidar_perception_fortiss]  [NVBLAS] Config parsed
[lidar_perception_fortiss]  [NVBLAS] CPU Blas library need to be provided`

If you have this error, restart the PC:
`[lidar_perception_fortiss]  GPUassert: unknown error modules/perception/lidar/lib/segmentation/cnnseg/cnn_segmentation.cc 84`

- You have to provide the tf static transformation, otherwise the perception component does not work.