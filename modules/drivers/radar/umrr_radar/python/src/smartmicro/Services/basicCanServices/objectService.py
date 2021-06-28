import json
import queue

from copy import deepcopy
from smartmicro.Services.basicCanServices.canService import CanIDService


class CanIDServiceObjectList(CanIDService):
    """
    The current class inidicates the decoding of target messages in general. It provides the possibility to decode every
    object message from header to single frame messages.
    """

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: initialization                                                                                         #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __init__(self, canSpecFile):
        """
        The current function initializes target can ID service. Therefore the decoding style of the message will be
        required and an nput queue will be configured.

        Parameters
        ----------
        canSpecFile : json-File
            The json file has to be configured to describe the setup of can message designed for objects
        """

        self.recvQueue = queue.Queue()

        with open(canSpecFile) as json_data:
            self.objectListSpec = json.load(json_data)


    # ---------------------------------------------------------------------------------------------------------------- #
    # function: getObjectList                                                                                          #
    # ---------------------------------------------------------------------------------------------------------------- #
    def getObjectList(self, timeout=None):
        """
        The function will be called fro the outside to get the objects list of the current cycle.

        Returns
        -------
        objects : list of objects(dict)
            The return value is a list of objects. The single object will be designed as dictionary like the json file.
        """

        ## wait for a header message
        msg = self.recvQueue.get(block=True, timeout=timeout)

        ## iterating until msg taken from the que is the one with can id that relates to objects 
        while msg['canID'] != self.objectListSpec['header']['CanId']:
            msg = self.recvQueue.get()

        headerSpec = self.objectListSpec['header']['Elements']

        ## we are getting here dictionary
        header = self.__decodeMsgElements(msg['data'], headerSpec)

        ## wait for the delivered number of
        objects = []
        for i in range(0, int(header['Number_Of_Objects'])):

            _object = self.__decodeObjectMessage(self.recvQueue.get()['data'], header['Object_data0_format'])
            _object.update(header)

            objects.append(deepcopy(_object))

        return deepcopy(objects)


    # ---------------------------------------------------------------------------------------------------------------- #
    # function: __decodeObjectMessage                                                                                  #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __decodeObjectMessage(self, msg, format):
        """
        The current function will deal with the multiframe state of the can message. It will call the correct decoding
        style.

        Parameters
        ----------
        msg : binary
            The message is the binary coded style of the data

        Returns
        -------
        object : dict
            The return value is the decoded object from the message
        """

        if format == 3:
            frame = 'format0'
        else: # else it should be 4
            frame = 'format1'

        return self.__decodeMsgElements(msg, self.objectListSpec[frame]['Elements'])

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: __decodeMsgElements                                                                                    #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __decodeMsgElements(self, msg, decodingDict):
        """
        The function will deal with the single decoding of every information listed in the json file for a given
        message.

        Parameters
        ----------
        msg             : binary
            The message will be a binary format information which has to be decoded

        decodingDict    : dict
            The decoding dict includes all rules to extract information from the current message

        Returns
        -------
        objectDict      : dict
            The object dictionary includes all decoded information
        """

        objectDict = dict()

        for decRule in decodingDict:
            objectDict[decRule] = self.decode(msg, decodingDict[decRule])

        return objectDict

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: clearQueue                                                                                             #
    # ---------------------------------------------------------------------------------------------------------------- #
    def clearQueue(self):
        """
        Clear all objects in the queue.

        Returns
        -------
        None
        """
        while self.isEmpty() == False:
            self.getObjectList(0.01)
