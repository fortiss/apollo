from smartmicro.Protocols.uat.uatMain import ParameterType
from smartmicro.Protocols.udt.udtUatResponseMain import UAT_ResponseMain, UAT_RespErrorCode


class UATv3Response(UAT_ResponseMain):
    """
    The class encodes and decodes messages of UDT type 17000 version 4 which is an UAT Response Message for UAT message
    version 3
    """

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: __init__                                                                                               #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __init__(self):
        super().__init__()
        self.data['version'] = 4
        self.data['parameterType'] = ParameterType.INTEGER_READ
        self.data['result'] = UAT_RespErrorCode.SUCCESS
        self.data['dim0'] = 0
        self.data['dim1'] = 0
        self.data['dim2'] = 0
        self.data['dim3'] = 0
        self.data['dim4'] = 0
        self.data['dim5'] = 0
        self.data['dim6'] = 0
        self.data['dim7'] = 0

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: encode                                                                                                 #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def encode(data):
        """
        Encodes a dictionary of UDT type 17000 version 4.

        Parameters
        ----------
        data    : dict
            A dict with the keys: 'UDT-Index', 'version', 'UAT-ID', 'result', 'deviceId' 'parameterNumber',
            'parameterType', 'counter', 'dim0', 'dim1', 'dim2', 'dim3', 'dim4', 'dim5', 'dim6', 'dim7' and 'value'.

        Returns
        -------
        Nine byte objects representing the UAT Response Message for UAT message version 1

        Raises
        ------
        TypeError:
            if the type from the udt-index, uat-index, parameterNumber or dim0...7 is not int.
        ValueError:
            if the UDT index does not match the expected one (17000)
            if the version is not equal 4

        """
        # Checks that the parameterNumber, the UAT-ID are an integer
        if type(data['parameterNumber']) is not int:
            raise TypeError("UDT_UAT_v3_Response encode: ParameterNumber must be of type int")
        if type(data['UAT-ID']) is not int:
            raise TypeError("UDT_UAT_v3_Response encode: UAT-ID must be of type int")
        if type(data['UDT-Index']) is not int:
            raise TypeError("UDT_UAT_v3_Response encode: UDT-Index must be of type int")
        if data['UDT-Index'] != 17000:
            raise ValueError("UDT_UAT_v3_Response encode: UDT-Index value is not 17000")
        if type(data['dim0']) is not int or type(data['dim1']) is not int or type(data['dim2']) is not int or type(
                data['dim3']) is not int or type(data['dim4']) is not int or type(data['dim5']) is not int or type(
                data['dim6']) is not int or type(data['dim7']) is not int:
            raise TypeError("UDT_UAT_v3_Response encode: Dimension must be of type int")
        # Check the version number
        if data['version'] != 4:
            raise ValueError("UDT_UAT_v3_Response encode: The version number is false. Expected 4 version: {}"
                             .format(data['version']))

        # Encode the header
        header = UAT_ResponseMain.encodeHeaderMessage(data['UDT-Index'], data['version'])

        # Encode the first message (parameter message)
        message1 = UAT_ResponseMain.encodeParameterTypeMessage(data['UDT-Index'] + 9, data['counter'],
                                                               data['result'].value,
                                                               data['deviceId'], data['parameterType'].value,
                                                               data['parameterNumber'])

        # Encode the third message (dim0 and dim1 message)
        message3 = UAT_ResponseMain.encodeDimMessage(data['UDT-Index'] + 11, data['counter'], data['dim0'], data['dim1'])

        # Encode the 4th message (dim2 and dim3 message)
        message4 = UAT_ResponseMain.encodeDimMessage(data['UDT-Index'] + 12, data['counter'], data['dim2'], data['dim3'])

        # Encode the 5th message (dim4 and dim5 message)
        message5 = UAT_ResponseMain.encodeDimMessage(data['UDT-Index'] + 13, data['counter'], data['dim4'], data['dim5'])

        # Encode the 6th message (dim6 and dim7 message)
        message6 = UAT_ResponseMain.encodeDimMessage(data['UDT-Index'] + 14, data['counter'], data['dim6'], data['dim7'])

        # Encode the 7th message (parameter value message)
        message7 = UAT_ResponseMain.encodeValueMessage(data['UDT-Index'] + 15, data['counter'], data['parameterType'],
                                                       data['value'])

        # Encode the second message and calculate the crc value
        crcCalcArrayBefore = message1[2:8]
        crcCalcArrayAfter  = message3[2:8]
        crcCalcArrayAfter.extend(message4[2:8])
        crcCalcArrayAfter.extend(message5[2:8])
        crcCalcArrayAfter.extend(message6[2:8])
        crcCalcArrayAfter.extend(message7[2:8])
        message2 = UAT_ResponseMain.encodeCRCMessage(data['UDT-Index'] + 10, data['counter'], data['UAT-ID'],
                                                     crcCalcArrayBefore, crcCalcArrayAfter)

        return [header, message1, message2, message3, message4, message5, message6, message7, header]

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: decode                                                                                                 #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def decode(msgList):
        """
        Decodes a binary message of UDT type 17000 version 4 which is an UAT Response Message for UAT message version 3.

        Parameters
        ----------
        msgList         : bytearray
            Contains nine byte objects each being of length 8.

        Returns
        -------
        data            : dict
            A dict with the keys: 'UDT-Index', 'version', 'UAT-ID', 'result', 'deviceId' 'parameterNumber',
            'parameterType', 'counter', 'dim0', 'dim1', 'dim2', 'dim3', 'dim4', 'dim5', 'dim6', 'dim7' and 'value'.

        Raises
        ------
        TypeError:
            if the length from each message is not equal 8.
            if the number of messages is not equal 9.
        ValueError:
            if the UDT index does not match the expected one (17000)
            if the version is not equal 4
            if the counters from the instruction message does not match

        """
        # Check that the msgList is correct
        numberOfMessages = 9
        if len(msgList) != numberOfMessages:
            raise TypeError('UDT_UAT_v3_Response decode: The message list has not two messages. msgList:{}'
                            .format(msgList))
        # Check that the messages in the msgList is correct
        messagesLength = 8
        for msg in msgList:
            if len(msg) != messagesLength:
                raise TypeError('UDT_UAT_v3_Response decode: The input message list is corrupt. len(msg):{}. msgList:{}.'
                                .format(len(msg), msgList))

        # Create the data dict
        data = dict()
        header = msgList[0]
        message1 = msgList[1]
        message2 = msgList[2]
        message3 = msgList[3]
        message4 = msgList[4]
        message5 = msgList[5]
        message6 = msgList[6]
        message7 = msgList[7]
        footer = msgList[8]

        # Decode the header
        [data['UDT-Index'], data['version']] = UAT_ResponseMain.decodeHeaderMessage(header)

        # Check the version
        if data['version'] != 4:
            raise ValueError("UDT_UAT_v3_Response decode: Tried to decode a UAT response with wrong UDT type 17000 version. "
                            "Version 4 expected. Found {}".format(data['version']))
        # Check the UDI-Index from header
        if data['UDT-Index'] != 17000:
            raise TypeError("UDT_UAT_v3_Response decode: header Decoded UDT index is not 17000 instead {} was decoded"
                            .format(data['UDT-Index']))

        [index, version] = UAT_ResponseMain.decodeHeaderMessage(footer)
        # Check that the header is equal to the footer
        if index != data['UDT-Index'] or version != data['version']:
            raise ValueError("UDT_UAT_v3_Response decode: The footer is not equal the header. Header:{} Footer{}"
                             .format(header, footer))

        # Decode the message 1 (parameter type message)
        [index, counter1, data['result'], data['deviceId'], data['parameterType'],
         data['parameterNumber']] = UAT_ResponseMain.decodeParameterTypeMessage(message1)

        # Check the UDI-Index from message 1
        if index != 17009:
            raise TypeError("UDT_UAT_v3_Response decode: Decoded message 1 UDT index is not 17009 instead {} was decoded"
                            .format(index))

        # decode message 2 (crc message)
        crcCalcDataArrayBefore = message1[2:8]
        crcCalcDataArrayAfter = message3[2:8]
        crcCalcDataArrayAfter.extend(message4[2:8])
        crcCalcDataArrayAfter.extend(message5[2:8])
        crcCalcDataArrayAfter.extend(message6[2:8])
        crcCalcDataArrayAfter.extend(message7[2:8])
        [index, counter2, data['UAT-ID']] = UAT_ResponseMain.decodeCRCMessage(message2, crcCalcDataArrayBefore,
                                                                            crcCalcDataArrayAfter)
        # Check the UDI-Index from message 2
        if index != 17010:
            raise ValueError("UDT_UAT_v3_Response decode: Decoded message 2 UDT index is not 17010 instead {} was decoded"
                            .format(index))

        # Decode message 3 (dim0 and dim1 message)
        [index, counter3, data['dim0'], data['dim1']] = UAT_ResponseMain.decodeDimMessage(message3)
        # Check the UDI-Index from message 3
        if index != 17011:
            raise ValueError("UDT_UAT_v3_Response decode: Decoded message 3 UDT index is not 17011 instead {} was decoded"
                            .format(index))

        # Decode message 4 (dim2 and dim3 message)
        [index, counter4, data['dim2'], data['dim3']] = UAT_ResponseMain.decodeDimMessage(message4)
        # Check the UDI-Index from message 4
        if index != 17012:
            raise ValueError("UDT_UAT_v3_Response decode: Decoded message 4 UDT index is not 17012 instead {} was decoded"
                            .format(index))

        # Decode message 5 (dim4 and dim5 message)
        [index, counter5, data['dim4'], data['dim5']] = UAT_ResponseMain.decodeDimMessage(message5)
        # Check the UDI-Index from message 3
        if index != 17013:
            raise ValueError("UDT_UAT_v3_Response decode: Decoded message 5 UDT index is not 17013 instead {} was decoded"
                            .format(index))

        # Decode message 6 (dim6 and dim7 message)
        [index, counter6, data['dim6'], data['dim7']] = UAT_ResponseMain.decodeDimMessage(message6)
        # Check the UDI-Index from message 4
        if index != 17014:
            raise ValueError("UDT_UAT_v3_Response decode: Decoded message 6 UDT index is not 17014 instead {} was decoded"
                            .format(index))

        # Decode message 7 (parameter value message)
        [index, counter7, data['value']] = UAT_ResponseMain.decodeValueMessage(message7, data['parameterType'])
        # Check the UDI-Index from message 5
        if index != 17015:
            raise ValueError("UDT_UAT_v3_Response decode: Decoded message 7 UDT index is not 17015 instead {} was decoded"
                            .format(index))

        # Check that all seven counter are the same
        if counter1 != counter2 or counter1 != counter3 or counter1 != counter4 or counter1 != counter5 or \
                        counter1 != counter6 or counter1 != counter7:
            raise ValueError('UDT_UAT_v3_Response decode: The seven instruction message counters does not match. '
                             'Counter1:{} Counter2:{} Counter3:{} Counter4:{} Counter5:{} Counter6:{} Counter7:{}'
                             .format(counter1, counter2, counter3, counter4, counter5, counter6, counter7))
        data['counter'] = counter1
        return data