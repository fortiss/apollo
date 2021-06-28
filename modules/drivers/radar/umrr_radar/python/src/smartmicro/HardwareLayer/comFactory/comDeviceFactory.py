from smartmicro.HardwareLayer.drivers.canDrivers.canSocket import CanSocket

class ComDeviceFactory:

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: _createCanSocket                                                                                       #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    #def _createCanSocket():
    def _createCanSocket(usedSocked):
        """

        Returns
        -------
        device        : instance of can socket
            The can lawicel device handle.
        """
        #device = CanSocket()
        device = CanSocket(usedSocked)
        return device

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: getDevice                                                                                              #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def getDevice(deviceName,usedSocked, deviceType=None, channelConfig=None, serialPort=None, ip=None, port=None):
        """
        This function initializes the communication interface and returns the device handle.

        Returns
        -------
        device  : instance of device
            The device handle.

        """
        device = None

        if deviceName == 'CAN_SOCKET':
            #device = ComDeviceFactory._createCanSocket()
            device = ComDeviceFactory._createCanSocket(usedSocked)

        return device
