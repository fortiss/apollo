import struct
from smartmicro.Protocols.uat.uatMain import UATMainV1_V2_V3


class UATv3:
    """
    The class encodes and decodes UAT version 3 messages

    """

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: encode                                                                                                 #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def encode(data):
        """
        Encodes the provided data into three byte messages according to the UATv3 format.


        Parameters
        ----------
        data    : dictionary
            A dict with the keys: 'UAT-ID', 'deviceId' 'parameterNumber', 'parameterType', 'value', 'din0', 'dim1',
            'dim2', 'dim3', 'dim4', 'dim5', 'dim6' and 'dim7'

        Returns
        -------
        Four byte objects representing the uat_v3 messages

        Raises
        ------
        TypeError:
            if either data['parameterNumber'], data['UAT-ID'] or data['dim0..7'] is not of type int
            the passed parameter type does not match the type of the passed value

        """
        if type(data['parameterNumber']) is not int:
            raise TypeError("UATv3 encode: ParameterNumber must be of type int")

        if type(data['UAT-ID']) is not int:
            raise TypeError("UATv3 encode: UAT-ID must be of type int")

        if type(data['dim0']) is not int or type(data['dim1']) is not int or type(data['dim2']) is not int or type(
                data['dim3']) is not int or type(data['dim4']) is not int or type(data['dim5']) is not int or type(
                data['dim6']) is not int or type(data['dim7']) is not int:
            raise TypeError("UATv3 encode: Dimension must be of type int")

        # Encode the parameter message
        message2 = UATMainV1_V2_V3.encodeParameterMessage(data['UAT-ID'], data['deviceId'], data['parameterType'],
                                                          data['value'])

        # Encode the dim message (dim0-3)
        message3Index = 0x2
        message3 = UATMainV1_V2_V3.encodeDimMessage(data['UAT-ID'], message3Index, data['dim0'], data['dim1'],
                                                    data['dim2'], data['dim3'])
        # Encode the dim message (dim4-7)
        message4Index = 0x3
        message4 = UATMainV1_V2_V3.encodeDimMessage(data['UAT-ID'], message4Index, data['dim4'], data['dim5'],
                                                    data['dim6'], data['dim7'])

        # Encode the header message
        crcCalcArray = message2[0:8]
        crcCalcArray.extend(message3)
        crcCalcArray.extend(message4)
        message1_header = UATMainV1_V2_V3.encodeHeader(data['UAT-ID'], data["uatVersion"], data['parameterType'].value,
                                                       data['parameterNumber'], crcCalcArray)

        return [message1_header, message2, message3, message4]

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: decode                                                                                                 #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def decode(msgList):
        """
        Decodes the two message UATv3 format in a data dict.

        Parameters
        ----------
        msgList     : bytearray
            contains four byte objects each being of length 8.

        Returns
        -------
            A dict with the keys: 'UAT-ID', 'deviceId' 'parameterNumber', 'parameterType', 'value', 'din0', 'dim1',
            'dim2', 'dim3', 'dim4', 'dim5', 'dim6' and 'dim7'.

        Raises
        ------
        TypeError:
            if the length from each message is not equal 8.
            if the number of messages is not equal 4.
        ValueError:
            if the decoded uat version is not equal 3.
            if the UAT ID between the three message does not match.
            if the message index is wrong.

        """
        # Checks that the msgList is correct
        numberOfMessages = 4
        if len(msgList) != numberOfMessages:
            raise TypeError('UATv3 decode: The message list has not two messages. msgList:{}' .format(msgList))

        # Checks that the messages in the msgList is correct
        messagesLength = 8
        if len(msgList[0]) != messagesLength or len(msgList[1]) != messagesLength or len(msgList[2]) != messagesLength\
                or len(msgList[3]) != messagesLength:
            raise TypeError('UATv3 decode: The input message list is corrupt. len(msgList[0]):{} len(msgList[1]):{} '
                            'len(msgList[2]):{} len(msgList[3]):{}'
                            .format(len(msgList[0]), len(msgList[1]), len(msgList[2]), len(msgList[3])))

        # Creates the data dict
        data = dict()
        message1_header = msgList[0]
        message2 = msgList[1]
        message3 = msgList[2]
        message4 = msgList[3]

        # Checks that the format version is correct
        formatVersion = 0x3
        if message1_header[3] != formatVersion:
            raise ValueError('UATv3 decode: The header message has the false version number. Header{} formatVersion{}'
                             .format(message1_header[3], formatVersion))

        # Checks the message index
        if message1_header[2] != 0x0 or message2[2] != 0x1 or message3[2] != 0x2 or message4[2] != 0x3:
            raise ValueError('UATv3 decode: The header message index is false. Header{} Message2{} Message3{} '
                             'Message4{}'
                             .format(message1_header[2], message2[2], message3[2], message4[2]))

        # Checks that all messages have the same UAT-ID
        uatMsg1 = struct.unpack('<H', message1_header[0:2])[0]
        uatMsg2 = struct.unpack('<H', message2[0:2])[0]
        uatMsg3 = struct.unpack('<H', message3[0:2])[0]
        uatMsg4 = struct.unpack('<H', message4[0:2])[0]
        if uatMsg1 != uatMsg2 or uatMsg1 != uatMsg3 or uatMsg1 != uatMsg4:
            raise ValueError("UATv3 decode: UAT ID mismatch between UAT messages")
        data['UAT-ID'] = uatMsg1

        # Decode the header message
        # Gets the parameter Number and Type from the message 1 header
        crcCalcDataArray = message2
        crcCalcDataArray.extend(message3)
        crcCalcDataArray.extend(message4)
        [data['parameterNumber'], data['parameterType'], data["uatVersion"]]  = UATMainV1_V2_V3.decodeHeader(message1_header, crcCalcDataArray)

        # Decode the message 2 (parameter message)
        [data['deviceId'], data['value']] = UATMainV1_V2_V3.decodeParameterMessage(data['parameterType'], message2)

        # Decode the message 3 (dim 0-3)
        [data['dim0'], data['dim1'], data['dim2'], data['dim3']] = UATMainV1_V2_V3.decodeDimMessage(message3)

        # Decode the message 4 (dim 4-7)
        [data['dim4'], data['dim5'], data['dim6'], data['dim7']] = UATMainV1_V2_V3.decodeDimMessage(message4)

        return data