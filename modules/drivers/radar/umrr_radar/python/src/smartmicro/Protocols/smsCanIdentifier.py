from enum import Enum, unique


@unique
class SMSCanIdentifier_Automotive(Enum):
    UDT_IDENTIFIER = 0x700
    UAT_IDENTIFIER = 0x3fb


class SMSCanIdentifier(Enum):
    BOOTLOADER_IDENTIFIER = 0x320