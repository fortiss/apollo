import socket
import struct
import sys
from smartmicro.HardwareLayer.drivers.canDrivers.canInterface import CanFrameFormat, CanInterfaceError, CanInterface


class CanSocketError(Exception):
    pass


class CanSocket(CanInterface):
    """
    The can interface is used in any can driver class.
    """

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: __init__                                                                                               #
    # ---------------------------------------------------------------------------------------------------------------- #
    #def __init__(self):
    def __init__(self,interface):
        self.sock = socket.socket(socket.PF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
        #interface = "vcan1"
        self.interface = interface
        self.sock.bind((self.interface,))
        #print(self.interface)
        # try:
            #self.sock.bind((interface,))
            # self.sock.bind((self.interface,))
        # except OSError:
            # sys.stderr.write("Could not bind to interface '%s'\n" % interface)
            # do something about the error...

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: initChannel                                                                                            #
    # ---------------------------------------------------------------------------------------------------------------- #
    def initChannel(self, bitRate, channelIndex=1):
        """
        Initializes the can driver and configures the can bus.

        Parameters
        ----------
        bitRate         : int
            The channel bit rate in kbit/s
        channelIndex    : int
            Specifies the channel index

        Returns
        -------

        """
        pass

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: sendData                                                                                               #
    # ---------------------------------------------------------------------------------------------------------------- #
    def sendData(self, identifier, dlc, data, frameFormat=CanFrameFormat.std, channelIndex=1):
        """
        Send a can message.

        Parameters
        ----------
        identifier      : int
            Can message identifier
        dlc             : int
            Can message data length
        data            : list
            Can message data
        frameFormat     : instance of can frame format
            Specifies the can frame format (standard or extended or canFD
        channelIndex    : int
            Specifies the can channel number

        Returns
        -------

        """
        fmt = "<IB3x8s"
        canId = identifier
        if frameFormat == CanFrameFormat.xtd:
            canId = identifier | socket.CAN_EFF_FLAG
        elif frameFormat == CanFrameFormat.fd:
            raise CanSocketError('CanSocket is not supported can FD')

        can_pkt = struct.pack(fmt, canId, dlc, data)

        self.sock.send(can_pkt)

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: receiveData                                                                                            #
    # ---------------------------------------------------------------------------------------------------------------- #
    def receiveData(self, channelIndex=1):
        """
        Returns the received can messages.

        Parameters
        ----------
        channelIndex    : int
            Specifies the can channel number

        Returns
        -------
        retCanMessage   : list or None
            The received can message is returned as a list [identifier, data length, data]. If no can message was \
            received, None is returned.

        """
        fmt = "<IB3x8s"
        canPkt = self.sock.recv(16)

        canId, length, data = struct.unpack(fmt, canPkt)
        canId &= socket.CAN_EFF_MASK
        data = data[:length]

        canMessage = [canId, length, bytearray(data), channelIndex]

        return canMessage


    # ---------------------------------------------------------------------------------------------------------------- #
    # function: status                                                                                                 #
    # ---------------------------------------------------------------------------------------------------------------- #
    def status(self, channelIndex=1):
        """
        Print the can bus status.

        Parameters
        ----------
        channelIndex    : int
            Specifies the can channel number

        Returns
        -------

        """
        raise CanInterfaceError('status function is not implemented')

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: changeBitRate                                                                                          #
    # ---------------------------------------------------------------------------------------------------------------- #
    def changeBitRate(self, bitRate, channelIndex=1):
        """
        This function will be change the channel bit rate.

        Parameters
        ----------
        bitRate         : int
            The channel bit rate in kbit/s
        channelIndex    : int
            Specifies the can channel number

        Returns
        -------

        """
        raise CanInterfaceError('changeBitRate function is not implemented')

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: close                                                                                                  #
    # ---------------------------------------------------------------------------------------------------------------- #
    def close(self):
        """
        Close the can driver.

        Returns
        -------

        """
        self.sock.close()
