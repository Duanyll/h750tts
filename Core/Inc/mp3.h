/*
 * mp3.h
 *
 *  Created on: Apr 6, 2023
 *      Author: WR
 */

#ifndef INC_MP3_H_
#define INC_MP3_H_

#include <diskio.h>
#include <ff.h>
#include <ff_gen_drv.h>
#include <mp3dec.h>
#include <string.h>
#endif /* INC_MP3_H_ */

typedef struct __packed {
  uint8_t id[3];   
  uint8_t mversion;
  uint8_t sversion;
  uint8_t flags;   
  uint8_t size[4]; 
} ID3V2_TagHead;

typedef struct {
  uint8_t *readFilePtr;
  uint8_t *endFilePtr;
  HMP3Decoder decoder;
  MP3FrameInfo lastFrameInfo;
  int32_t dmaBufferSize; // number of samples in one DMA buffer frame

  uint8_t isPlaying;
  uint8_t bufferToFill;
  uint8_t shouldStop;
  int volume;

  uint8_t outChannels; // 0x01 for left, 0x02 for right, 0x03 for both

} Mp3DecodeState;

#define MP3_OK 0
#define MP3_FAIL -1

#define MP3_FILE_BUFFER_SIZE 32 * 1024
#define MP3_DECODE_BUFFER_SIZE 1152 * 2
#define MP3_DMA_BUFFER_SIZE MP3_DECODE_BUFFER_SIZE * 2
#define MP3_INDEX_BUFFER_SIZE 16 * 1024 / 4
#define MP3_DICT_BUFFER_SIZE 64 * 1024 / 4

#define MP3_MAX_VOLUME 100
#define MP3_QUEUE_SIZE 128

uint8_t I2S_WaitFlagStateUntilTimeout(I2S_HandleTypeDef *hi2s, uint32_t Flag,
                                      uint32_t Status, uint32_t Timeout);

int MP3_Init();
int MP3_Enqueue(int fileId);
int MP3_Speak(char *str);
int MP3_SetVolume(int vol);
int MP3_GetVolume();
int MP3_StopPlay(int clearQueue);
int MP3_PollBuffer();
int MP3_GetIsPlaying();