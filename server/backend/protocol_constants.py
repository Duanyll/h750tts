# data format: [0x19260817][type (1)][is last (1)][length (4)][data]
# type 0x00: Terminating connection (length is not present)
# type 0x01: None (length is not present)
# type 0x02: JPEG image
# type 0x03: WAV audio
# type 0x04: JSON

HEADER = b'\x19\x26\x08\x17'
TYPE_TERMINATE = 0x00
TYPE_NONE = 0x01
TYPE_IMAGE = 0x02
TYPE_AUDIO = 0x03
TYPE_JSON = 0x04
