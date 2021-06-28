import struct
from smartmicro.Protocols.uat.uatMain import UATMainV1_V2_V3


class UATv2:
    """
    The class encodes and decodes UAT version 2 messages

    """

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: encode                                                                                                 #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def encode(data):
        """
        Encodes the provided data into three byte messages according to the UATv2 format.

        Parameters
        ----------
        data    : dict
            A dict with the keys: 'UAT-ID', 'deviceId' 'parameterNumber', 'parameterType', 'value', 'din0', 'dim1',
            'dim2' and 'dim3'.

        Returns
        -------
        Three byte objects representing the uat_v2 messages

        Raises
        ------
        TypeError:
            if either data['parameterNumber'], data['UAT-ID'] or data['dim0..3'] is not of type int
            The passed parameter type does not match the type of the passed value
        """
        if type(data['parameterNumber']) is not int:
            raise TypeError("UATv2 encode: ParameterNumber must be of type int")

        if type(data['UAT-ID']) is not int:
            raise TypeError("UATv2 encode: UAT-ID must be of type int")

        if type(data['dim0']) is not int or type(data['dim1']) is not int or type(data['dim2']) is not int or type(
                data['dim3']) is not int:
            raise TypeError("UATv2 encode: Dimension must be of type int")

        # Encode the parameter message
        message2 = UATMainV1_V2_V3.encodeParameterMessage(data['UAT-ID'], data['deviceId'], data['parameterType'],
                                                          data['value'])

        # Creates the dim message
        message3Index = 0x2
        message3 = UATMainV1_V2_V3.encodeDimMessage(data['UAT-ID'], message3Index, data['dim0'], data['dim1'], data['dim2'],
                                                    data['dim3'])

        # Creates the header message
        crcCalcArray  = message2[0:8]
        crcCalcArray.extend(message3)
        message1Header = UATMainV1_V2_V3.encodeHeader(data['UAT-ID'], data["uatVersion"], data['parameterType'].value,
                                                      data['parameterNumber'], crcCalcArray)
        return [message1Header, message2, message3]

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: decode                                                                                                 #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def decode(msgList):
        """
        Decodes the two message UATv2 format in a data dict.

        Parameters
        ----------
        msgList:
        Contains three byte objects each being of length 8.

        Returns
        -------
        A dict with the keys: 'UAT-ID', 'deviceId' 'parameterNumber', 'parameterType', 'value', 'din0', 'dim1', 'dim2'
        and 'dim3'.

        Raises
        ------
        TypeError:
            if the length from each message is not equal 8.
            if the number of messages is not equal 3.
        ValueError:
            if the decoded uat version is not equal 2.
            if the UAT ID between the three message does not match.
            if the message index is wrong.


        """
        # check that the msgList is correct
        numberOfMessages = 3
        if len(msgList) != numberOfMessages:
            raise TypeError('UATv2 decode: The message list has not two messages. msgList:{}' .format(msgList))

        # check that the messages in the msgList is correct
        messagesLength = 8
        if len(msgList[0]) != messagesLength or len(msgList[1]) != messagesLength or len(msgList[2]) != messagesLength:
            raise TypeError('UATv2 decode: The input message list is corrupt. len(msgList[0]):{}. len(msgList[1]):{}. '
                            'len(msgList[2]):{}'
                            .format(len(msgList[0]), len(msgList[1]), len(msgList[2])))

        # create the data dict
        data           = dict()
        message1Header = msgList[0]
        message2       = msgList[1]
        message3       = msgList[2]

        # Check that the format version is correct
        formatVersion = 0x2
        if message1Header[3] != formatVersion:
            raise ValueError('UATv2 decode: The header message has the false version number. Header{} formatVersion{}'
                             .format(message1Header[3], formatVersion))

        # Check the message index
        if message1Header[2] != 0x0 or message2[2] != 0x1 or message3[2] != 0x2:
            raise ValueError('UATv2 decode: The header message index is false. Header{} Message2{} Message3{}'
                             .format(message1Header[2], message2[2], message3[2]))

        # Check that all messages have the same UAT-ID
        uatMsg1 = struct.unpack('<H', message1Header[0:2])[0]
        uatMsg2 = struct.unpack('<H', message2[0:2])[0]
        uatMsg3 = struct.unpack('<H', message3[0:2])[0]
        if uatMsg1 != uatMsg2 or uatMsg1 != uatMsg3:
            raise ValueError("UATv2 decode: UAT ID mismatch between UAT messages")
        data['UAT-ID'] = uatMsg1

        # Decode the header message
        # Gets the parameter Number and Type from the message 1 header
        crcCalcDataArray = message2
        crcCalcDataArray.extend(message3)
        [data['parameterNumber'], data['parameterType'], data["uatVersion"]]  = UATMainV1_V2_V3.decodeHeader(message1Header, crcCalcDataArray)

        # Decode the message 2 (parameter message)
        [data['deviceId'], data['value']] = UATMainV1_V2_V3.decodeParameterMessage(data['parameterType'], message2)

        # Decode the message 3 (dim message)
        [data['dim0'], data['dim1'], data['dim2'], data['dim3']] = UATMainV1_V2_V3.decodeDimMessage(message3)

        return data