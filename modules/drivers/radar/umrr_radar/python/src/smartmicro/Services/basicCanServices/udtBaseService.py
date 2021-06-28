import time
import queue
import struct

from enum import Enum, unique

from smartmicro.Helper.basicThreadHelper.threadHelper import ThreadHelper
from smartmicro.Services.basicCanServices.canService import CanIDService
from smartmicro.Services.basicCanServices.uatResponseService import uatResponseService


@unique
class udtRespService(Enum):
    USER_SERVICE = 0
    UAT_RESPONSE = 1

class udtService(CanIDService, ThreadHelper):
    # ---------------------------------------------------------------------------------------------------------------- #
    # function: initialization                                                                                         #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __init__(self):
        """
        The function provides all necessary variables and instances to deal with the udt service.
        """
        # init parent class : ThreadHelper
        ThreadHelper.__init__(self)
        # init parent class : CanIDService
        CanIDService.__init__(self)
        # provide receive queue
        self.recvQueue           = queue.Queue()
        # provide empty dictionary for sub services
        self.subServiceDict      = dict()
        # provide empty dictionary for sub service queues
        self.subServiceQueueDict = dict()
        # register subservices
        self.__regSubServices()
        # register queues for sub-services
        self.__regSubServiceQueues()
        # start thread
        self.start()

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: __regSubServices                                                                                       #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __regSubServices(self):
        """
        The function registers all necessary sub services for further processes.

        Returns
        -------

        """
        # register uat response service
        self.subServiceDict[udtRespService.UAT_RESPONSE] = uatResponseService()

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: __regSubServiceQueues                                                                                  #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __regSubServiceQueues(self):
        """
        The function registers all available queues for the sub-service.

        Returns
        -------

        """
        # run through all sub-services
        for key in self.subServiceDict.keys():
            # get all identifier
            idList = self.subServiceDict[key].getUdtIdentifier()
            # run through all identifier
            for subServiceId in idList:
                # register the queue
                self.subServiceQueueDict[str(subServiceId)] = \
                    self.subServiceDict[key].getRXQueue()

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: clearSubServiceQueue                                                                                   #
    # ---------------------------------------------------------------------------------------------------------------- #
    def clearSubServiceQueue(self, subService=udtRespService.UAT_RESPONSE):
        """
        The function clears the queue of internal used sub services.

        Parameters
        ----------
        subService  : enumerate
            identifier of the sub-service

        Returns
        -------

        """
        # clear current sub service queue
        self.subServiceDict[subService].clearQueue()

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: getMessage                                                                                             #
    # ---------------------------------------------------------------------------------------------------------------- #
    def getMessage(self, respId=udtRespService.UAT_RESPONSE, timeout=2):
        """
        The function returns the response of a dedicated sub-service of the udt service.

        Parameters
        ----------
        respId  : enumerate
            identifier of the sub-service
        timeout : integer
            timeout in [s]

        Returns
        -------
        response    : dict
            response of the used id service
        """
        return self.subServiceDict[respId].getMessage(timeout)

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: run                                                                                                    #
    # ---------------------------------------------------------------------------------------------------------------- #
    def run(self):
        """
        The function sorts all received data into the correct queue of the sub-service.

        Returns
        -------

        """
        # run as long as thread is not closed
        while self.shutDownBool is not True:
            # wait until message available
            while self.recvQueue.empty():
                # wait for 2 ms
                time.sleep(0.002)
            # get current data
            msg = self.recvQueue.get()
            # decode identifier
            index = struct.unpack('<H', msg["data"][0:2])[0]
            # check if identifier is available
            if str(index) in self.subServiceQueueDict.keys():
                # put data into queue
                self.subServiceQueueDict[str(index)].put(msg)

