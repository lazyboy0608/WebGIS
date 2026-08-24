from enum import IntEnum


class SeismicDataFormat(IntEnum):
    IBM_FLOAT_4_BYTE = 1
    INTEGER_4_BYTE = 2
    INTEGER_2_BYTE = 3
    FIXED_POINT_WITH_GAIN = 4
    IEEE_FLOAT_4_BYTE = 5
    IEEE_FLOAT_8_BYTE = 6
    INTEGER_3_BYTE = 7
    INTEGER_1_BYTE = 8