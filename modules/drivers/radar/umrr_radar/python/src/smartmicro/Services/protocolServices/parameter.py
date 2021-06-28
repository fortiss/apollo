import logging
from smartmicro.Protocols.cmdStatParam.cspCommon import cspCommon, errorFunctionID
from smartmicro.Protocols.cmdStatParam.cspSendVersion1 import cspSendVersion1
from smartmicro.Protocols.cmdStatParam.cspSendVersion2 import cspSendVersion2
from smartmicro.Protocols.uat.uatMain import MessageType, ParameterType, DataFormat
from smartmicro.Services.communication import comDeviceTypes


class Parameter:
    """
    The parameter module provides the functionality to write Parameter via a communication link to a destination.
    """

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: __init__                                                                                               #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __init__(self, _comModule, parameterFileList=None, rootDir=None, uatVersion=1,
                 _comDeviceType=comDeviceTypes.CAN):
        """
        The init requires a communication module instance since it requires a means to transfer parameters.

        Parameters
        ----------
        _comModule          : instance of communication module
            internal used instance to send messages
        parameterFileList   : list
            contains a file that contains a list of parameter files. This parameter overrules the root dir parameter
        rootDir             : string
            relative direction of param file
        uatVersion          : integer
            version of used uat version, default version 1
        _comDeviceType      : comDeviceTypes
            specifies with which device the status is requested
        """
        self.com_device_type = _comDeviceType
        # copy instance of communication module
        self.comModule       = _comModule
        # set empty dictionary for parameter list
        self.parameters      = dict()
        # define default error function dictionary
        self.errorFuncDict   = dict()
        # set uat version
        self.uatVersion      = uatVersion
        # check whether root direction or param list file are available
        if rootDir is not None and parameterFileList is not None:
            raise ValueError("Either use root Dir or a parameterFile list")
        # derive parameter structure from given file
        cspCommon.initializeValueDict(self.parameters, parameterFileList, rootDir, fileExt="param")

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: _sendRawParameter                                                                                      #
    # ---------------------------------------------------------------------------------------------------------------- #
    def _sendRawParameter(self, param, canChannelIndex=1, errorHandler=dict()):
        """
        The function calls the function to send the messages.

        Parameters
        ----------
        param       : dict
            dictionary to be send
        canChannelIndex : int
            specifies the can channel index
        errorHandler    : dict
            generates defined errors at a value not equal to zero

        Returns
        -------

        """
        cspCommon.sendRawParameter(param, comModule=self.comModule, canId=0x3fb, deviceType=self.com_device_type,
                                   canChannelIndex=canChannelIndex, errorHandler=errorHandler)

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: sendRawParameter                                                                                       #
    # ---------------------------------------------------------------------------------------------------------------- #
    def sendRawParameter(self, section, parameterNr, value=0, devId=0, paramType="integer", msgType="rw"):

        param = None

        if self.uatVersion == 4:
            # provide parameter dictionary
            param = self.__provideParamDictVersion4(section, parameterNr, value, devId, paramType, msgType)
        elif self.uatVersion == 1:
            # provide parameter dictionary
            param = self.__provideParamDictVersion1(section, parameterNr, value, devId, paramType, msgType)
        else:
            raise TypeError("unsupported UAT Version selected in Parameter class")
            
        self._sendRawParameter(param, canChannelIndex=1, errorHandler=self.errorFuncDict)

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: __provideParamDictVersion4                                                                             #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __provideParamDictVersion4(self, section, parameterNr, value, devId, paramType, msgType):
        # derive parameter type
        if paramType == "float":
            paramType = DataFormat.FLOAT_IEEE
        else:
            paramType = DataFormat.INTEGER

        if "rw" == msgType:
            msgAction = MessageType.PARAMETER_WRITE_READ
        elif "r" == msgType:
            msgAction = MessageType.PARAMETER_READ
        elif "w" == msgType:
            msgAction = MessageType.PARAMETER_WRITE
        else:
            raise BaseException("ERROR: Current action not possible!")

        # create parameter dictionary
        param = dict()
        # fill base information
        param['UAT-ID'] = section
        param['uatVersion'] = 4
        param['deviceId'] = devId
        param['numberOfInstructions'] = 1
        # fill parameter instruction
        param['instructionsList'] = [dict()] * param['numberOfInstructions']
        param['instructionsList'][0]['UAT-ID'] = 0
        param['instructionsList'][0]['dataFormat'] = paramType
        param['instructionsList'][0]['messageType'] = msgAction
        param['instructionsList'][0]['parameterNumber'] = parameterNr
        param['instructionsList'][0]['value'] = value
        param['instructionsList'][0]['dim0'] = 0
        param['instructionsList'][0]['dim1'] = 0
        param['instructionsList'][0]['instructionIdx'] = 0

        return param

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: __provideParamDictVersion1
    # The param dict for uatV1 can be found in Protocols.uat.uatV1.py                                                                            #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __provideParamDictVersion1(self, section, parameterNr, value, devId, paramType, msgType):
        # derive parameter type
        if paramType == "float":
            #paramType = DataFormat.FLOAT_IEEE
            if "rw" == msgType:
                paramType = ParameterType.IEEE_FLOAT_RW
            elif "r" == msgType:
                paramType = ParameterType.IEEE_FLOAT_READ
            elif "w" == msgType:
                paramType = ParameterType.IEEE_FLOAT_WRITE
            else:
                raise BaseException("ERROR: Current action not possible!")
        elif paramType == "integer":
            #paramType = DataFormat.INTEGER
            if "rw" == msgType:
                paramType = ParameterType.INTEGER_RW
            elif "r" == msgType:
                paramType = ParameterType.INTEGER_READ
            elif "w" == msgType:
                  paramType = ParameterType.INTEGER_WRITE
            else:
                  raise BaseException("ERROR: Current action not possible!")

        #if "rw" == msgType:
        #    msgAction = MessageType.PARAMETER_WRITE_READ
        #elif "r" == msgType:
        #     msgAction = MessageType.PARAMETER_READ
        #elif "w" == msgType:
        #    msgAction = MessageType.PARAMETER_WRITE
        #else:
        #    raise BaseException("ERROR: Current action not possible!")

        # create parameter dictionary
        param = dict()
        # fill base information
        param['UAT-ID'] = section
        param['uatVersion'] = 1
        param['deviceId'] = devId
        # fill parameter instruction
        #param['UAT-ID'] = 0
        param['parameterNumber'] = parameterNr
        param['parameterType'] = paramType
        param['value'] = value

        return param
