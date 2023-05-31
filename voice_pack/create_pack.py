import os

def create_pack(speech_dir, pinyin_file, output_dir):
    # List all files in speech_dir
    files = os.listdir(speech_dir)
    files = [f for f in files if f.endswith('.mp3')]
    files.sort()

    out_bin_file = os.path.join(output_dir, 'BIN')
    out_index_file = os.path.join(output_dir, 'INDEX')

    # open output files
    bin_file = open(out_bin_file, 'wb')
    index_file = open(out_index_file, 'wb')

    id_dict = {}

    # concat all files into bin file, and write offsets to index file
    offset = 0
    for i, f in enumerate(files):
        index_file.write(offset.to_bytes(4, 'little'))
        offset += os.path.getsize(os.path.join(speech_dir, f))
        bin_file.write(open(os.path.join(speech_dir, f), 'rb').read())
        id_dict[f[:-4]] = i
    index_file.write(offset.to_bytes(4, 'little'))

    bin_file.close()
    index_file.close()

    # open pinyin file
    pinyin_file = open(pinyin_file, 'r', encoding='utf-8')
    char_dict = []
    for line in pinyin_file:
        line = line.rstrip('\n')
        char, pinyin = line.split(' ')
        if pinyin in id_dict:
            # Get utf-8 int value of char
            char_dict.append((ord(char), id_dict[pinyin]))
        else: 
            print('Warning: {} not found in id_dict'.format(pinyin))
    pinyin_file.close()

    # sort char_dict by utf-8 int value of char
    char_dict.sort(key=lambda x: x[0])

    dict_file = open(os.path.join(output_dir, 'DICT'), 'wb')
    for char, id in char_dict:
        dict_file.write(char.to_bytes(4, 'little'))
        dict_file.write(id.to_bytes(4, 'little'))
    dict_file.close()

if __name__ == '__main__':
    create_pack('D:/Downloads/zhspeak_6.1.2_generic/zhspeak-data/zh_dir/',
                './omv/device/pinyin_data.txt',
                './voice_pack/')
