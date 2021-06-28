#!/home/fortiss/.virtualenvs/ros_python3/bin/python3

import sys
# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, '/apollo/modules/drivers/proto/')
sys.path.insert(1, '/apollo/modules/drivers/canbus/proto/')
sys.path.insert(1, '/apollo/modules/drivers/radar/umrr_radar/python/src/')
sys.path.insert(1, '/apollo/modules/common/proto/')
sys.path.insert(1, '/apollo/modules/drivers/radar/umrr_radar/python/crt_proto/')

import pointcloud_pb2 as pc_2

# from apollo.modules.drivers.proto.pointcloud_pb2 import pointcloud_pb2 as pc_2
# import apollo.drivers.pointcloud_pb2 as pc_2

import queue

# from std_msgs.msg import Header
import header_pb2 as header

from smartmicro.HardwareLayer.comFactory.comDeviceFactory import ComDeviceFactory
from smartmicro.Services.basicCanServices.targetService import CanIDServiceTargetList
from smartmicro.Services.communication import comDeviceTypes, Communication
from smartmicro.Services.protocolServices.status import Status
from smartmicro.Services.protocolServices.parameter import Parameter
from smartmicro.Services.basicCanServices.uatResponseService import uatResponseService
# from umrr_driver.srv import *

# CRT
#from cyber_py import cyber
from cyber_py3 import cyber

import logging

from umrr_radar_conf_pb2 import SetupConf
from umrr_radar_conf_pb2 import RadarConf
from umrr_radar_conf_pb2 import CanConf
from umrr_radar_conf_pb2 import ModeSetup

# these imports support reading of a configuration
import json
from google.protobuf.json_format import MessageToJson
from google.protobuf import json_format

# this is used to get execution arguments
import sys

class com_sensor:
    """
    Class is used to establish a connection over can with a sensor
    and register several services for target lists, status, parameter...
    Uses SmartMicro protocols
    """
    def __init__(self, rc, cc):
        """
        Function initializes the class with its necessary values
        Also takes steps to establish communication with the sensor
        """

        self.radar_conf = rc
        self.can_conf = cc                

        if hasattr(self.radar_conf, 'can_socket') and not(self.radar_conf.can_socket is None) and hasattr(self.can_conf, "can_spec") and not(self.can_conf.can_spec is None):
            # CRT
            self.sock = self.radar_conf.can_socket
            self.spec = self.can_conf.can_spec

            # establish connection with sensor
            self.__est_sens_con()
            # register receive services
            self.__reg_recv_services()
            # register communication protocols
            self.__reg_com_protocols()

            # CRT
            logging.info("Using can spec: %s", self.spec)
            logging.info("Using can socket: %s", self.sock)
        else:
            # CRT
            logging.log("Could not find necessary parameters on the Server!")

    def __est_sens_con(self):
        """
        Function creates a communication instance
        """
        device_inst = ComDeviceFactory.getDevice('CAN_SOCKET', self.sock)
        self.comMod = Communication([{'deviceType': comDeviceTypes.CAN, 'device': device_inst}])

    def __reg_recv_services(self):
        """
        Function creates target list and uat service and registers them in
        the communication instance
        """
        self.target_serv = CanIDServiceTargetList(self.spec)
        self.respserv = uatResponseService()
        #The below Identifier 0x400 is used for the
        #Specification of the output raw targets
        self.comMod.registerCanIDService(self.target_serv, 0x400, 0x7F)
        #The below Identifier 0x700 is used for the
        #Specification of the sensor software version
        self.comMod.registerCanIDService(self.respserv, 0x700)

    def __reg_com_protocols(self):
        """
        Function provides the necessary communication protocols
        """
        self.status = Status(self.comMod)
        self.parameter = Parameter(self.comMod)


class crt_umrr_publisher:
    """
    Class creates the ros node, provides steps to generate pc2 message
    from sensor target list and creates two services to communicate
    with the connected sensor through the status and parameter protocol-
    services
    """
    def __init__(self):
        
        # CRT
        self.ummrr_node = cyber.Node("umrr_can_publisher")        
                
        # advertise published topic in cyber rt
        # EW - in our case, we do not have a Parameter server, which represents a dictionary for a static configuration
        # our configuration is stored in the .pb.txt files, so we need to extract it from there.
        
        # CRT
        if len(sys.argv) != 2:
            print("Usage:", sys.argv[0], "Config file for Radar")
            sys.exit(-1)

        self.setup_conf = SetupConf()
        self.radar_conf = RadarConf()
        self.can_conf = CanConf()
        with open(sys.argv[1], 'r') as myfile:
            data=myfile.read()

        json_format.Parse(data, self.setup_conf, ignore_unknown_fields=False)
        
        self.radar_conf = self.setup_conf.radar_conf
        self.can_conf = self.setup_conf.can_conf

        #json_format.Parse(data, self.radar_conf, ignore_unknown_fields=False)  
        #json_format.Parse(data, self.can_conf, ignore_unknown_fields=False)  

        
        self.pub = self.ummrr_node.create_writer("target_list", pc_2.PointCloud, qos_depth=2)        
        self.frame_id = self.radar_conf.frame_id

        # CRT
        if hasattr(self.radar_conf, "debug") and not self.radar_conf.debug is None:
            # provide services for communication from outside
            self.__create_serv()

        # bind to socket and establish connection to sensor
        try:
            self.con_sensor = com_sensor(self.radar_conf, self.can_conf)            
            # CRT
            if not self.radar_conf.debug:
                self.__read_sw_version()
                self.__setup_sensor()
                self.__get_used_antenna()

            self.__inform_log()
            self.__run()
        except OSError as error_msg:
            # differ error according to its number
            if error_msg.errno == 2:                
                # evaluates to os error "file not found"                
                # CRT
                logging.error("Specified can spec not found!")
            elif error_msg.errno == 19:               
                # evaluates to os error "no such device"                
                # CRT
                logging.error("Specified socket not found!")
                

    def __run(self):
        """
        Function retreives messages from sensor and publishes pc2
        messages (This is a debug draft!)
        """
        # start spinning
        self.seq = 0
        
        # CRT
        start = cyber.Time.now()

        #CRT
        if not self.radar_conf.debug:
            #CRT
            logging.info("Clearing targetlist queue on startup...")
            try:
                self.con_sensor.target_serv.clearQueue()
            except queue.Empty:                
                # CRT
                logging.error("Could not clar the targetlist. Is sensor booted?")
        
        # CRT
        logging.info("Entering running loop...")
        
        # CRT
        while not cyber.is_shutdown():
            # get new target list from sensor
            try:
                target_list = self.con_sensor.target_serv.getTargetList(timeout=5)
            except queue.Empty:
                # this Error occours when the sensor queue is empty                
                # CRT
                logging.warning("Could not receive Target List! Is a Sensor connected?")
                # wait for next target list
                continue

            # create pointcloud message from received target list
            cloud_msg = self.__create_pcl_msg(target_list, self.seq)

            # CRT
            self.pub.write(cloud_msg)
            self.seq += 1

            # CRT
            duration = cyber.Time.now() - start
            logging.debug("Duration: %s ms", duration.to_sec() * 1000)

    def __create_serv(self):
        """
        Function creates necessary interfaces to request status and
        send parameters to the connected sensor from outside of the node
        """
        
        # CRT
        # initiate service with lambda bc normally takes no args
        # self.ummrr_node.create_service('sensor_status', None, None, lambda msg: self.__status_req(msg, self.con_sensor))
        # self.ummrr_node.create_service('sensor_parameter', None, None, lambda psg: self.__param_req(psg, self.con_sensor))
        # self.umrr_node.spin()?????

    def __inform_log(self):
        """
        Function prints some information about the connected Sensor like
        used software version, frame id and can spec
        """
        # create list for can messages
        self.__fields_from_spec()

        # CRT
        logging.info("Using frame_id: %s", self.frame_id)
        logging.info('The fields of the targets are: %s' % ''.join([name + ', ' for name in self.field_names]))

    def __fields_from_spec(self):
        """
        Function creates the message template from can spec
        """
        self.fields = []
        self.field_names = []
        self.byte_offset = 0

        for frame in self.con_sensor.target_serv.targetListSpec:
            elements = self.con_sensor.target_serv.targetListSpec[frame]["Elements"]
            for element in elements:                
                self.field_names.append(element)
                self.byte_offset += 4

    def __setup_sensor(self):
        
        # check if setup parameters are omitted:
        # CRT
        if hasattr(self.radar_conf, "antenna_mode") and not self.radar_conf.antenna_mode is None:
            
            # set antenna mode
            # CRT
            ant_dict = self.radar_conf.antenna_mode

            # send config to sensor
            # CRT
            self.con_sensor.parameter.sendRawParameter(ant_dict.section, ant_dict.parameter,
                                                       ant_dict.value, msgType="w")

        # CRT
        if hasattr(self.radar_conf, "center_frequency") and not self.radar_conf.center_frequency is None:
            # CRT
            freq_dict = self.radar_conf.center_frequency

            # CRT
            self.con_sensor.parameter.sendRawParameter(freq_dict.section, freq_dict.parameter,
                                                       freq_dict.value, msgType="w")
                                                       
    def __get_used_antenna(self):
        # because umr11 and 8f use different commands for antenna mode, check connected sensor
        if self.sensor_type == 1:
            self.con_sensor.parameter.sendRawParameter(3016, 1, msgType="r")
            res = self.__get_resp_value()
            #res = res["instructionsList"][0]['value']
            res = res['value']

            # CRT
            logging.info(''.join("Current Antenna Mode: " + str(res)))
        elif self.sensor_type == 0:
            self.con_sensor.parameter.sendRawParameter(3016, 0, msgType="r")
            res = self.__get_resp_value()
            #res = res["instructionsList"][0]['value']
            res = res['value']

            # CRT
            logging.info(''.join("Current Antenna Mode: " + str(res)))

    def __read_sw_version(self):
        """
        Function sends and reads messages from sensor
        """
        # create dictionary
        self.sw_dict = []
        for x in range(4, 13):
            self.con_sensor.status.sendRawStatus(3042, x)
            res = self.__get_resp_value()
            #res = res["instructionsList"][0]['value']
            res = res['value']
            self.sw_dict.append(res)

        # check if sensor responded to query
        if len(self.sw_dict) == 0:
            raise ValueError()
        else:
            sens_sw = ''.join([str(i) + '.' for i in self.sw_dict[2:5]])
            sens_sw = sens_sw[0:len(sens_sw)-1]

            # CRT
            logging.info('Sensor Software Version: %s', sens_sw)

            # send info to parameter Server
            # CRT
            if hasattr(self.radar_conf, "software_vers") and not self.radar_conf.software_vers is None:
                radar_conf.software_vers = sens_sw
            if self.sw_dict[5] > 0 or self.sw_dict[5]==0:
                # connected to UMRR-8f
                # CRT
                logging.info("Sensor Type: UMRR 8F")

                # send info to parameter Server
                # CRT
                if hasattr(self.radar_conf, "sensor_type") and not self.radar_conf.sensor_type is None:
                    # CRT
                    self.radar_conf.sensor_type = "UMRR_8F"

                self.sensor_type = 1

            else:
                # connected to UMRR-11
                # CRT
                logging.info("Sensor Type: UMRR 11")

                # send info to parameter Server
                # CRT
                if hasattr(self.radar_conf, "sensor_type") and not self.radar_conf.sensor_type is None:
                    # CRT
                    self.radar_conf.sensor_type = "UMRR_11"
                self.sensor_type = 0

    def __get_resp_value(self):
        """
        Function reads the sensor response from the response queue
        """
        try:
            resp = self.con_sensor.respserv.getMessage(timeout=2)
            # resp = resp["instructionsList"][0]['value']
        except queue.Empty:
            # CRT
            logging.error("Could not receive sensor response!")
            resp = 0
        return resp

    def __status_req(self, req, handle):
        """
        Function provides status service
        """
        # send request to sensor communication instance
        # handle.status.sendRawStatus(req.section, req.param)
        # develop
        # check if user omitted an empty string
        if req.type == "":
            handle.status.sendRawStatus(req.section, req.param)
        else:
            # string is not empty, set to value
            handle.status.sendRawStatus(req.section, req.param, statusType=req.type)

        resp = self.__get_resp_value()
        #resp = resp["instructionsList"][0]['value']
        resp = resp['value']
        # ans = ''.join("Sensor answered: " + str(resp))
        return str(resp)

    def __param_req(self, req, handle):
        """
        Function provides parameter service
        """
        handle.parameter.sendRawParameter(req.section, req.param, req.value)
        # resp = ''.join("Set Parameter " + str(req.param) + " to " + str(self.__get_resp_value()))
        resp = self.__get_resp_value()
        #resp = resp["instructionsList"][0]['value']
        resp = resp['value']
        return str(resp)

    @staticmethod
    def __create_pcl_msg(list_of_targets, seq):
        """
        Function fills the template with data coming from the sensor
        """

        header = Header()
        
        header.timestampt_sec = cyber.Time.now()
        header.radar_timestamp = cyber.Time.now()
        header.module_name = "Cartesian UMMR CAN Publisher"
        header.sequence_num = seq
        
        header.frame_id = self.radar_conf.frame_id        

        cloud_msg = pc_2.PointCloud()
        cloud_msg.header = header
        cloud_msg.frame_id = self.radar_conf.frame_id

        for target in list_of_targets:
            try:                                
                dist = target["Range"]
                azimuth_phi = target["Azimuth"] / 180.0 * pi
                elevation_theta = point["Elevation"] / 180.0 * pi
                x = dist * cos(elevation_theta) * cos(azimuth_phi)
                y = dist * cos(elevation_theta) * sin(azimuth_phi)
                z = dist * sin(elevation_theta)

                point = pc_2.PointXYZIT()
                point.x = x
                point.y = y
                point.z = z
                point.timestampt = cyber.Time.now()

                cloud_msg.point.append(point)
            except KeyError:
                # CRT
                logging.warning("Incomplete position data received. Skipping result.")
                
        
        return cloud_msg


if __name__ == '__main__':

    #CRT
    cyber.init() #TODO: I am not sure if this is necessary
    crt_umrr_publisher()

    #!!!!!
