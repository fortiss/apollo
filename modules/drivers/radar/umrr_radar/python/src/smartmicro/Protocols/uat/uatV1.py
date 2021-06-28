import struct
from smartmicro.Protocols.uat.uatMain import UATMainV1_V2_V3


class UATv1:
    """
    The class encodes and decodes UAT version 1 messages

    """

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: encode                                                                                                 #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def encode(data):
        """
        Encodes the provided data into two byte messages according to the UATv1 format.

        Parameters
        ----------
        data    : dict
            A dict with the keys: 'UAT-ID', 'deviceId' 'parameterNumber', 'parameterType' and 'value'.

        Returns
        -------
        Two byte objects representing the uat v1 messages

        Raises
        ------
        TypeError:
            if either data['parameterNumber'] or data['UAT-ID'] is not of type int
            the passed parameter type does not match the type of the passed value

        """
        # checks that the parameterNumber and the UAT-ID is an integer
        if type(data['parameterNumber']) is not int:
            raise TypeError("UATv1 encode: ParameterNumber must be of type int")
        if type(data['UAT-ID']) is not int:
            raise TypeError("UATv1 encode: UAT-ID must be of type int")

        # creates the parameter message
        message2 = UATMainV1_V2_V3.encodeParameterMessage(data['UAT-ID'], data['deviceId'], data['parameterType'],
                                                          data['value'])

        # creates the header message
        message1Header = UATMainV1_V2_V3.encodeHeader(data['UAT-ID'], data["uatVersion"], data['parameterType'].value,
                                                      data['parameterNumber'], message2)

        return [message1Header, message2]

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: decode                                                                                                 #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def decode(msgList):
        """
        Decodes the two message UATv1 format in a data dict.

        Parameters
        ----------
        msgList
            Contains two byte objects each being of length 8

        Returns
        -------
        A dict with the keys: 'UAT-ID', 'deviceId' 'parameterNumber', 'parameterType' and 'value'

        Raises
        ------
        TypeError:
            if the length from each message is not equal 8.
            if the number of messages is not equal 2.
        ValueError:
            if the decoded uat version is not equal 1.
            if the UAT ID between the two message does not match.
            if the message index is wrong.


        """
        # checks that the msgList is correct
        numberOfMessages = 2
        if len(msgList) != numberOfMessages:
            raise TypeError('UATv1 decode: The message list has not two messages. msgList:{}' .format(msgList))

        # checks that the messages in the msgList is correct
        messagesLength = 8
        if len(msgList[0]) != messagesLength or len(msgList[1]) != messagesLength:
            raise TypeError('UATv1 decode: The input message list is corrupt. len(msgList[0]):{}. len(msgList[1]):{}.'
                            .format(len(msgList[0]), len(msgList[1])))

        # creates the data dict
        data            = dict()
        message1Header = msgList[0]
        message2        = msgList[1]
        formatVersion   = 0x1

        # checks that the format version is correct
        if message1Header[3] != formatVersion:
            raise ValueError('UATv1 decode: The header message has the false version number. Header{} formatVersion{}'
                             .format(message1Header[3], formatVersion))

        # checks the message index
        if message1Header[2] != 0x0 or message2[2] != 0x1:
            raise ValueError('UATv1 decode: The header message index is false. Header{} Message2{}'
                             .format(message1Header[2], message2[2]))

        # checks that both messages have the same UAT-ID
        uatMsg1 = struct.unpack('<H', message1Header[0:2])[0]
        uatMsg2 = struct.unpack('<H', message2[0:2])[0]
        if uatMsg1 != uatMsg2:
            raise ValueError("UATv1 decode: UAT ID mismatch between UAT messages")
        data['UAT-ID'] = uatMsg1

        # decode the header message
        # gets the parameter Number and Type from the message 1 header
        crcCalcDataArry = message2
        [data['parameterNumber'], data['parameterType'], data["uatVersion"]]  = UATMainV1_V2_V3.decodeHeader(message1Header, crcCalcDataArry)

        # decode the message 2 (parameter message)
        [data['deviceId'], data['value']] = UATMainV1_V2_V3.decodeParameterMessage(data['parameterType'], message2)

        return data