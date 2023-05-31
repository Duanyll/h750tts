# example data from kMandarin_8105
"""
U+4E00: yī  # 一
U+4E01: dīng  # 丁
U+4E03: qī  # 七
U+4E07: wàn  # 万
U+4E08: zhàng  # 丈
U+4E09: sān  # 三
"""

# Transform to:
"""
一 yi1
丁 ding1
七 qi1
万 wan4
丈 zhang4
三 san1
"""

tones = {
    'ā': 'a1',
    'á': 'a2',
    'ǎ': 'a3',
    'à': 'a4',
    'ē': 'e1',
    'é': 'e2',
    'ě': 'e3',
    'è': 'e4',
    'ī': 'i1',
    'í': 'i2',
    'ǐ': 'i3',
    'ì': 'i4',
    'ō': 'o1',
    'ó': 'o2',
    'ǒ': 'o3',
    'ò': 'o4',
    'ū': 'u1',
    'ú': 'u2',
    'ǔ': 'u3',
    'ù': 'u4',
    'ǖ': 'v1',
    'ǘ': 'v2',
    'ǚ': 'v3',
    'ǜ': 'v4',
}

def convert_line(line: str) -> str:
    code = line.split(':')[0].lstrip('U+')
    pinyin = line[8:].split()[0]
    char = chr(int(code, 16))
    has_tone = False
    for i in range(len(pinyin)):
        if pinyin[i] in tones:
            tone = tones[pinyin[i]]
            pinyin = pinyin[:i] + tone[0] + pinyin[i+1:] + tone[1]
            has_tone = True
            break
    if not has_tone:
        pinyin += '6'
    return char + ' ' + pinyin + '\n'

def convert_file(infile: str, outfile) -> None:
    with open(infile, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    with open(outfile, 'w', encoding='utf-8') as f:
        for line in lines:
            if line[0] != '#':
                f.write(convert_line(line))

if __name__ == '__main__':
    convert_file('omv/utils/kMandarin_8105.txt', 'omv/device/pinyin_data.txt')
    