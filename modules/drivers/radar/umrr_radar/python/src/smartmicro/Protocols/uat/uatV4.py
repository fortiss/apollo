import struct
import crcmod
from smartmicro.Protocols.uat.uatMain import DataFormat, MessageType


class UATv4:
    """
    The class provides encode and decode functions of UAT messages for versions 4.
    """

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: encodeHeader                                                                                           #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def encodeHeader(UAT_ID, formatVersion, deviceId, numberOfInstructions, crcCalcDataArray):
        """
        The function encodes the arguments to a byte array with 8 bytes. The header message is defined:

        +--------------+--------------------+
        | Byte 0       |                    |
        +--------------+ UAT-ID             |
        | Byte 1       |                    |
        +--------------+--------------------+
        | Byte 2       | Message index      |
        +--------------+--------------------+
        | Byte 3       | Format version     |
        +--------------+--------------------+
        | Byte 4       | Device id          |
        +--------------+--------------------+
        | Byte 5       | Number of commands |
        +--------------+--------------------+
        | Byte 6       |                    |
        +--------------+ crc16 value        |
        | Byte 7       |                    |
        +--------------+--------------------+

        Parameters
        ----------
        UAT_ID                  : int
            UAT index
        formatVersion           : int
            UAT version number
        deviceId                : int
            target device ID
        numberOfInstructions    : int
            in UAT format version 4 several instructions can be sent in one block. The argument specifies the number of
            instructions.
        crcCalcDataArray        : list
            data for the calculation of the crc value

        Returns
        -------
        header      : bytearray
            encoded header message

        """
        # Creates the header message
        header = bytearray(8)
        ## Message 1 (Header) of UAT Format version 1
        header[0:2] = struct.pack('<H', UAT_ID) # UAT-ID
        header[2]   = 0x0 # Message index
        header[3]   = formatVersion
        header[4]   = deviceId
        header[5]   = numberOfInstructions

        # Creates the crc function
        crc16 = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
        # The crc input data
        crcCalcArray = header[0:6]
        crcCalcArray.extend(crcCalcDataArray)
        # Calculates the crc
        calcCRC = crc16(crcCalcArray)
        # Write the crc value into the message 1 header
        header[6:8] = struct.pack('<H', calcCRC)
        return header

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: getHeaderInfo                                                                                          #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def getHeaderInfo(msg):
        """
        The function encodes the UAT-ID, the number of instructions and the device id.
        Parameters
        ----------
        msg     : bytearray

        Returns
        -------
        data    : dict
            A dictionary with the UAT-ID, the number of instructions and the device id.

        """
        data                         = dict()
        data['UAT-ID']               = struct.unpack('<H', msg[0:2])[0]
        data['numberOfInstructions'] = msg[5]
        data['deviceId']             = msg[4]

        return data

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: decodeHeader                                                                                           #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def decodeHeader(headerMessage, crcCalcDataArray):
        """
        The function decodes the header message and check that the crc value is correct. Returns the device id and the
        number of commands. The header message is defined:

        +--------------+--------------------+
        | Byte 0       |                    |
        +--------------+ UAT-ID             |
        | Byte 1       |                    |
        +--------------+--------------------+
        | Byte 2       | Message index      |
        +--------------+--------------------+
        | Byte 3       | Format version     |
        +--------------+--------------------+
        | Byte 4       | Device id          |
        +--------------+--------------------+
        | Byte 5       | Number of commands |
        +--------------+--------------------+
        | Byte 6       |                    |
        +--------------+ crc16 value        |
        | Byte 7       |                    |
        +--------------+--------------------+

        Parameters
        ----------
        headerMessage       : bytearray
            encoded header message
        crcCalcDataArray    : bytearray
            data for the calculation of the crc value

        Returns
        -------
        A list with device id and the number of commands

        Raises
        ------
        ValueError:
            if the received crc value and the calculated crc vale does not match

        """
        # Checks that the crc value is correct
        crcCalcArray = bytearray()
        crcCalcArray.extend(headerMessage[0:6])
        if len(crcCalcDataArray) != 0:
            crcCalcArray.extend(crcCalcDataArray)
        # Calculate the crc value
        crc16 = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
        crcCalc = crc16(crcCalcArray)
        # The received crc value
        crcRecv = struct.unpack('<H', headerMessage[6:8])[0]
        # Checks that the calculated and received crc value are correct
        if crcCalc != crcRecv:
            raise ValueError("UATv4 decodeHeader: CRC Mismatch CRC Calc:{}, crc recv:{}".format(crcCalc, crcRecv))

        # device ID
        deviceID = headerMessage[4]
        # Number of commands
        numberOfCommands = headerMessage[5]
        uatVersion = headerMessage[3]
        return [deviceID, numberOfCommands, uatVersion]

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: encodeCommandMessage                                                                                   #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def encodeCommandMessage(UAT_ID, messageType, parameterNumber, dim0, dim1, dataFormat, parameterValue, commandIndex):
        """
        The function encodes the command to two bytearray. The first command message is defined as:

        +--------------+--------------------+
        | Byte 0       |                    |
        +--------------+ UAT-ID             |
        | Byte 1       |                    |
        +--------------+--------------------+
        | Byte 2       | Command index      |
        +--------------+--------------------+
        | Byte 3       | Message type       |
        +--------------+--------------------+
        | Byte 4       |                    |
        +--------------+ Parameter number   |
        | Byte 5       |                    |
        +--------------+--------------------+
        | Byte 6       | Dim 0              |
        +--------------+--------------------+
        | Byte 7       | Dim 1              |
        +--------------+--------------------+

        The second command message is defined as:

        +--------------+--------------------+
        | Byte 0       |                    |
        +--------------+ UAT-ID             |
        | Byte 1       |                    |
        +--------------+--------------------+
        | Byte 2       | Command index      |
        +--------------+--------------------+
        | Byte 3       | Data format        |
        +--------------+--------------------+
        | Byte 4       | Parameter value    |
        +--------------+                    |
        | Byte 5       |                    |
        +--------------+                    |
        | Byte 6       |                    |
        +--------------+                    |
        | Byte 7       |                    |
        +--------------+--------------------+


        Parameters
        ----------
        UAT_ID                  : integer
            UAT index
        messageType             : MessageType
            assign parameter/status/command message
        dim0                    : integer
            first dimension index
        dim1                    : integer
            second dimension index
        parameterNumber         : integer
            parameter number
        dataFormat              : DataFormat
            specifies the format of the data (float or int data)
        parameterValue          : integer/float
            value to be set
        commandIndex            : integer
            index of the command

        Returns
        -------
        The encoded command messages

        Raises
        ------
        TypeError:
            if the data format and the type of the parameter value mismatch.
        ValueError:
            if the data format does not specify int or float type.

        """
        # Create the first message
        message1 = bytearray(8)
        message1[0:2] = struct.pack('<H', UAT_ID) # UAT-ID
        message1[2] = commandIndex # Message index
        message1[3] = messageType
        message1[4:6] = struct.pack('<H', parameterNumber)
        message1[6] = dim0
        message1[7] = dim1

        # Create the second message
        message2 = bytearray(8)
        message2[0:2] = struct.pack('<H', UAT_ID) # UAT-ID
        message2[2] = commandIndex + 1 # Message index
        message2[3] = dataFormat
        # Writes the parameter value
        # int value
        if dataFormat == DataFormat.INTEGER.value :
            # if type(parameterValue) is not int:
            #     raise TypeError("UATv4 encodeCommandMessage: data type of passed value does not match the given "
            #                     "parameter type int")
            message2[4:] = struct.pack('<I', parameterValue)
        # float value
        elif dataFormat == DataFormat.FLOAT_IEEE.value :
            # if type(parameterValue) is not float:
            #     raise TypeError("UATv4 encodeCommandMessage: data type of passed value does not match the given "
            #                     "parameter type float")
            message2[4:] = struct.pack('<f', parameterValue)
        else:
            raise ValueError("UATv4 encodeCommandMessage: unknown Parameter Type")
        return[message1, message2]

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: decodeCommandMessage                                                                                   #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def decodeCommandMessage(message1, message2):
        """
        The function decodes the command messages. Returns the message type, parameter number, dim0, dim1, data format
        and parameter value. The command messages are defined as:

        +--------------+--------------------+
        | Byte 0       |                    |
        +--------------+ UAT-ID             |
        | Byte 1       |                    |
        +--------------+--------------------+
        | Byte 2       | Command index      |
        +--------------+--------------------+
        | Byte 3       | Message type       |
        +--------------+--------------------+
        | Byte 4       |                    |
        +--------------+ Parameter number   |
        | Byte 5       |                    |
        +--------------+--------------------+
        | Byte 6       | Dim 0              |
        +--------------+--------------------+
        | Byte 7       | Dim 1              |
        +--------------+--------------------+

        The second command message is defined as:

        +--------------+--------------------+
        | Byte 0       |                    |
        +--------------+ UAT-ID             |
        | Byte 1       |                    |
        +--------------+--------------------+
        | Byte 2       | Command index      |
        +--------------+--------------------+
        | Byte 3       | Data format        |
        +--------------+--------------------+
        | Byte 4       | Parameter value    |
        +--------------+                    |
        | Byte 5       |                    |
        +--------------+                    |
        | Byte 6       |                    |
        +--------------+                    |
        | Byte 7       |                    |
        +--------------+--------------------+

        Parameters
        ----------
        message1        : bytearray
            the first encoded command message
            the second encoded command message
        message2

        Returns
        -------
        A list with message type, parameter number, dim0, dim1, data format, parameter value, idx

        Raises
        ------
        ValueError:
            if the data format does not specify int or float type.

        """
        # Information from the first message
        idx        = int(( message1[2] - 1 ) / 2)
        messageTyp = MessageType(message1[3])
        parameterNumber = struct.unpack('<H', message1[4:6])[0]
        dim0 = message1[6]
        dim1 = message1[7]

        # Information from the second message
        dataFormat = DataFormat(message2[3])
        # Writes the parameter value
        # int value
        if dataFormat == DataFormat.INTEGER :
            parameterValue = struct.unpack('<I', message2[4:])[0]
        # float value
        elif dataFormat == DataFormat.FLOAT_IEEE :
            parameterValue = struct.unpack('<f', message2[4:])[0]
        else:
            raise ValueError("UATv4 decodeCommandMessage: unknown data format Type")
        return [messageTyp, parameterNumber, dim0, dim1, dataFormat, parameterValue, idx]

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: encode                                                                                                 #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def encode(data):
        """
        Encodes the provided data into (1 + 2 * numberOfInstructions) byte messages according to the UATv4 format

        Parameters
        ----------
        data            : dict
            A dict with the keys: 'UAT-ID', 'deviceId', 'dataFormat', 'numberOfInstructions', 'instructionsList',
            'parameterNumber', 'messageType', 'value', 'din0', and 'dim1'.

        Returns
        -------
        (1 + 2 * numberOfInstructions byte objects representing the uat_v4 messages

        Raises
        ------
        ValueError:
            if the 'numberOfInstructions' value is negative
        TypeError:
            if the type from the uat-index, parameterNumber, dim0 or dim1 is not int
            if the length form the data['instructionsList'] and the value from the data['numberOfInstructions'] mismatch.

        """
        # Check the UAT-ID type
        if type(data['UAT-ID']) is not int:
            raise TypeError("UATv4 encode: UAT-ID must be of type int")
        # Check the number of commands
        if data['numberOfInstructions'] < 0:
            raise ValueError("UATv4 encode: The number of Instructions is less then 0. NumberOfInstructions{}"
                             .format(data['numberOfInstructions']))
        # Check that the commandList is correct
        if len(data['instructionsList']) != data['numberOfInstructions']:
            raise TypeError("UATv4 encode: The instructions list does not have the same number as numberOfCommands. "
                             "len(data['instructionsList']):{} data['numberOfInstructions']{}" .format(len(data['instructionsList']),
                                                                                            data['numberOfInstructions']))

        numberOfInstructions = data['numberOfInstructions']
        messageList = []

        instructionsIndex = 1

        # Create and encode the two messages for each command
        for index in range (0, numberOfInstructions):
            # The command data
            instructionsData  = data['instructionsList'][index]
            instructionsIndex = 1 + ( 2 * instructionsData["instructionIdx"] )
            # Check the parameter number type
            if type(instructionsData['parameterNumber']) is not int:
                raise TypeError("UATv4 encode: ParameterNumber must be of type int")
            if type(instructionsData['dim0']) is not int or type(instructionsData['dim1']) is not int:
                raise TypeError("UATv4 encode: Dimension must be of type int")

            # Encode the command
            instructionMessage = (UATv4.encodeCommandMessage(data['UAT-ID'], instructionsData['messageType'].value,
                                                             instructionsData['parameterNumber'], instructionsData['dim0'],
                                                             instructionsData['dim1'], instructionsData['dataFormat'].value,
                                                             instructionsData['value'], instructionsIndex))
            messageList.append(instructionMessage[0])
            messageList.append(instructionMessage[1])

        # Create a array with all command data to calculate the crc value
        crcCalcArray = []
        for message in messageList:
            crcCalcArray.extend(message[0:8])

        header = UATv4.encodeHeader(data['UAT-ID'], data["uatVersion"], data['deviceId'], data['numberOfInstructions'],
                                    crcCalcArray)
        # Add the header to the first position
        messageList.insert(0, header)

        return messageList

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: decode                                                                                                 #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def decode(msgList):
        """
        Decodes the two message UATv4 format in a data dict.

        Parameters
        ----------
        msgList         : bytearray
            Contains (1 + 2 * numberOfInstructions) byte objects each being of length 8.

        Returns
        -------
        data            : dictionary
            A dictionary with the keys: 'UAT-ID', 'deviceId', 'dataFormat', 'numberOfInstructions',
            'instructionsList', 'parameterNumber', 'messageType', 'value', 'din0', and 'dim1'.

        Raises
        ------
        ValueError:
            if the UAT ID does not match the expected one
        TypeError:
            if the length from each message is not equal 8.
            if the number of messages is not equal (1 + 2 * numberOfInstructions).

        """
        # Checks that the msgList is correct.
        if not len(msgList) % 2:
            raise TypeError('UATv4 decode: The message list has not 1 + 2 * n messages. len(msgList):{}'
                            .format(len(msgList)))

        # Checks that the messages in the msgList is correct
        messagesLength = 8
        for message in msgList:
            if len(message) != messagesLength:
                raise TypeError('UATv4 decode: The input message list is corrupt. len(msgList):{}'
                                .format(len(msgList)))

        data = dict()
        numberOfMessages = len(msgList)

        # Decode the header and check the UAT-ID
        messageHeader = msgList[0]
        uatHeader = struct.unpack('<H', messageHeader[0:2])[0]
        crcCalcArray = bytearray()
        for message in msgList[1:]:
            crcCalcArray.extend(message)
            uatMsg = struct.unpack('<H', message[0:2])[0]
            if uatHeader != uatMsg:
                raise ValueError("UATv4 decode: UAT ID mismatch between UAT messages")
        [data['deviceId'], data['numberOfInstructions'], data["uatVersion"]] = UATv4.decodeHeader(messageHeader, crcCalcArray)
        data['UAT-ID'] = uatHeader

        # Check that the number of message and the number of commands are correct. number of message = 1 + 2 * number of commands
        calcNumberOfMessages = 1 + 2 * data['numberOfInstructions']
        if numberOfMessages != calcNumberOfMessages:
            raise ValueError('UATv4 decode: The number of messages and the number of commands does not match. '
                             'len(msgList):{} calcNumberOfMessages:{} numberOfCommands:{}'
                             .format(len(msgList), calcNumberOfMessages, data['numberOfCommands']))

        # Decode the first and second command message for each received command
        indexCommand = 0
        data['instructionsList'] = [dict()] * data['numberOfInstructions']
        for index in range(1, numberOfMessages, 2):
            message1 = msgList[index]
            message2 = msgList[index+1]
            instructionData = dict()
            [instructionData['messageType'] , instructionData['parameterNumber'], instructionData['dim0'],
             instructionData['dim1'], instructionData['dataFormat'], instructionData['value'],
             instructionData['instructionIdx']]= UATv4.decodeCommandMessage(message1, message2)
            data['instructionsList'][indexCommand] = instructionData
            indexCommand += 1

        return data