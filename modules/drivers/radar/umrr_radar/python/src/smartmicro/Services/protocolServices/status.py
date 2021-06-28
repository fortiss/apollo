from smartmicro.Protocols.cmdStatParam.cspCommon import cspCommon
from smartmicro.Protocols.uat.uatMain import MessageType, ParameterType, DataFormat
from smartmicro.Services.communication import comDeviceTypes


class Status:

    def __init__(self, _comModule, statusFileList=None, rootDir=None, uatVersion=1, _comDeviceType=comDeviceTypes.CAN):


        """
        The init requires a communication module instance since it requires a means to read status values

        Status
        ----------
        _comModule          : instance of communication module
            internal used instance to send messages
        statusFileList      : list
            contains a file that contains a list of status files.
        rootDir             : str
            this is the start directory where the status module searches for .status files
        uatVersion          : integer
            version of used uat version, default version 1
        _comDeviceType      : comDeviceTypes
            specifies with which device the status is requested

        Raises
        ------
        ValueError
            if rootDir and statusFileList are set
        """
        self.comDeviceType = _comDeviceType
        # copy instance of communication module
        self.comModule  = _comModule
        # set empty dictionary for status list
        self.statusValues = dict()
        # set uat version
        self.uatVersion = uatVersion
        # check if file with status are available
        if rootDir is not None and statusFileList is not None:
            raise ValueError("Either use root Dir or a status file list")

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: __sendRawParameter                                                                                     #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __sendRawParameter(self, param , canChannelIndex=1):
        """
        The function calls the function to send the messages.

        Parameters
        ----------
        param   : dict
            dictionary to be send
        canChannelIndex : int
            specifies the can channel index

        Returns
        -------

        """
        cspCommon.sendRawParameter(param, comModule=self.comModule, canId=0x3fb, deviceType=self.comDeviceType,
                                   canChannelIndex=canChannelIndex)

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: sendRawStatus                                                                                          #
    # ---------------------------------------------------------------------------------------------------------------- #
    def sendRawStatus(self, section, parameterNr, devId=0, statusType="integer"):

        param = None

        if self.uatVersion == 4:
            # provide parameter dictionary
            param = self.__provideStatusDictVersion4(section, parameterNr, devId, statusType)
        elif self.uatVersion == 1:
            # provide parameter dictionary
            param = self.__provideStatusDictVersion1(section, parameterNr, devId, statusType)
        else:
            raise TypeError("unsupported UAT Version selected in Status class")
            
        self.__sendRawParameter(param, canChannelIndex=1)

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: __provideStatusDictVersion4                                                                            #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __provideStatusDictVersion4(self, section, parameterNr, devId, statusType):
        # derive parameter type
        if statusType == "float":
            statusType = DataFormat.FLOAT_IEEE
        else:
            statusType = DataFormat.INTEGER
        # create parameter dictionary
        param = dict()
        # fill base information
        param['UAT-ID']                 = section
        param['uatVersion']             = 4
        param['deviceId']               = devId
        param['numberOfInstructions']   = 1
        # fill parameter instruction
        param['instructionsList']                       = [dict()] * param['numberOfInstructions']
        param['instructionsList'][0]['UAT-ID']          = 0
        param['instructionsList'][0]['dataFormat']      = statusType
        param['instructionsList'][0]['messageType']     = MessageType.STATUS
        param['instructionsList'][0]['parameterNumber'] = parameterNr
        param['instructionsList'][0]['value']           = 0
        param['instructionsList'][0]['dim0']            = 0
        param['instructionsList'][0]['dim1']            = 0
        param['instructionsList'][0]['instructionIdx']            = 0

        return param

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: __provideStatusDictVersion1                                                                            #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __provideStatusDictVersion1(self, section, parameterNr, devId, statusType):
        # derive parameter type
        if statusType == "float":
            statusType = DataFormat.FLOAT_IEEE
            paramType = ParameterType.IEEE_FLOAT_READ
        else:
            statusType = DataFormat.INTEGER
            paramType = ParameterType.INTEGER_READ
        # create parameter dictionary
        param = dict()
        # fill base information
        param['UAT-ID']                 = section
        param['uatVersion']             = 1
        param['deviceId']               = devId
        # fill parameter instruction
        #param['UAT-ID']          = 0
        param['parameterNumber'] = parameterNr
        param['parameterType'] = paramType
        param['value']           = 0

        return param
