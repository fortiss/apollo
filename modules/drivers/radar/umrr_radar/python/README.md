umrr_drivers 0.1.0
=======================

Overview/Purpose
-----------------------

This package provides a ROS node to convert the target list of a radar sensor into a PointCloud2 message and nodes to further process the point clouds. The main node `umrr_can_publisher` configures the radar sensor and reads the incoming CAN messages. Also provided is an example for 3D Visualization using Rviz.

Hardware prerequisites
-----------------------
- smartmicro automotive radar sensor (for information about the SmartMicro UMRR_8F type 146 radar sensors installed in the Fortuna vehicle, please read the pdf files in the docs folder)
- Lawicel USBCAN adapter or any other adapter compatible with linux providing an can socket. The CAN interface in Fortuna is a PEAK PCI Express FD CAN card which supports SocketCAN.

**Important note about using this ROS node with the radars installed in Fortuna research vehicle:**

The umrr_driver uses the SmartMicro UAT protocol which establishes communication with the sensors and via this protocol the ROS node sends commands to receive the sensor status or alter parameters of the sensor such as the Antenna Mode or the Waveform mode. As can be seen in the folder umrr_driver/src/smartmicro/Protocols/uat/, there are four different UAT versions from 1 to 4. Each one uses different definitions regarding the structure, encoding and decoding of CAN messages. The umrr_driver package as offered by SmartMicro supports only the UATv4 protocol. Unfortunately, the software installed in the radar sensors of Fortuna, even though it is the latest version that these sensors support, does not work with UATv4 but rather with UATv1.

This leads to an error of "unsupported UDT-UAT response index received". As SmartMicro support suggested, to overcome this error, we can edit the yaml configuration files in umrr_driver/cfg/ and set debug = 1. This way, as can be seen in umrr_driver/scripts/umrr_publisher, the node does not use communication services (sensor_status, sensor_parameter) and just receives the radar target list from the sensors. Even though this avoids the errors and provides the basic functionality of reading the radar detections, it does not offer the ability to alter sensor parameters such as the Antenna mode or the waveform node. Per smartmicro support, since their umrr_driver fully supports only UATv4, we can send the following CAN messages to the sensor in order to alter those parameters:

**Waveform mode**  
long range  
E6.5D.00.44.01.00.0B.C8  
00.00.00.00.00.01.0B.C8  
medium range  
90.E9.00.44.01.00.0B.C8  
00.00.00.01.00.01.0B.C8  
short range  
0B.35.00.44.01.00.0B.C8  
00.00.00.02.00.01.0B.C8  

**Antenna mode**  
TX0  
70.73.00.84.01.00.0B.C8  
00.00.00.00.00.01.0B.C8  
TX1  
06.C7.00.84.01.00.0B.C8  
00.00.00.01.00.01.0B.C8  
TX2  
9D.1B.00.84.01.00.0B.C8  
00.00.00.02.00.01.0B.C8  

Those messages can be sent by using can-utils (https://sgframework.readthedocs.io/en/latest/cantutorial.html). For example we can set the waveform of the radar connected to interface can0 in long range mode via:

```
cansend can0 3FB#C80B000144005DE6
cansend can0 3FB#C80B010000000000
```


However, in order to have the full functionalities of the umrr_driver available for our radar sensors, we performed some changes in the provided source code. In particular, we changed the umrr_driver/src/smartmicro/Services/basicCANService.py to support both UATv4 (as originally provided) and UATv1. In addition, we made changes in the umrr_driver/src/smartmicro/Services/protocolServices/parameter.py and status.py so that they provide the parameter dictionaries as expected by UAT Version 1.

With these changes, the umrr_driver successfully receives the radar target list but can also set the Antenna and Waveform mode via the yaml configuration files. Currently, there is only a minor limitation with this approach. The umrr_driver sends a Status request in order to receive the version of the software installed in the sensors (see read_sw_version() method of umrr_publisher) and based on the response, it identifies the sensor type as UMRR_11 or UMRR_8F. Because the software installed in the Fortuna UMRR_8F sensors does not recognize this Status request, it responds with zeros which leads to an erroneous identification of the sensors as UMRR_11. The type of the sensors is only used in the umrr_publisher in order to select which command to use for reading the Antenna mode. Therefore, we made a change to set the sensor as UMRR_8F when the response to this Status request is zero and the publisher correctly receives the Antenna mode as it is set on startup based on the yaml configuration file.   

Configuration
-----------------------
This driver is designed for Ubuntu 16.04 LTS running ROS Kinectic
Can Protocol format: json configuration file

Test Environment
-----------------------
Tested with Lawicel USBCAN Adapter using umrr8f and umr11.
Extended to work with PEAK PCI Express FD card using umrr8f

Installation
-----------------------
The node operates using a can socket. If you are not using the LAWICEL adapter make sure the socket is reachable for example using the command
candump slcan0

The Lawicel adapter can be installed using the following steps:

1. add the kernel module slcan to your etc/modules file so it is loaded during booutup
2. check if the module is running by typing lsmod|grep slcan
output should look similar to: slcan   16834 0
3. install can-utils by typing
sudo apt install can-utils
4. Map the usb on a can device by running
sudo slcand -o -c -f -s6 /dev/ttyUSB0 slcan0
5. Setup the network device making the socket available for the userspace
sudo ifconfig slcan0 up
6. Test if the setup is done and working correctly by typing
candump slcan0
You shuld see the raw can messages


Regarding the **PEAK PCI CAN card**, PEAK SocketCAN drivers are already included in the Linux kernel and therefore there is no needed for further installations. We just need to perform the following steps in order to set up the communication between the CAN interface and the computer:

1. Load the necessary can modules:

```
$ modprobe can_dev
$ modprobe can
$ modprobe can_raw
```
Note that can_dev is usually pre-loaded because it is required by the peak_pciefd module which is loaded on linux startup.
The loaded modules can be checked with:
```
$ lsmod | grep can
$ lsmod | grep peak
```

2. Configure the IP link and specify the CAN bus bitrate:

```
$ sudo ip link set can0 type can bitrate 500000
$ sudo ifconfig can0 up
```

Note that can0 corresponds to a specific port of the PCI can card. Depending on the number of ports on the card, several interfaces can be started in the same way as above, just by changing the final index to can1 etc.

3. Check if the RAW can data are being received:
```
$ candump can0
```

For further information on SocketCAN and the PEAK device, please visit:
1. https://en.wikipedia.org/wiki/SocketCAN
2. https://www.peak-system.com/fileadmin/media/linux/index.htm
3. https://www.peak-system.com/PCAN-PCI-Express-FD.414.0.html?&L=1



This node requires python 3 while ROS only supports python 2.7 therefore we need to set up an virtual environment

Prerequisites:
install the following packages:
```
sudo apt-get install python3 python3-dev virtualenvwrapper virtualenv
```

Close and reopen you shell afterwards to update your .bash_rc (or run the command "source ~/.bashrc")

1. Create a virtual environment using:
```
mkvirtualenv -p /usr/bin/python3 <your_enviroment_name>
```
This creates an environment and also activates it. Notice the brackets in your command line prompt
2. install the following packages in your virtual environment
rospkg
catkin_pkg
crc_mod
crc16
using the command:
```
pip install rospkg catkin_pkg crcmod crc16
```
Leave your virtual environment.

For convenient use e.g. nest the launch file in your existing project, you will have to edit the umrr_can_publisher script.
Open the python script located in umrr_drivers/src and edit the shebang line.

Enter the path to the environment you just setup. To do this:
1. Open a new terminal
2. type "workon <name_of_your_environment>"
3. type "echo $VIRTUAL_ENV" copy the resulting path and leave the console
4. enter the obtained path to your shebang path for example: #!/home/user/.virtualenvs/ros_treiber/bin/python


Usage
-----------------------

The `umrr_can_publisher` node needs Python3, while ROS officially only supports Python2.
So make sure you are starting this node with Python3, for example by using a virtual environment.

Make sure the can socket is available to linux

1. Open a console and type:
```
roslaunch umrr_driver automotive_radar.launch
```
Note! If the above command yields a 'No such file or directory' error, it is probably due to Windows newlines (\r) in the umrr_can_publisher script, which are not recognized by Linux. This can be resolved via:
```
dos2unix umrr_can_publisher
```
3. Incoming data should now be visible to check type
```
rostopic echo /target_list
```
4. Visualization can be started using
```
roslaunch umrr_driver visualization.launch
```
Name of the launcher is subject to be changed.

Launch Files
----------------------

The launch file `visualization.launch` is an example for a basic visualization using Rviz

Nodes
----------------------

### Umrr_Can_Publisher

This node reads the incoming CAN messages, writes the targets to a PointCloud2 message using the `can_spec` and publishes it.

**Important:** This node need Python3, while ROS officially only supports Python2.
So make sure you are starting this node with Python3, for example by using a virtual environment.

#### Published Topics

* **`target_list`** (sensor_msgs/PointCloud2)

  A point cloud with the radar targets of the current cycle. Depending on the sensor configuration, the point cloud
  will contain different fields, which are defined in the corresponding `can_spec`.

#### Parameters

* **`~can_spec`** (string)

  Path to the `can_spec` to use.

* **`~frame_id`** (string, default:"radar")

  Frame ID of the sensor.

* **`~can_socket`** (string, default:"slcan0")

  Can socket the node should use.

* **`~debug`** (int, default:"0")

  Choose to start node in debug mode, status requests are than switched off.

* **`~antenna_mode`** (dict, default:"")

  Provide a dict to configure the sensors used antenna on startup.

* **`~center_frequency`** (dict, default:"")

  Provide a dict to configure the sensors used center frequency on startup

###   pc2_filter.py

This node has the ability to filter incoming pointcouds from sensor by various criteria.
It offers a dynamic reconfigure server to configure the filter while running.

#### Subscribed Topics

* **`target_list`** (sensor_msgs/PointCloud2)

  The input cloud must contain the following fields:
  * `Range` (Unit: [m])
  * `Azimuth` (Unit: [°])
  * `Elevation` (Unit: [°])
  * `Speed_Radial` (Unit: [m/s])

#### Published Topics

* **`target_list_filtered`** (sensor_msgs/PointCloud2)  

  The output cloud contains the following fields:
  * `Range` (Unit: [m])
  * `Azimuth` (Unit: [°])
  * `Elevation` (Unit: [°])
  * `Speed_Radial` (Unit: [m/s])

### Sperical_Coord_2_Cartesian_Coord

This node converts a point cloud with targets in spherical coordinates to a point cloud with cartesian coordinates,
so that it is possible to view the point cloud in Rviz.

#### Subscribed Topics

* **`target_list_filtered`** (sensor_msgs/PointCloud2)

  The input cloud must contain the following fields:
  * `Range` (Unit: [m])
  * `Azimuth` (Unit: [°])
  * `Elevation` (Unit: [°])
  * `Speed_Radial` (Unit: [m/s])


#### Published Topics

* **`target_list_cartesian`** (sensor_msgs/PointCloud2)

  The output cloud contains the following fields:
  * `x` (Unit: [m])
  * `y` (Unit: [m])
  * `z` (Unit: [m])
  * `Speed_Radial` (Unit: [m/s])
