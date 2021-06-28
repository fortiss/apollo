import queue
import struct

from smartmicro.Protocols.udt.udtUatResponseV4 import UATv4Response
#The PEAK PC-CAN PCI card installed in fortiss car PC1 returns a UDT type 17000 version 2, not version 5!
#This corresponds to to UATv1
from smartmicro.Protocols.udt.udtUatResponseV1 import UATv1Response
from smartmicro.Services.basicCanServices.canService import CanIDService


class uatResponseService(CanIDService):
    # ---------------------------------------------------------------------------------------------------------------- #
    # function: initialization                                                                                         #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __init__(self):
        """
        The function provides all necessary variables and instances to deal with the udt sub-service uat responses.
        """
        # init super class
        CanIDService.__init__(self)
        # provide receive queue
        self.recvQueue = queue.Queue()
        # provide decode dictionary
        self.decDict   = dict()
        # provide udt identifier referring to uat response service
        self.uatRespIdList = [17000, 17001, 17002, 17003, 17004, 17005, 17006, 17007, 17008, 17009,
                              17010, 17011, 17012, 17013, 17014, 17015, 17016, 17017, 17018]
        # set decode functions
        self.__regDecodeFunctions()

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: __regDecodeFunctions                                                                                   #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __regDecodeFunctions(self):
        """
        The function registers all decode functions into one dictionary.

        Returns
        -------

        """
        # register decode functions

        #if the response version is UDT type 17000 version 2, use UATv1
        #The below response returns data : dict
        #A dict with the keys: 'UDT-Index', 'version', 'UAT-ID', 'result',
        #'deviceId' 'parameterNumber', 'parameterType', 'counter' and 'value'.
        self.decDict["2"] = UATv1Response.decode

        #if the response version is UDT type 17000 version 5, use UATv4
        #The below response returns data : dict
        #A dict with the keys: 'UDT-Index', 'version', 'UAT-ID', 'result',
        #'deviceId' 'parameterNumber',  'messageType', 'dataFormat',
        #'counter', 'numberOfInstructions' 'dim0', 'dim1' and 'value'.
        self.decDict["5"] = UATv4Response.decode

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: getUdtIdentifier                                                                                       #
    # ---------------------------------------------------------------------------------------------------------------- #
    def getUdtIdentifier(self):
        """
        The function returns a list of used udt identifier for this response service.

        Returns
        -------
        uatRespIdList   : list
            list of used uat response identifier
        """
        return self.uatRespIdList

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: getMessage                                                                                             #
    # ---------------------------------------------------------------------------------------------------------------- #
    def getMessage(self, timeout=None):
        """
        The function decodes received uat responses

        Parameters
        ----------
        timeout : integer
            timeout in [s]

        Returns
        -------

        """
        # wait for header
        header               = self.__waitForHeader(timeout)
        # decode uat response version
        msgList, respVersion = self.__uatVersionCtrl(header, timeout)
        # decode uat response
        decResp              = self.decDict[str(respVersion)](msgList)

        return decResp

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: __waitForHeader                                                                                        #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __waitForHeader(self, timeout=None):
        """
        The function waits for the header of the response.

        Parameters
        ----------
        timeout : integer
            timeout in [s]

        Returns
        -------
        header  : bytearray
            header message of the response
        """
        # init default udt index
        udtIndex = 0
        # set default header
        header   = bytearray(8)
        # run as long as header is not found
        while udtIndex != 17000:
            # get header from queue
            header   = self.recvQueue.get(block=True, timeout=timeout)['data']
            # extract udt index
            udtIndex = struct.unpack('<H', header[0:2])[0]

        return header

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: __waitForHeader                                                                                        #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __uatVersionCtrl(self, header, timeout=None):
        """
        The function decodes the corresponding uat version for further response decoding. Additional the corresponding
        messages for the response will be collected.

        Parameters
        ----------
        header  : bytearray
            header message used to determine next steps
        timeout : integer
            timeout in [s]

        Returns
        -------
        msgList : list
            list of bytearrays
        uatRespVersion  : integer
            current version of uat response
        """
        # decode uat response version
        uatRespVersion = struct.unpack("<B", header[2:3])[0]
        if uatRespVersion == 2:
           #Versions 1 to 3 support only 1 instruction per block
           #and expect a msgList of 5 byte arrays (1 header + 4 more messages)
           remaining_datapackages = 4
        elif uatRespVersion == 5:
            numberOfInstructions = header[5]
            # (Number of instructions * 3) data packages
            remaining_datapackages = numberOfInstructions * 3
        else:
            raise TypeError("unsupported UDT-UAT response index received")
        # provide list of response messages
        msgList = [header]
        for nsgIdx in range(0, remaining_datapackages):
            msgList.append(self.recvQueue.get(block=True, timeout=timeout)['data'])

        return msgList, uatRespVersion

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: clearQueue                                                                                             #
    # ---------------------------------------------------------------------------------------------------------------- #
    def clearQueue(self):
        """
        Flushes the recvQueue.

        Returns
        -------
        None
        """
        while self.isEmpty() is False:
            self.getMessage()
