/*
 * mp3.c
 *
 *  Created on: Apr 6, 2023
 *      Author: WR
 */

#include "mp3.h"
#include "i2s.h"

#define SPEED \
  3  // interval between characters.  2 is normal(typical) , and 3 is faster.

uint8_t WaveFileBuf[WAVEFILEBUFSIZE];
uint8_t TempBuf[WAVETEMPBUFSIZE];
wavctrl WaveCtrlData;
uint8_t CloseFileFlag;  // 1:already open file have to close it
uint8_t EndFileFlag;    // 1:reach the wave file end;2:wait for last
                        // transfer;3:finish transfer stop dma
uint8_t FillBufFlag;    // 0:fill first half buf;1:fill second half buf;0xff do
                        // nothing
uint32_t DmaBufSize;
uint8_t Mp3DecodeBuf[DECODEBUFSIZE];
uint8_t canplay;
FIL Mp3File;
mp3Info Mp3Info;
uint8_t *Readptr;  // MP3解码读指针
int32_t ByteLeft;  // buffer还剩余的有效数据
uint8_t InitMp3InfoFlag;
HMP3Decoder Mp3Decoder;
int startAddr[2600];
char dict[2600][20];
int fileLength[2600];
int currentFile, fileCount;

#define MP3_QUEUE_SIZE 128
int MP3_Queue[MP3_QUEUE_SIZE];  // Circular Queue
int MP3_QueueHead, MP3_QueueTail;

#define MP3_OK 0
#define MP3_FAIL 1

void HAL_I2S_TxHalfCpltCallback(I2S_HandleTypeDef *hi2s) {
  if (EndFileFlag == 0) {
    FillBufFlag = 0;
  } else if (EndFileFlag == 1) {
    memset(WaveFileBuf, 0, DmaBufSize / 2);
    EndFileFlag = 2;
  } else if (EndFileFlag == 2)
    EndFileFlag = 3;
}

void HAL_I2S_TxCpltCallback(I2S_HandleTypeDef *hi2s) {
  if (EndFileFlag == 0) {
    FillBufFlag = 1;
  } else if (EndFileFlag == 1) {
    memset(&WaveFileBuf[DmaBufSize / 2], 0, DmaBufSize / 2);
    EndFileFlag = 2;
  } else if (EndFileFlag == 2)
    EndFileFlag = 3;
}

int MP3_Init() {
  canplay = 1;
  FIL dictFile;
  f_open(&dictFile, "0:/DICT.TXT", FA_READ);
  char line[50];
  int br;
  f_read(&dictFile, line, 30, &br);
  int i = 1;
  while (br) {
    char *p = strtok(line, "\t");
    strcpy(dict[i], p);
    p = strtok(NULL, "\t");
    startAddr[i] = atoi(p);
    p = strtok(NULL, "\t");
    fileLength[i] = atoi(p) - startAddr[i];
    i++;
    f_read(&dictFile, line, 30, &br);
  }
  fileCount = i - 1;
  f_close(&dictFile);
  f_open(&Mp3File, "0:/TARGET", FA_READ);

  MP3_QueueHead = MP3_QueueTail = 0;

  return MP3_OK;
}

int MP3_FindFile(char* pinyin) {
  char mp3FileName[20];
  strcpy(mp3FileName, pinyin);
  strcat(mp3FileName, ".mp3");
  int l = 1, r = fileCount, mid;
  while (l < r) {
    mid = (l + r + 1) >> 1;
    if (strcmp(mp3FileName, dict[mid]) < 0)
      r = mid - 1;
    else
      l = mid;
  }
  return l;
}

int MP3_Enqueue(char* pinyin) {
  int fileId = MP3_FindFile(pinyin);
  if (MP3_QueueHead == (MP3_QueueTail + 1) % MP3_QUEUE_SIZE) return MP3_FAIL;
  MP3_Queue[MP3_QueueTail] = fileId;
  MP3_QueueTail = (MP3_QueueTail + 1) % MP3_QUEUE_SIZE;
  return MP3_OK;
}

int MP3_StartPlayAsync(int fileId) {
  if (canplay == 0) return MP3_FAIL;
  canplay = 0;

  uint8_t res = 0;
  uint32_t br = 0;
  uint32_t Mp3DataStart = 0;
  CloseFileFlag = 0;
  EndFileFlag = 0;
  FillBufFlag = 0xFF;
  ID3V2_TagHead *TagHead;
  CloseFileFlag = 1;

  currentFile = fileId;

  f_lseek(&Mp3File, startAddr[currentFile]);
  res = f_read(&Mp3File, TempBuf, fileLength[currentFile], &br);

  TagHead = (ID3V2_TagHead *)TempBuf;

  if (strncmp("ID3", (const char *)TagHead->id, 3) == 0) {
    Mp3Info.DataStart = ((uint32_t)TagHead->size[0] << 21) |
                        ((uint32_t)TagHead->size[1] << 14) |
                        ((uint32_t)TagHead->size[2] << 7) | TagHead->size[3];
  }

  if (!Mp3Decoder) {
    Mp3Decoder = MP3InitDecoder();
  }

  Readptr = TempBuf;
  ByteLeft = br;
  InitMp3InfoFlag = 0;

  while (EndFileFlag == 0) {
    res = MP3_FillBuffer(WaveFileBuf);
    if (res == 0) break;
  }
  DmaBufSize =
      Mp3Info.OutSamples * Mp3Info.bitsPerSample * 4 / (8 * Mp3Info.nChans);
  MP3_FillBuffer(WaveFileBuf + DmaBufSize / 2);
  if (res != 0) {
    if (CloseFileFlag) {
      f_close(&Mp3File);
      CloseFileFlag = 0;
    }
    MP3FreeDecoder(Mp3Decoder);
    return res;
  }
  HAL_GPIO_WritePin(PCM5102A_XMT_GPIO_Port, PCM5102A_XMT_Pin, GPIO_PIN_SET);
  HAL_I2S_Transmit_DMA(&hi2s1, (uint16_t *)WaveFileBuf, DmaBufSize / 2);

  return MP3_OK;
}

int MP3_PollBuffer() {
  if (EndFileFlag == 0) {
    if (FillBufFlag == 0) {
      MP3_FillBuffer(WaveFileBuf);
      FillBufFlag = 0xFF;
    } else if (FillBufFlag == 1) {
      MP3_FillBuffer(&WaveFileBuf[DmaBufSize / 2]);
      FillBufFlag = 0xFF;
    }
  } else if (EndFileFlag == 3) {
    HAL_GPIO_WritePin(PCM5102A_XMT_GPIO_Port, PCM5102A_XMT_Pin, GPIO_PIN_RESET);
    canplay = 1;

    // Try to play next song
    if (MP3_QueueHead != MP3_QueueTail) {
      MP3_StartPlayAsync(MP3_Queue[MP3_QueueHead]);
      MP3_QueueHead = (MP3_QueueHead + 1) % MP3_QUEUE_SIZE;
    }
  }
  return MP3_OK;
}

uint32_t MP3_FillBuffer(uint8_t *Buf) {
  uint32_t br = 0;
  int32_t Offset;
  int32_t err = 0;
  int32_t i;
  uint16_t *PlayPtr;
  uint16_t *Mp3Ptr;
  MP3FrameInfo Mp3FrameInfo;

  Offset =
      MP3FindSyncWord(Readptr, ByteLeft);  // 在readptr位置,开始查找同步字符
  if (Offset < 0)  // 没有找到同步字符,跳出帧解码循环
  {
    return MP3_FAIL;
  }
  Readptr += Offset;   // MP3读指针偏移到同步字符处.
  ByteLeft -= Offset;  // buffer里面的有效数据个数,必须减去偏移量

  if (ByteLeft < MAINBUF_SIZE * SPEED) {
    EndFileFlag = 1;
  }

  err = MP3Decode(Mp3Decoder, &Readptr, &ByteLeft, (int16_t *)Mp3DecodeBuf,
                  0);  // 解码一帧MP3数据

  if (err != 0) {
    return MP3_FAIL;
  }

  if (InitMp3InfoFlag == 0) {
    MP3GetLastFrameInfo(Mp3Decoder, &Mp3FrameInfo);  // 得到刚刚解码的MP3帧信息
    Mp3Info.bitsPerSample = Mp3FrameInfo.bitsPerSample;
    Mp3Info.nChans = Mp3FrameInfo.nChans;
    Mp3Info.OutSamples = Mp3FrameInfo.outputSamps;
    Mp3Info.samprate = Mp3FrameInfo.samprate;
    InitMp3InfoFlag = 1;
    if (Mp3Info.bitsPerSample != 16) {
      return MP3_FAIL;
    }
  }
  Mp3Ptr = (uint16_t *)Mp3DecodeBuf;
  PlayPtr = (uint16_t *)Buf;
  if (Mp3Info.nChans == 2) {
    for (i = 0; i < Mp3Info.OutSamples; i++) {
      PlayPtr[i] = Mp3Ptr[i];
    }
  } else {
    for (i = 0; i < Mp3Info.OutSamples; i++) {
      PlayPtr[0] = Mp3Ptr[0];
      PlayPtr[1] = Mp3Ptr[0];
      PlayPtr += 2;
      Mp3Ptr += 1;
    }
  }

  return MP3_OK;
}

uint8_t I2S_WaitFlagStateUntilTimeout(I2S_HandleTypeDef *hi2s, uint32_t Flag,
                                      uint32_t Status, uint32_t Timeout) {
  uint32_t tickstart = 0;

  /* Get tick */
  tickstart = HAL_GetTick();

  /* Wait until flag is set */
  if (Status == RESET) {
    while (__HAL_I2S_GET_FLAG(hi2s, Flag) == RESET) {
      if (Timeout != HAL_MAX_DELAY) {
        if ((Timeout == 0) || ((HAL_GetTick() - tickstart) > Timeout)) {
          /* Set the I2S State ready */
          hi2s->State = HAL_I2S_STATE_READY;

          /* Process Unlocked */
          __HAL_UNLOCK(hi2s);

          return 1;
        }
      }
    }
  } else {
    while (__HAL_I2S_GET_FLAG(hi2s, Flag) != RESET) {
      if (Timeout != HAL_MAX_DELAY) {
        if ((Timeout == 0) || ((HAL_GetTick() - tickstart) > Timeout)) {
          /* Set the I2S State ready */
          hi2s->State = HAL_I2S_STATE_READY;

          /* Process Unlocked */
          __HAL_UNLOCK(hi2s);

          return 1;
        }
      }
    }
  }
  return 0;
}
