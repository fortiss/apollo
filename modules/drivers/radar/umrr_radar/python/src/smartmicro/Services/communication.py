import threading
from enum import Enum, unique
from copy import deepcopy
from smartmicro.Helper.extendedThreadHelper.CanRecv import canReceive


@unique
class comDeviceTypes(Enum):
    """
    Enumeration of all communication device types that are supported by the communication module.
    """
    CAN = 1
    CAN_FD = 2
    ETHERNET = 3
    RS485 = 4


class Communication:
    """
    The communication class provides the interface to the user to allow for the usage of
    all available communication interfaces.

    The communication module provides different interfaces.
    * a can message based interface
    * debug streaming interface. (over ethernet, implicitly)

    The transmission of data is done in a synchronized way. Everything is transmitted before returning.
    The reception of data has to be implemented by the registration of services. The following services can be registered
    * canIdService
    * dbgService

    The registration of a can ID service enables the reception of can messages for a given can ID range. The registered
    service receive each can message as a single object in it receive queue.

    The registration of a dbg service enables the reception of data on a dedicated UDP port which is implicitly encoded
    by the port identifier which is requested from the registered service by the communication module.
    The data package that is being put into the receive queue by the communication module is always the data from a
    complete frame.

    """
    # ---------------------------------------------------------------------------------------------------------------- #
    # function: initialization                                                                                         #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __init__(self, _deviceDictList=None):
        """

        Parameters
        ----------
        _deviceDictList (list)
            a list of dictionaries. [{'deviceType', 'device'}]

        Examples
        --------
        Initialization example using the com device factory. This is using the LAWICEL can device.

        >>> canDevice = ComDeviceFactory.getDevice('CAN_LAWICEL')
        >>> comDeviceList = [{'deviceType': comDeviceTypes.CAN, 'device': canDevice}]
        >>> comModule = Communication(comDeviceList)

        """
        self.deviceDict = _deviceDictList
        self.dbgStreamerSockets = dict()
        self.udpStartPortDebugStreamer = 50000
        self.receiveThreadCan = dict()
        self.registeredCanServices = []
        self.eth_device_list = []
        self.send_mutex = threading.Lock()
        self.registered_response_services = []
        self.recordHelperQueue = None

        if _deviceDictList is not None:

            deviceTypeList = []
            # Creates a list with all deviceTypes from the deviceDictList
            for dev in _deviceDictList:
                deviceTypeList.append(dev['deviceType'])
            # check if each key is only present once
            for devType in comDeviceTypes:
                if deviceTypeList.count(devType) > 1 :
                    raise ValueError('Communication Module: One com device type is more than once in the deviceDictList'
                                     '. Type:{} comDeviceList:{}' .format(devType, self.deviceDict))

            # Init for each deviceType a receive thread
            for dev in _deviceDictList:
                if dev['deviceType'] is comDeviceTypes.CAN:
                    self.receiveThreadCan[comDeviceTypes.CAN] = canReceive(dev['device'])
                    self.receiveThreadCan[comDeviceTypes.CAN].start()
                else:
                    raise ValueError("Communication Module: unknown device")

    def get_devices_of_type(self, com_device_type):
        device_list = []
        for dev in self.deviceDict:
            if dev['deviceType'] is com_device_type:
                device_list.append(dev)
        return device_list

    def register_response_service(self, can_id):
        if can_id not in self.registered_response_services:
            self.registered_response_services.append(can_id)

    def add_eth_sensor_device_entry(self, serial_nr, device_id, udp_ip, udp_port ):

        device = dict()
        device['serial_nr'] = serial_nr
        device['deviceId'] = device_id
        device['udp_port'] = udp_port
        device['udp_addr'] = udp_ip

        self.eth_device_list.append(device)

    def enableSensorLogging(self, deviceType):
        """
        Parameters
        ----------
            deviceType: (comDeviceTypes) specifies which communication device is used obtain the log messages from

        Returns
        -------
        None
        """

        if deviceType == comDeviceTypes.CAN:
            raise IOError("a can device does not support log message output")

        com_receive = self.receiveThreadCan[deviceType]
        com_receive.enableLogMessageOutput()

    def disableSensorLogging(self, deviceType):
        """
        Parameters
        ----------
            deviceType: (comDeviceTypes) specifies which communication device is used obtain the log messages from

        Returns
        -------
        None
        """

        if deviceType == comDeviceTypes.CAN:
            raise IOError("a can device does not support log message output")

        com_receive = self.receiveThreadCan[deviceType]
        com_receive.disableLogMessageOutput()

    def registerSensorLogQueue(self, _queue, deviceType):
        """
        Parameters
        ----------
            _queue: this is the queue which will receive the log messages
            deviceType: (comDeviceTypes) specifies which communication device is used obtain the log messages from

        Returns
        -------
        None
        """

        if deviceType == comDeviceTypes.CAN:
            raise IOError("a can device does not support log message output")

        com_receive = self.receiveThreadCan[deviceType]
        com_receive.registerLogMessageQueue(_queue)

    def unregisterSensorLogQueue(self, deviceType):
        """
        Parameters
        ----------
            deviceType: (comDeviceTypes) specifies which communication device is used obtain the log messages from

        Returns
        -------
        None
        """

        if deviceType == comDeviceTypes.CAN:
            raise IOError("a can device does not support log message output")

        com_receive = self.receiveThreadCan[deviceType]
        com_receive.unregisterLogMessageQueue()

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: flushAllRegisterServices                                                                               #
    # ---------------------------------------------------------------------------------------------------------------- #
    def flushAllRegisterServices(self):
        """
        This flushes all registers can services.

        Returns
        -------
        None

        """
        # flush all registers can services
        for service in self.registeredCanServices:
            service.clearQueue()

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: registerCanIDService                                                                                   #
    # ---------------------------------------------------------------------------------------------------------------- #
    def registerCanIDService(self, service, canID, canIDRange=0, deviceType=comDeviceTypes.CAN):
        """
        This registers a can id service which provides a receive queue. After the registration the communication
        module puts any received message with the given can ids into the queue that is owned by the specified service.

        :param service: can id services that provides as interface a receive queue
        :param canID: can id that shall be registered with the provided services
        :param canIDRange: registers the service for the can id: (canID : canID + canIDRange), default is 0
        :param deviceType: (comDeviceTypes) specifies which communication device is used to transfer the given can messages.
        """
        # add the service to the register service list
        self.registeredCanServices.append(service)
        # get service queue
        serviceQueue = service.getRXQueue()

        # register the service queue
        self.receiveThreadCan[deviceType].registerQueue(serviceQueue, canID, canIDRange)

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: registerDebugStreamerService                                                                           #
    # ---------------------------------------------------------------------------------------------------------------- #
    def registerRecordHelper(self, recordHelper, deviceType=comDeviceTypes.CAN):
        """
        This registers a can recording helper which provides a receive queue. After the registration the communication
        module puts any received message into the queue that is owned by the specified helper.


        :param recordHelper: canRecordingHelper. instance of can recording helper class
        :param deviceType: comDeviceTypes
        """
        # get recording queue
        self.recordHelperQueue = recordHelper.getRecordQueue()
        # register recordQueue
        self.receiveThreadCan[deviceType].registerRecordingQueue(self.recordHelperQueue)

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: startDebugStreamerService                                                                              #
    # ---------------------------------------------------------------------------------------------------------------- #
    def startDebugStreamerService(self, dbgService):
        """
        Starts the thread that was created by registering it with the communication module.
        This thread cannot be stopped. It can only be suspended and resumed using the following functions:
        * :func:`suspendDebugStreamerService`
        * :func:`resumeDebugStreamerService`

        Parameters
        ----------
            dbgService

        """
        portIdentifier = dbgService.getPortIdentifier()
        self.dbgStreamerSockets[portIdentifier.name].start()

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: suspendDebugStreamerService                                                                            #
    # ---------------------------------------------------------------------------------------------------------------- #
    def suspendDebugStreamerService(self, dbgService):
        """
        Suspends the thread that was created on the registration of the passed dbgService. This means the reception
        of data is stopped. No data will be put into the receive queue of the passed service.

        Parameters
        ----------
        dbgService

        """
        portIdentifier = dbgService.getPortIdentifier()
        self.dbgStreamerSockets[portIdentifier.name].suspend()

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: resumeDebugStreamerService                                                                             #
    # ---------------------------------------------------------------------------------------------------------------- #
    def resumeDebugStreamerService(self, dbgService):
        """
        Resumes the thread that puts puts the received debug data (port data) into the rx queue.

        Parameters
        ----------
            dbgService

        """
        portIdentifier = dbgService.getPortIdentifier()
        self.dbgStreamerSockets[portIdentifier.name].resume()

    def shutDownDebugStreamerService(self, dbgService):
        """
        Resumes the thread that puts puts the received debug data (port data) into the rx queue.

        Parameters
        ----------
            dbgService

        """
        portIdentifier = dbgService.getPortIdentifier()
        self.dbgStreamerSockets[portIdentifier.name].shutDown()

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: suspendCommunicationDevice                                                                             #
    # ---------------------------------------------------------------------------------------------------------------- #
    def suspendCommunicationDevice(self, deviceType):
        """
        Stops putting data into the registered service queues for the specified communication device type

        Parameters
        ----------
            deviceType

        """
        # Suspends the receiveThread
        self.receiveThreadCan[deviceType].suspend()

    def suspendAllCommunicationDevices(self):
        """
        Stops putting data into the registered service queues for alll registered communication device type
        """
        for key in self.receiveThreadCan:
            self.receiveThreadCan[key].suspend()

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: resumeCommunicationDevice                                                                              #
    # ---------------------------------------------------------------------------------------------------------------- #
    def resumeCommunicationDevice(self, deviceType):
        """
        Resumes putting data from the specified communication device type into the registered service queues

        :param deviceType:
        :return:
        """
        # Resumes the receiveThread
        self.receiveThreadCan[deviceType].resume()

    def shutDownCommunicationDevice(self, deviceType):
        """
        Shut down putting data from the specified communication device type into the registered service queues

        :param deviceType:
        :return:
        """
        # Shut down the received Thread
        self.receiveThreadCan[deviceType].shutDown()
        self.receiveThreadCan[deviceType].join()

    def shutDownAllCommunicationDevices(self):
        """
           Shut down putting data from all registered communication device type into the registered service queues
        """
        for key in self.receiveThreadCan:
            self.receiveThreadCan[key].shutDown()
            self.receiveThreadCan[key].join()

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: __getComDeviceByType                                                                                   #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __getComDeviceByType(self, deviceType):
        """

        :param deviceType:
        """
        dictDev = next(item for item in self.deviceDict if item['deviceType'] == deviceType)
        comDevice = dictDev['device']

        return comDevice

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: close                                                                                                  #
    # ---------------------------------------------------------------------------------------------------------------- #
    def close(self):
        """
        Closes all communication devices that where registered at instantiation time

        Returns
        -------
        errorList   : list

        """
        errorList = list()
        for dev in self.deviceDict:
            try:
                dev['device'].close()
            except Exception as e:
                # add the error information to the list
                errorList.append(e)

        return errorList

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: sendCanMessages                                                                                        #
    # ---------------------------------------------------------------------------------------------------------------- #
    def sendCanMessages(self, canMessageList, deviceType=comDeviceTypes.CAN, channelIndex=1, deviceId=0):
        """
        This is a function to send a list of can messages at once. The device type parameter decides which registered
        device. This interface is a can message interface only. The lower levels are dealing how to transfer these
        type of message over the chosen communication channel (deviceType)

        :param canMessageList: (list of dict) can messages in the following format
        :param deviceType: (comDeviceTypes) specifies which communication device is used to transfer the given can messages.
        :param channelIndex: specifies the channel index
        :param deviceId: specifies the ID of the used device

        Raises
        -------
        LookupError
            if the given device type is not found within the registered communication devices
        ValueError
            if the length of a data package for a can message exceeds 8 bytes
        """

        # if queue object was passed to the function, write can messages that are send out also to this queue
        if self.recordHelperQueue is not None:
            for msg in canMessageList:
                msg["channelIndex"] = channelIndex
                msg["canID"]        = msg["canId"]
                msg["dlc"]          = len(msg['data'])
                # throw an exception if the data is too long
                if len(msg['data']) > 8:
                    raise ValueError("Can data size must not exceed 8 bytes")
                self.recordHelperQueue.put(deepcopy(msg))

        with self.send_mutex:
            sendComDevice = None

            # look for the deviceTyp in the deviceDict
            for dev in self.deviceDict:
                if dev['deviceType'] is deviceType:
                    sendComDevice = dev['device']

            # throw an exception if no device was found
            if sendComDevice is None:
                raise LookupError("Specified communication device not found")

            ## TODO FIXME ==> generic solution. Interface improvement of lower layer

            # send the messageList
            for msg in canMessageList:
                # throw an exception if the data is too long
                if len(msg['data']) > 8:
                    raise ValueError("Can data size must not exceed 8 bytes")
                # send the can message
                sendComDevice.sendData(msg['canId'], len(msg['data']), msg['data'], channelIndex=channelIndex)
