#include "mp3dec.h"
#include "stdint.h"
#include "stdio.h"
#include "stdlib.h"

typedef struct __packed {
  uint8_t id[3];
  uint8_t mversion;
  uint8_t sversion;
  uint8_t flags;
  uint8_t size[4];
} ID3V2_TagHead;

typedef struct {
  uint8_t* readFilePtr;
  uint8_t* endFilePtr;
  HMP3Decoder decoder;
  MP3FrameInfo lastFrameInfo;
} Mp3DecodeState;

#define FILE_BUFFER_SIZE 32 * 1024
uint8_t file_buffer[FILE_BUFFER_SIZE];
#define DECODE_BUFFER_SIZE 1152 * 2
int16_t decode_buffer[DECODE_BUFFER_SIZE];

int Mp3DecodeFrame(Mp3DecodeState* state) {
  int offset = MP3FindSyncWord(state->readFilePtr, FILE_BUFFER_SIZE);
  if (offset < 0) {
    printf("MP3FindSyncWord failed\n");
    return -1;
  }
  state->readFilePtr += offset;
  int bytesLeft = state->endFilePtr - state->readFilePtr;
  int err = MP3Decode(state->decoder, &state->readFilePtr, &bytesLeft,
                      decode_buffer, 0);
  if (err != 0) {
    printf("MP3Decode failed\n");
    return -1;
  }
  MP3GetLastFrameInfo(state->decoder, &state->lastFrameInfo);
  printf("MP3 frame decoded: %d samples, %d channels, %d Hz\n",
         state->lastFrameInfo.outputSamps, state->lastFrameInfo.nChans,
         state->lastFrameInfo.samprate);
  return 0;
}

int Mp3Init(Mp3DecodeState* state, uint8_t* file_buffer, uint32_t file_size) {
  state->readFilePtr = file_buffer;
  state->endFilePtr = file_buffer + file_size;
  if (state->decoder == NULL) {
    state->decoder = MP3InitDecoder();
  }
  // Parse ID3V2 tag
  ID3V2_TagHead* tag = (ID3V2_TagHead*)file_buffer;
  if (tag->id[0] == 'I' && tag->id[1] == 'D' && tag->id[2] == '3') {
    printf("ID3V2 tag found\n");
    uint32_t size = (tag->size[0] << 21) | (tag->size[1] << 14) |
                    (tag->size[2] << 7) | (tag->size[3]);
    printf("ID3V2 tag size: %d\n", size);
    state->readFilePtr += size;
  }
  return 0;
}

#define INDEX_BUFFER_SIZE 16 * 1024 / 4
uint32_t index_buffer[INDEX_BUFFER_SIZE];
int index_size;
#define DICT_BUFFER_SIZE 64 * 1024 / 4
uint32_t dict_buffer[DICT_BUFFER_SIZE]; // Interleave code and index
int dict_size;

int Mp3LoadIndexAndDict() {
  char* indexFile = "D:/source/stm32/h750tts/voice_pack/voice_pack.index";
  // Just load index file to memory
  FILE* fp = fopen(indexFile, "rb");
  if (fp == NULL) {
    printf("open index file failed\n");
    return -1;
  }
  index_size = fread(index_buffer, 1, INDEX_BUFFER_SIZE * 4, fp);
  index_size = index_size / 4;
  printf("index size: %d\n", index_size);
  fclose(fp);
  // Load dict file to memory
  char* dictFile = "D:/source/stm32/h750tts/voice_pack/voice_pack.dict";
  fp = fopen(dictFile, "rb");
  if (fp == NULL) {
    printf("open dict file failed\n");
    return -1;
  }
  dict_size = fread(dict_buffer, 1, DICT_BUFFER_SIZE * 4, fp);
  dict_size = dict_size / 8;
  printf("dict size: %d\n", dict_size);
  fclose(fp);
}

int Mp3FindIndexFromDict(int code) {
  // Binary search code in dict
  int left = 0;
  int right = dict_size - 1;
  while (left <= right) {
    int mid = (left + right) / 2;
    if (dict_buffer[mid * 2] == code) {
      return dict_buffer[mid * 2 + 1];
    } else if (dict_buffer[mid * 2] < code) {
      left = mid + 1;
    } else {
      right = mid - 1;
    }
  }
  return -1;
}

// Parse a utf8 string to unicode, return current char code like python ord()
uint32_t ParseUtf8(char** str) {
  uint8_t c = **str;
  if (c < 0x80) {
    (*str)++;
    return c;
  }
  if ((c & 0xe0) == 0xc0) {
    (*str) += 2;
    return ((c & 0x1f) << 6) | ((*str)[-1] & 0x3f);
  }
  if ((c & 0xf0) == 0xe0) {
    (*str) += 3;
    return ((c & 0x0f) << 12) | (((*str)[-2] & 0x3f) << 6) |
           ((*str)[-1] & 0x3f);
  }
  if ((c & 0xf8) == 0xf0) {
    (*str) += 4;
    return ((c & 0x07) << 18) | (((*str)[-3] & 0x3f) << 12) |
           (((*str)[-2] & 0x3f) << 6) | ((*str)[-1] & 0x3f);
  }
  return -1;
}

Mp3DecodeState state;

int main() {
  Mp3LoadIndexAndDict();
  char* binFile = "D:/source/stm32/h750tts/voice_pack/voice_pack.bin";
  FILE* fp = fopen(binFile, "rb");
  if (fp == NULL) {
    printf("open bin file failed\n");
    return -1;
  }

  char* str = "你好";
  char* p = str;
  char* outfile = "D:/source/stm32/h750tts/voice_pack/a.raw";
  FILE* fout = fopen(outfile, "w");
  while (*p) {
    int code = ParseUtf8(&p);
    printf("Code: %d\n", code);
    int index = Mp3FindIndexFromDict(code);
    printf("Index: %d\n", index);
    if (index >= 0) {
      int offset = index_buffer[index];
      int length = index_buffer[index + 1] - offset;
      printf("Offset: %d, length: %d\n", offset, length);
      fseek(fp, offset, SEEK_SET);
      fread(file_buffer, 1, length, fp);

      Mp3Init(&state, file_buffer, length);
      while (state.readFilePtr < state.endFilePtr) {
        if (Mp3DecodeFrame(&state) != 0) {
          break;
        }
        int maxAmp = 0;
        for (int i = 0; i < state.lastFrameInfo.outputSamps; i++) {
          fprintf(fout, "%d\n", decode_buffer[i]);
        }
      }
    }
  }
  
  fclose(fp);
  fclose(fout);
}