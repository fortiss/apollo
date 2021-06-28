import struct
import crc16
from smartmicro.Protocols.uat.uatMain import DataFormat, MessageType
from smartmicro.Protocols.udt.udtUatResponseMain import UAT_RespErrorCode


class UATv4Response:
    """
    The class provides encode and decode functions of UDT type 17000 version 5 which is an UAT Response Message for UAT
    message version 4. In UDT type 17000 version 5 several instructions can be sent in one block. Each instruction
    consists of 2 messages. Example: 3 instructions are to be sent in one block. The value of the number of instructions
    would thus be 3 and the following messages would be transmitted:
    * 1 x header + 3 * 3 (messages for the 3 instructions) = 10 messages
    * 1 x header + 3 * N. N = number of instructions.
    """

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: __init__                                                                                               #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __init__(self):
        self.data = dict()
        self.data['UDT-Index'] = 17000
        self.data['version'] = 5
        self.data['deviceId'] = 0
        self.data['numberOfInstructions'] = 1
        self.data['instructionsList'] = [dict()] * self.data['numberOfInstructions']
        self.data['instructionsList'][0]['UAT-ID'] = 0
        self.data['instructionsList'][0]['result'] = UAT_RespErrorCode.SUCCESS
        self.data['instructionsList'][0]['dataFormat'] = DataFormat.DEFAULT
        self.data['instructionsList'][0]['messageType'] = MessageType.DEFAULT
        self.data['instructionsList'][0]['parameterNumber'] = 0
        self.data['instructionsList'][0]['counter'] = 0
        self.data['instructionsList'][0]['value'] = 0
        self.data['instructionsList'][0]['dim0'] = 0
        self.data['instructionsList'][0]['dim1'] = 0

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: getDataPackage                                                                                         #
    # ---------------------------------------------------------------------------------------------------------------- #
    def getDataPackage(self):
        """
        Returns a dict with default values.

        Returns
        -------
        data        : dict
            the dictionary with the data information
        """
        return self.data

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: encodeHeaderMessage                                                                                    #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def encodeHeaderMessage(UDT_Index, version, deviceId, NumberOfInstructions, crcCalcDataArray):
        """
        The function encodes the arguments to a byte array with 8 bytes. The header message is defined:

        +--------------+---------------------------+
        | Byte 0       |                           |
        +--------------+ UDT-Index                 |
        | Byte 1       |                           |
        +--------------+---------------------------+
        | Byte 2       |                           |
        +--------------+ Version                   |
        | Byte 3       |                           |
        +--------------+---------------------------+
        | Byte 4       | Device ID                 |
        +--------------+---------------------------+
        | Byte 5       | Number of instructions    |
        +--------------+---------------------------+
        | Byte 6       |                           |
        +--------------+ crc16 value               |
        | Byte 7       |                           |
        +--------------+---------------------------+

        Parameters
        ----------
        UDT_Index               : int
            the udt index
        version                 : int
            the "UAT Read Parameter" versions number
        deviceId                : int
            target device ID
        NumberOfInstructions    : int
            in UAT format version 4 several instructions can be sent in one block. The argument specifies the number
            of instructions.
        crcCalcDataArray        : list
            data for the calculation of the crc value

        Returns
        -------
        headerMessage       : bytearray
            encoded header message

        """
        headerMessage = bytearray(8)
        # Encode the UDT-Index
        headerMessage[0:2] = struct.pack('<H', UDT_Index)
        # Encode the version number
        headerMessage[2:4] = struct.pack('<H', version)
        # Encode the device ID
        headerMessage[4] = deviceId
        # Encode the number of instructions
        headerMessage[5] = NumberOfInstructions

        # Calculate the crc value. Over instruction message 1-3 for all instructions. Header is ignored for CRC
        # calculation.
        initCrc = 0xFFFF
        calcCRC = crc16.crc16xmodem(bytes(crcCalcDataArray), initCrc)
        # Encode the crc value
        headerMessage[6:8] = struct.pack('<H', calcCRC)
        return headerMessage

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: decodeHeaderMessage                                                                                    #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def decodeHeaderMessage(headerMessage, crcCalcDataArray):
        """
        The function decodes the header message and check that the crc value is correct. Returns the UDT-Index, the
        version, the device ID and the number of instructions. The header message is defined:

        +--------------+---------------------------+
        | Byte 0       |                           |
        +--------------+ UDT-Index                 |
        | Byte 1       |                           |
        +--------------+---------------------------+
        | Byte 2       |                           |
        +--------------+ Version                   |
        | Byte 3       |                           |
        +--------------+---------------------------+
        | Byte 4       | Device ID                 |
        +--------------+---------------------------+
        | Byte 5       | Number of instructions    |
        +--------------+---------------------------+
        | Byte 6       |                           |
        +--------------+ crc16 value               |
        | Byte 7       |                           |
        +--------------+---------------------------+

        Parameters
        ----------
        headerMessage           : bytearray
            encoded header message
        crcCalcDataArray        : list
            data for the calculation of the crc value

        Returns
        -------
        A list with the UDT-Index, the version, the device ID and the number of instructions.

        Raises
        ------
        ValueError:
            if the received crc and the calculated crc value mismatch.

        """
        # Decode the UDT-Index
        index = struct.unpack('<H', headerMessage[0:2])[0]
        # Decode the version number
        version = struct.unpack('<H', headerMessage[2:4])[0]
        # Decode the device ID
        deviceId = headerMessage[4]
        # Decode the number of instructions
        numberOfInstructions = headerMessage[5]

        # Calculate the crc value
        initCrc = 0xFFFF
        calcCRC = crc16.crc16xmodem(bytes(crcCalcDataArray), initCrc)
        # Decode the crc value
        recvCRC = struct.unpack('<H', headerMessage[6:8])[0]
        if calcCRC != recvCRC:
            raise ValueError("UDT_UATv4Response decodeHeaderMessage: CRC error calc: {}, received {}"
                             .format(calcCRC, recvCRC))
        return [index, version, deviceId, numberOfInstructions]

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: encodeParameterMessage                                                                                 #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def encodeParameterMessage(UDT_Index, counter, messageType, UAT_ID, parameterNumber):
        """
        The function encodes the arguments to a byte array with 8 bytes. The parameter(instruction1) message is defined:

        +--------------+--------------------------+
        | Byte 0       |                          |
        +--------------+ UDT-Index                |
        | Byte 1       |                          |
        +--------------+--------------------------+
        | Byte 2       | Counter                  |
        +--------------+--------------------------+
        | Byte 3       | Message type             |
        +--------------+--------------------------+
        | Byte 4       |                          |
        +--------------+ UAT-ID                   |
        | Byte 5       |                          |
        +--------------+--------------------------+
        | Byte 6       |                          |
        +--------------+ Parameter number         |
        | Byte 7       |                          |
        +--------------+--------------------------+

        Parameters
        ----------
        UDT_Index           : int
            the udt index
        counter             : int
            number of parameters transmitted. Start at 0, increment by 1 for each additional parameter
        UAT_ID              : int
            uat id
        messageType         : MessageType
            describes the type of message. See the class MessageType (uatMain.py).
        parameterNumber     : int
            parameter number

        Returns
        -------
        parameterMessage    : bytearray
            encoded parameter message

        """
        parameterMessage = bytearray(8)
        # Encode the UDT-Index
        parameterMessage[0:2] = struct.pack('<H', UDT_Index)
        # Encode the counter
        parameterMessage[2] = counter
        # Encode message type
        parameterMessage[3] = messageType
        # Encode UAT_ID
        parameterMessage[4:6] = struct.pack('<H', UAT_ID)
        # Encode parameter number
        parameterMessage[6:8] = struct.pack('<H', parameterNumber)
        return parameterMessage

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: decodeParameterMessage                                                                                 #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def decodeParameterMessage(parameterMessage):
        """
        The function decodes the parameter(instruction1) message. Returns a list with the UDT-Index, the counter, the
        message type, the uat-id and the parameter number. The parameter message is defined:

        +--------------+--------------------------+
        | Byte 0       |                          |
        +--------------+ UDT-Index                |
        | Byte 1       |                          |
        +--------------+--------------------------+
        | Byte 2       | Counter                  |
        +--------------+--------------------------+
        | Byte 3       | Message type             |
        +--------------+--------------------------+
        | Byte 4       |                          |
        +--------------+ UAT-ID                   |
        | Byte 5       |                          |
        +--------------+--------------------------+
        | Byte 6       |                          |
        +--------------+ Parameter number         |
        | Byte 7       |                          |
        +--------------+--------------------------+

        Parameters
        ----------
        parameterMessage    : bytearray
            encoded parameter message

        Returns
        -------
        The list contains the UDT-Index, the counter, the message type, the uat-id and the parameter number.

        """
        # Decode the message
        index = struct.unpack('<H', parameterMessage[0:2])[0]
        # Decode the counter
        counter = parameterMessage[2]
        # Decode the message type
        messageType = MessageType(parameterMessage[3])
        # Decode the UAT-ID
        UAT_ID = struct.unpack('<H', parameterMessage[4:6])[0]
        # Decode the parameter number
        parameterNumber = struct.unpack('<H', parameterMessage[6:8])[0]
        return [index, counter, messageType, UAT_ID, parameterNumber]

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: encodeParameterValueMessage                                                                            #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def encodeParameterValueMessage(UDT_Index, counter, result, parameterValue, dataFormat):
        """
        The function encodes the arguments to a byte array with 8 bytes. The parameter value(instruction2) message is
        defined:

        +--------------+--------------------------+
        | Byte 0       |                          |
        +--------------+ UDT-Index                |
        | Byte 1       |                          |
        +--------------+--------------------------+
        | Byte 2       | Counter                  |
        +--------------+--------------------------+
        | Byte 3       | Result                   |
        +--------------+--------------------------+
        | Byte 4       |                          |
        +--------------+                          |
        | Byte 5       |                          |
        +--------------+ Parameter value          |
        | Byte 6       |                          |
        +--------------+                          |
        | Byte 7       |                          |
        +--------------+--------------------------+

        Parameters
        ----------
        UDT_Index           : int
            the udt index
        counter             : int
            number of parameters transmitted. Start at 0, increment by 1 for each additional parameter
        result              : int
            return value or error code. See the class UAT_RespErrorCode (udtUatResponseMain.py)
        parameterValue      : int
            parameter value
        dataFormat          : int
            specifies the format of the data

        Returns
        -------
        parameterValueMessages      : bytearray
            encoded parameter value message

        Raises
        ------
        ValueError:
            if the data format does not specify int or float type.
        TypeError:
            if the data format and the type of the parameter value mismatch.
        """
        parameterValueMessage = bytearray(8)
        # Encode the UDT-Index
        parameterValueMessage[0:2] = struct.pack('<H', UDT_Index)
        # Encode the counter
        parameterValueMessage[2] = counter
        # Encode the result
        parameterValueMessage[3] = result

        if dataFormat == DataFormat.INTEGER.value :
            # Check if the parameterValue type is int
            if type(parameterValue) is not int:
                raise TypeError("UDT_UATv4Response encodeParameterValueMessage: data type of passed value does not match"
                                " the given parameter type int")
            # Encode the parameter parameterValue
            parameterValueMessage[4:] = struct.pack('<i', parameterValue)
        # Check if the value type is float
        elif dataFormat == DataFormat.FLOAT_IEEE.value :
            # Check if the parameterValue type is float
            if type(parameterValue) is not float:
                raise TypeError("UDT_UATv4Response encodeParameterValueMessage: data type of passed value does not match"
                                " the given parameter type float")
            # Encode the parameter parameterValue
            parameterValueMessage[4:] = struct.pack('<f', parameterValue)
        else:
            raise ValueError("UDT_UATv4Response encodeParameterValueMessage: unknown Parameter Type.")

        return parameterValueMessage

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: decodeParameterValueMessage                                                                            #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def decodeParameterValueMessage(parameterValueMessage, dataFormat):
        """
        The function decodes the parameter value(instruction2) message. Returns a list with the UDT-Index, the counter,
        the result and the parameter value. The parameter value message is defined:

        +--------------+--------------------------+
        | Byte 0       |                          |
        +--------------+ UDT-Index                |
        | Byte 1       |                          |
        +--------------+--------------------------+
        | Byte 2       | Counter                  |
        +--------------+--------------------------+
        | Byte 3       | Result                   |
        +--------------+--------------------------+
        | Byte 4       |                          |
        +--------------+                          |
        | Byte 5       |                          |
        +--------------+ Parameter value          |
        | Byte 6       |                          |
        +--------------+                          |
        | Byte 7       |                          |
        +--------------+--------------------------+

        Parameters
        ----------
        parameterValueMessage       : bytearray
            encoded parameter value message
        dataFormat                  : DataFormat
            specifies the format of the data

        Returns
        -------
            A list contains the UDT-Index, the counter, the result and the parameter value

        Raises
        ------
        ValueError:
            if the data format does not specify int or float type.

        """
        # Decode the message
        index = struct.unpack('<H', parameterValueMessage[0:2])[0]
        # Decode the counter
        counter = parameterValueMessage[2]
        # Decode the result
        result = UAT_RespErrorCode(parameterValueMessage[3])
        # Decode the value
        if dataFormat == DataFormat.INTEGER.value:
            # parameter type is an integer type
            value = struct.unpack('<i', parameterValueMessage[4:8])[0]
        elif dataFormat == DataFormat.FLOAT_IEEE.value:
            # parameter type is a float type
            value = struct.unpack('<f', parameterValueMessage[4:8])[0]
        else:
            raise ValueError("UDT_UATv4Response decodeParameterValueMessage: unknown Parameter Type")
        return [index, counter, result, value]

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: encodeDimMessage                                                                                       #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def encodeDimMessage(UDT_Index, counter, dataFormat, dim0, dim1):
        """
        The function encodes the arguments to a byte array with 8 bytes. The dim(instruction3) message is defined:

        +--------------+--------------------------+
        | Byte 0       |                          |
        +--------------+ UDT-Index                |
        | Byte 1       |                          |
        +--------------+--------------------------+
        | Byte 2       | Counter                  |
        +--------------+--------------------------+
        | Byte 3       | Data format              |
        +--------------+--------------------------+
        | Byte 4       | Dim 0                    |
        +--------------+--------------------------+
        | Byte 5       | Dim 1                    |
        +--------------+--------------------------+
        | Byte 6       | Not used                 |
        +--------------+--------------------------+
        | Byte 7       | Not used                 |
        +--------------+--------------------------+

        Parameters
        ----------
        UDT_Index           : int
            the udt index
        counter             : int
            number of parameters transmitted. Start at 0, increment by 1 for each additional parameter
        dataFormat          : int
            specifies the format of the data
        dim0                : int
            for arrays in parameter structures, specifies which indexes should be used in which dimension
        dim1                : int
            for arrays in parameter structures, specifies which indexes should be used in which dimension

        Returns
        -------
        dimMessage          : bytearray
            encoded dim message

        """
        dimMessage = bytearray(8)
        # Encode the UDT-Index
        dimMessage[0:2] = struct.pack('<H', UDT_Index)
        # Encode the counter
        dimMessage[2] = counter
        # Encode the data format
        dimMessage[3] = dataFormat
        # Encode dim A
        dimMessage[4] = dim0
        # Encode dim B
        dimMessage[5] = dim1
        # Byte 6 and 7 are unused
        return dimMessage

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: decodeDimMessage                                                                                       #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def decodeDimMessage(dimMessage):
        """
        The function decodes the dim message. The dim message is defined:

        +--------------+--------------------------+
        | Byte 0       |                          |
        +--------------+ UDT-Index                |
        | Byte 1       |                          |
        +--------------+--------------------------+
        | Byte 2       | Counter                  |
        +--------------+--------------------------+
        | Byte 3       | Data format              |
        +--------------+--------------------------+
        | Byte 4       | Dim 0                    |
        +--------------+--------------------------+
        | Byte 5       | Dim 1                    |
        +--------------+--------------------------+
        | Byte 6       | Not used                 |
        +--------------+--------------------------+
        | Byte 7       | Not used                 |
        +--------------+--------------------------+

        Parameters
        ----------
        dimMessage          : bytearray
            encoded dim message

        Returns
        -------
        A list contains the UDT-Index, the counter, the data format, dim 0 and dim 1.

        """
        # Decode the message
        index = struct.unpack('<H', dimMessage[0:2])[0]
        # Decode the counter
        counter = dimMessage[2]
        # Decode the data format
        dataFormat = DataFormat(dimMessage[3])
        # Decode the dim A
        dimA = dimMessage[4]
        # Encode the dim B
        dimB = dimMessage[5]
        # Byte 6 and 7 are unused
        return [index, counter, dataFormat, dimA, dimB]

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: encode                                                                                                 #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def encode(data):
        """
        Encodes a dictionary of UDT type 17000 version 5

        Parameters
        ----------
        data            : dict
            A dict with the keys: 'UDT-Index', 'version', 'UAT-ID', 'result', 'deviceId' 'parameterNumber',
            'messageType', 'dataFormat', 'counter', 'numberOfInstructions' 'dim0', 'dim1' and 'value'.

        Returns
        -------
        messageList     : list
            (1 + 3 * numberOfInstructions) byte objects representing the UAT Response Message for UAT message version 1

        Raises
        ------
        ValueError:
            if the UDT index does not match the expected one (17000)
            if the version is not equal 5
        TypeError:
            if the type from the udt-index, uat-index, parameterNumber, dim0 or dim1 is not int
            if the length form the data['instructionsList'] and the value from the data['numberOfInstructions'] mismatch

        """
        # Check that the parameterNumber, the UAT-ID are an integer
        if type(data['UDT-Index']) is not int:
            raise TypeError("UDT_UATv4Response encode: UDT-Index must be of type int")
        if data['UDT-Index'] != 17000:
            raise ValueError("UDT_UATv4Response encode: UDT-Index value is not 17000")
        # Check the version number
        if data['version'] != 5:
            raise ValueError("UDT_UATv4Response encode: The version number is false. Expected 5. Found: {}"
                             .format(data['version']))
        # Check that the commandList is correct
        if len(data['instructionsList']) != data['numberOfInstructions']:
            raise TypeError("UDT_UATv4Response encode: The instructions list does not have the same number as "
                            "numberOfCommands. len(data['instructionsList']):{} data['numberOfInstructions']{}"
                            .format(len(data['instructionsList']), data['numberOfInstructions']))

        numberOfInstructions = data['numberOfInstructions']
        messageList = []

        # Create and encode the three messages for each instruction
        for index in range (0, numberOfInstructions):
            # The command data
            instructionsData = data['instructionsList'][index]
            # Check the parameter number type
            if type(instructionsData['parameterNumber']) is not int:
                raise TypeError("UDT_UATv4Response encode: ParameterNumber must be of type int")
            if type(instructionsData['dim0']) is not int or type(instructionsData['dim1']) is not int:
                raise TypeError("UDT_UATv4Response encode: Dimension must be of type int")
            if type(instructionsData['UAT-ID']) is not int:
                raise TypeError("UDT_UATv4Response encode: UAT-ID must be of type int")

            # Encode the instruction message 1 (parameter message)
            messageList.append(UATv4Response.encodeParameterMessage(data['UDT-Index'] + 16, instructionsData['counter'], instructionsData['messageType'].value,
                                                                              instructionsData['UAT-ID'], instructionsData['parameterNumber']))
            # Encode the instruction message 2 (parameter value message)
            messageList.append(UATv4Response.encodeParameterValueMessage(data['UDT-Index'] + 17, instructionsData['counter'],
                                                                                   instructionsData['result'].value, instructionsData['value'], instructionsData['dataFormat'].value))
            # Encode the instruction message 3 (dim message)
            messageList.append(UATv4Response.encodeDimMessage(data['UDT-Index'] + 18, instructionsData['counter'], instructionsData['dataFormat'].value,
                                                                        instructionsData['dim0'], instructionsData['dim1']))

        # Encode the header and calculate the crc value
        # Calculate the crc value. Over instruction message for all instructions. Header is ignored for CRC
        crcCalcDataArray = []
        # Write all instruction message in an array to calculate the crc value
        for message in messageList:
            crcCalcDataArray.extend(message[0:8])
        header = UATv4Response.encodeHeaderMessage(data['UDT-Index'], data['version'], data['deviceId'],
                                                   data['numberOfInstructions'], crcCalcDataArray)
        # Add the header to the first position
        messageList.insert(0, header)

        return messageList

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: decode                                                                                                 #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def decode(msgList):
        """
        Decodes a binary message of UDT type 17000 version 5 which is an UAT Response Message for UAT message version 4

        Parameters
        ----------
        msgList     : bytearray
            (1 + 3 * numberOfInstructions) byte objects representing the UAT Response Message for UAT message version 1

        Returns
        -------
        data        : dict
            A dict with the keys: 'UDT-Index', 'version', 'UAT-ID', 'result', 'deviceId' 'parameterNumber',
            'messageType', 'dataFormat', 'counter', 'numberOfInstructions' 'dim0', 'dim1' and 'value'.

        Raises
        ------
        ValueError:
            if the UDT index does not match the expected one (17000)
            if the version is not equal 5
            if the counters from the instruction message does not match.
        TypeError:
            if the length from each message is not equal 8.
            if the number of messages is not equal (1 + 3 * numberOfInstructions).
        """
        # Checks that the msgList is correct.
        # One header and n * 3 instructions messages.
        if len(msgList) % 3 != 1:
            raise TypeError('UDT_UATv4Response decode: The message list has not 1 + 2 * n messages. len(msgList):{}'
                            .format(len(msgList)))

        # Checks that the messages in the msgList is correct
        messagesLength = 8
        for message in msgList:
            if len(message) != messagesLength:
                raise TypeError('UDT_UATv4Response decode: The input message list is corrupt. len(msgList):{}'
                                .format(len(msgList)))

        data = dict()
        # Decode the header
        header = msgList[0]
        crcCalcDataArray = []
        for message in msgList[1:]:
            crcCalcDataArray.extend(message[0:8])
        [data['UDT-Index'], data['version'], data['deviceId'], data['numberOfInstructions']] = UATv4Response.decodeHeaderMessage(header, crcCalcDataArray)

        # Check the version
        if data['version'] != 5:
            raise ValueError("UDT_UATv4Response decode: Tried to decode a UAT response with wrong UDT type 17000 version. "
                            "Version 5 expected. Found {}".format(data['version']))
        # Check the UDI-Index from header
        if data['UDT-Index'] != 17000:
            raise ValueError("UDT_UATv4Response decode: header Decoded UDT index is not 17000 instead {} was decoded"
                            .format(data['UDT-Index']))

        # Decode the first and second command message for each received command
        data['instructionsList'] = [dict()] * data['numberOfInstructions']
        for instructionIndex in range(0, data['numberOfInstructions']):
            message1 = msgList[1 + (instructionIndex * 3)]
            message2 = msgList[2 + (instructionIndex * 3)]
            message3 = msgList[3 + (instructionIndex * 3)]
            instructionData = dict()

            # Decode instruction message 1 (parameter message)
            [index, counter1, instructionData['messageType'], instructionData['UAT-ID'], instructionData['parameterNumber']] = UATv4Response.decodeParameterMessage(message1)
            # Check the UDI-Index from instruction message 1
            if index != 17016:
                raise ValueError("UDT_UATv4Response decode: header Decoded UDT index is not 17016 instead {} was decoded"
                                .format(index))

            # Decode instruction message 3 (parameter value message)
            [index, counter3, instructionData['dataFormat'], instructionData['dim0'], instructionData['dim1']] = UATv4Response.decodeDimMessage(message3)
            # Check the UDI-Index from instruction message 2
            if index != 17018:
                raise ValueError("UDT_UATv4Response decode: header Decoded UDT index is not 17018 instead {} was decoded"
                                 .format(index))

            # Decode instruction message 2 (parameter value message)
            [index, counter2, instructionData['result'], instructionData['value']] = UATv4Response.decodeParameterValueMessage(message2, instructionData['dataFormat'].value)
            # Check the UDI-Index from instruction message 2
            if index != 17017:
                raise ValueError("UDT_UATv4Response decode: header Decoded UDT index is not 17017 instead {} was decoded"
                                 .format(index))

            # Check that all three counter are the same
            if counter1 != counter2 or counter1 != counter3:
                raise ValueError('UDT_UATv4Response decode: The three instruction message counters does not match. Counter1:{} Counter2:{} Counter3:{}'
                                 .format(counter1, counter2, counter3))
            instructionData['counter'] = counter1

            data['instructionsList'][instructionIndex] = instructionData
        return data