from smartmicro.Protocols.uat.uatMain import ParameterType


class cspSendVersion1():

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: buildMessageDict                                                                                       #
    # ---------------------------------------------------------------------------------------------------------------- #
    @classmethod
    def buildMessageDict(cls, sectionName, paramName, parameters, uatVersion=3, value=None, write=True, read=True):
        """
        The function encodes the uat version 1-3.

        Parameters
        ----------
        sectionName : string
            section name of used parameter
        paramName   : string
            name of used parameter
        parameters  : dictionary
            dictionary with section and parameter information
        uatVersion  : integer
            current used uat version
        value       : integer or float
            current value to be set
        write       : bool
            assign writing of the data
        read        : bool
            assign reading of the data

        Returns
        -------
        param       : dictionary
            dictionary with uat data
        """
        # generate empty parameter dictionary
        param                    = dict()
        # set section ID
        param['UAT-ID']          = parameters[sectionName]['section']
        # get parameter from dictionary
        paramDict                = cls.extractSingleParamDict(paramName, sectionName, parameters)
        # set parameter number
        param['parameterNumber'] = paramDict['id']
        # evaluate parameter type
        param['parameterType']   = cls.evaluateParamType( paramDict['type'], write, read )
        # set parameter value
        param['value']           = value
        # set default device ID
        param['deviceId']        = 0
        # check if parameter is dimensional
        if "dimensions" in parameters[sectionName].keys():
            if uatVersion > 1:
                param["uatVersion"]  = 2
            else:
                param["uatVersion"]  = 1
        else:
            param["uatVersion"]  = 1

        return param


    # ---------------------------------------------------------------------------------------------------------------- #
    # function: addMessageExtension1                                                                                   #
    # ---------------------------------------------------------------------------------------------------------------- #
    @classmethod
    def addMessageExtension1(cls, element):
        """
        The function encodes the dimension data for uat version 2.

        Parameters
        ----------
        element     : integer / list of integer
            dimensional data

        Returns
        -------
        param       : dictionary
            dictionary with uat version 2 dimension data
        """
        if element is None:
            element = 0
        # check if element is None type element
        elementList = list()
        # check if element is list-type element
        if type(element) is not list:
            elementList.append(element)
        else:
            elementList = element
        # check length of list
        if len (elementList) < 4:
            while len(elementList) < 4:
                elementList.append(0)

        # generate empty parameter dictionary
        param = dict()
        # parameter dimension set
        param['dim0'] = elementList[0]
        param['dim1'] = elementList[1]
        param['dim2'] = elementList[2]
        param['dim3'] = elementList[3]

        return param

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: addMessageExtension2                                                                                   #
    # ---------------------------------------------------------------------------------------------------------------- #
    @classmethod
    def addMessageExtension2(cls, dimension, element):
        """
        The function encodes the dimension data for uat version 3.

        Parameters
        ----------
        dimension   : integer
            array dimension. Not used
        element     : integer / list of integer
            dimensional data

        Returns
        -------
        param       : dictionary
            dictionary with uat version 3 dimension data
        """
        if element is None:
            element = 0
        # check if element is None type element
        elementList = list()
        # check if element is list-type element
        if type(element) is not list:
            elementList.append(element)
        else:
            elementList = element
        # check length of list
        if len(elementList) < 8:
            while len(elementList) < 8:
                elementList.append(0)

        # generate empty parameter dictionary
        param = dict()
        # parameter dimension set
        param['dim4'] = elementList[4]
        param['dim5'] = elementList[5]
        param['dim6'] = elementList[6]
        param['dim7'] = elementList[7]

        return param

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: evaluateParamType                                                                                      #
    # ---------------------------------------------------------------------------------------------------------------- #
    @classmethod
    def evaluateParamType(cls, rawType, write, read):
        """
        The function encodes the type of variable and the access type.

        Parameters
        ----------
        rawType     : string
            assign float or integer variable
        write       : bool
            assign writing of the data
        read        : bool
            assign reading of the data

        Returns
        -------

        """
        if rawType == "f32":
            if write and not read:
                paramType = ParameterType.IEEE_FLOAT_WRITE
            elif write and read:
                paramType = ParameterType.IEEE_FLOAT_RW
            else:
                paramType = ParameterType.IEEE_FLOAT_READ
        else:
            if write and not read:
                paramType = ParameterType.INTEGER_WRITE
            elif write and read:
                paramType = ParameterType.INTEGER_RW
            else:
                paramType = ParameterType.INTEGER_READ

        return paramType

    # ---------------------------------------------------------------------------------------------------------------- #
    # function: extractSingleParamDict                                                                                 #
    # ---------------------------------------------------------------------------------------------------------------- #
    @classmethod
    def extractSingleParamDict(cls, paramName, sectionName, parameter_dict):
        """
        The function extracts data from the dictionary.

        Parameters
        ----------
        paramName       : string
            name of the parameter
        sectionName     : string
            name of the parameter section
        parameter_dict  : dictionary
            dictionary with section and parameter information

        Returns
        -------
        paramDict       : dictionary
            dictionary with parameter information
        """

        try:
            pList = parameter_dict[sectionName]['parameters']
        except BaseException:
            pass

        try:
            pList = parameter_dict[sectionName]['status']
        except BaseException:
            pass

        paramDictList = [d for d in pList if d.get('name') == paramName]
        if len(paramDictList) == 0:
            raise KeyError("Parameter with name {}.{} does not exist".format(sectionName,paramName))

        if len(paramDictList) > 1:
            raise ValueError("Parameter with doublicated name detected {}".format(paramDictList))
        paramDict = paramDictList[0]
        return paramDict