from smartmicro.Protocols.uat.uatMain import ParameterType
from smartmicro.Protocols.udt.udtUatResponseMain import UAT_ResponseMain, UAT_RespErrorCode


class UATv2Response(UAT_ResponseMain):
    """
    The class encodes and decodes messages of UDT type 17000 version 3 which is an UAT Response Message for UAT message
    version 2
    """

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: __init__                                                                                               #
    # ---------------------------------------------------------------------------------------------------------------- #
    def __init__(self):
        super().__init__()
        self.data['version'] = 3
        self.data['parameterType'] = ParameterType.INTEGER_READ
        self.data['result'] = UAT_RespErrorCode.SUCCESS
        self.data['dim0'] = 0
        self.data['dim1'] = 0
        self.data['dim2'] = 0
        self.data['dim3'] = 0

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: encode                                                                                                 #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def encode(data):
        """
        Encodes a dictionary of UDT type 17000 version 3.

        Parameters
        ----------
        data        : dict
            A dict with the keys: 'UDT-Index', 'version', 'UAT-ID', 'result', 'deviceId' 'parameterNumber',
            'parameterType', 'counter', 'dim0', 'dim1', 'dim2', 'dim3' and 'value'.

        Returns
        -------
        seven byte objects representing the UAT Response Message for UAT message version 1

        Raises
        ------
        TypeError:
            if the type from the udt-index, uat-index, parameterNumber or dim0...3 is not int..
        ValueError:
            if the UDT index does not match the expected one (17000)
            if the version is not equal 3.

        """
        # Checks that the parameterNumber, the UAT-ID are an integer
        if type(data['parameterNumber']) is not int:
            raise TypeError("UDT_UAT_v2_Response encode: ParameterNumber must be of type int")
        if type(data['UAT-ID']) is not int:
            raise TypeError("UDT_UAT_v2_Response encode: UAT-ID must be of type int")
        if type(data['UDT-Index']) is not int:
            raise TypeError("UDT_UAT_v2_Response encode: UDT-Index must be of type int")
        if data['UDT-Index'] != 17000:
            raise ValueError("UDT_UAT_v2_Response encode: UDT-Index value is not 17000")
        if type(data['dim0']) is not int or type(data['dim1']) is not int or type(data['dim2']) is not int or type(
                data['dim3']) is not int:
            raise TypeError("UDT_UAT_v2_Response encode: Dimension must be of type int")
        # Check the version number
        if data['version'] != 3:
            raise ValueError("UDT_UAT_v2_Response encode: The version number is false. Expected 3 version: {}"
                             .format(data['version']))

        # Encode the header
        header = UAT_ResponseMain.encodeHeaderMessage(data['UDT-Index'], data['version'])

        # Encode the first message (parameter message)
        message1 = UAT_ResponseMain.encodeParameterTypeMessage(data['UDT-Index'] + 4, data['counter'],
                                                               data['result'].value,
                                                               data['deviceId'], data['parameterType'].value,
                                                               data['parameterNumber'])

        # Encode the third message (dim0 and dim1 message)
        message3 = UAT_ResponseMain.encodeDimMessage(data['UDT-Index'] + 6, data['counter'], data['dim0'], data['dim1'])

        # Encode the third message (dim2 and dim3 message)
        message4 = UAT_ResponseMain.encodeDimMessage(data['UDT-Index'] + 7, data['counter'], data['dim2'], data['dim3'])

        # Encode the third message (parameter value message)
        message5 = UAT_ResponseMain.encodeValueMessage(data['UDT-Index'] + 8, data['counter'], data['parameterType'],
                                                       data['value'])

        # Encode the second message and calculate the crc value
        crcCalcArrayBefore = message1[2:8]
        crcCalcArrayAfter = message3[2:8]
        crcCalcArrayAfter.extend(message4[2:8])
        crcCalcArrayAfter.extend(message5[2:8])
        message2 = UAT_ResponseMain.encodeCRCMessage(data['UDT-Index'] + 5, data['counter'], data['UAT-ID'],
                                                     crcCalcArrayBefore, crcCalcArrayAfter)

        return [header, message1, message2, message3, message4, message5, header]

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: decode                                                                                                 #
    # ---------------------------------------------------------------------------------------------------------------- #
    @staticmethod
    def decode(msgList):
        """
        Decodes a binary message of UDT type 17000 version 3 which is an UAT Response Message for UAT message version 2

        Parameters
        ----------
        msgList         : bytearray
            Contains seven byte objects each being of length 8.

        Returns
        -------
        data            : dict
            A dict with the keys: 'UDT-Index', 'version', 'UAT-ID', 'result', 'deviceId' 'parameterNumber',
            'parameterType', 'counter', 'dim0', 'dim1', 'dim2', 'dim3' and 'value'.

        Raises
        ------
        TypeError:
            if the length from each message is not equal 8.
            if the number of messages is not equal 7.
        ValueError:
            if the UDT index does not match the expected one (17000)
            if the version is not equal 3.
            if the counters from the instruction message does not match


        """
        # Checks that the msgList is correct
        numberOfMessages = 7
        if len(msgList) != numberOfMessages:
            raise TypeError('UDT_UAT_v2_Response decode: The message list has not two messages. msgList:{}'
                            .format(msgList))
        # Checks that the messages in the msgList is correct
        messagesLength = 8
        for msg in msgList:
            if len(msg) != messagesLength:
                raise TypeError('UDT_UAT_v2_Response decode: The input message list is corrupt. len(msg):{}. msgList:{}.'
                                .format(len(msg), msgList))

        # Creates the data dict
        data     = dict()
        header   = msgList[0]
        message1 = msgList[1]
        message2 = msgList[2]
        message3 = msgList[3]
        message4 = msgList[4]
        message5 = msgList[5]
        footer   = msgList[6]

        # Decode the header
        [data['UDT-Index'], data['version']] = UAT_ResponseMain.decodeHeaderMessage(header)

        # Check the version
        if data['version'] != 3:
            raise ValueError("UDT_UAT_v2_Response decode: Tried to decode a UAT response with wrong UDT type 17000 version. "
                            "Version 3 expected. Found {}".format(data['version']))
        # Check the UDI-Index from header
        if data['UDT-Index'] != 17000:
            raise TypeError("UDT_UAT_v2_Response decode: header Decoded UDT index is not 17000 instead {} was decoded"
                            .format(data['UDT-Index']))

        [index, version] = UAT_ResponseMain.decodeHeaderMessage(footer)
        # Check that the header is equal to the footer
        if index != data['UDT-Index'] or version != data['version']:
            raise ValueError("UDT_UAT_v2_Response decode: The footer is not equal the header. Header:{} Footer{}"
                             .format(header, footer))

        # Decode the message 1 (parameter type message)
        [index, counter1, data['result'], data['deviceId'], data['parameterType'],
         data['parameterNumber']] = UAT_ResponseMain.decodeParameterTypeMessage(message1)

        # Check the UDI-Index from message 1
        if index != 17004:
            raise TypeError("UDT_UAT_v2_Response decode: Decoded message 1 UDT index is not 17004 instead {} was decoded"
                            .format(index))

        # decode message 2 (crc message)
        crcCalcDataArrayBefore = message1[2:8]
        crcCalcDataArrayAfter = message3[2:8]
        crcCalcDataArrayAfter.extend(message4[2:8])
        crcCalcDataArrayAfter.extend(message5[2:8])
        [index, counter2, data['UAT-ID']] = UAT_ResponseMain.decodeCRCMessage(message2, crcCalcDataArrayBefore,
                                                                            crcCalcDataArrayAfter)
        # Check the UDI-Index from message 2
        if index != 17005:
            raise TypeError("UDT_UAT_v2_Response decode: Decoded message 2 UDT index is not 17005 instead {} was decoded"
                            .format(index))

        # Decode message 3 (dim0 and dim1 message)
        [index, counter3, data['dim0'], data['dim1']] = UAT_ResponseMain.decodeDimMessage(message3)
        # Check the UDI-Index from message 3
        if index != 17006:
            raise TypeError("UDT_UAT_v2_Response decode: Decoded message 3 UDT index is not 17006 instead {} was decoded"
                            .format(index))

        # Decode message 4 (dim2 and dim3 message)
        [index, counter4, data['dim2'], data['dim3']] = UAT_ResponseMain.decodeDimMessage(message4)
        # Check the UDI-Index from message 4
        if index != 17007:
            raise TypeError("UDT_UAT_v2_Response decode: Decoded message 4 UDT index is not 17007 instead {} was decoded"
                            .format(index))

        # Decode message 3 (parameter value message)
        [index, counter5, data['value']] = UAT_ResponseMain.decodeValueMessage(message5, data['parameterType'])
        # Check the UDI-Index from message 5
        if index != 17008:
            raise TypeError("UDT_UAT_v2_Response decode: Decoded message 5 UDT index is not 17008 instead {} was decoded"
                            .format(index))

        # Check that all three counter are the same
        if counter1 != counter2 or counter1 != counter3 or counter1 != counter4 or counter1 != counter5:
            raise ValueError('UDT_UAT_v2_Response decode: The five instruction message counters does not match. '
                             'Counter1:{} Counter2:{} Counter3:{} Counter4{} Counter5{}'
                             .format(counter1, counter2, counter3, counter4, counter5))
        data['counter'] = counter1
        return data