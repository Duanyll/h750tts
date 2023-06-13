/*
 * mp3.c
 *
 *  Created on: Apr 6, 2023
 *      Author: WR
 */

#include "mp3.h"

#include "i2s.h"

#include <stdio.h>

FIL voice_pack_file;
uint8_t file_buffer[MP3_FILE_BUFFER_SIZE];
int16_t decode_buffer[MP3_DECODE_BUFFER_SIZE];
int16_t dma_buffer[MP3_DMA_BUFFER_SIZE];
uint32_t index_buffer[MP3_INDEX_BUFFER_SIZE];
uint32_t dict_buffer[MP3_DICT_BUFFER_SIZE]; // Interleaved, sorted char code and file id
int index_size;
int dict_size;

int play_queue[MP3_QUEUE_SIZE];  // Circular Queue
int play_queue_head, play_queue_tail;

Mp3DecodeState state;

// Parse a utf8 string to unicode, return current char code like python ord()
uint32_t ParseUtf8(char **str) {
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

int MP3_Init() {
  state.isPlaying = 0;
  state.volume = MP3_MAX_VOLUME / 2;
  state.bufferToFill = 0;
  state.shouldStop = 0;
  state.outChannels = 0x03;

  FIL fp;
  f_open(&fp, "0:/INDEX", FA_READ);
  f_read(&fp, index_buffer, MP3_INDEX_BUFFER_SIZE * 4, &index_size);
  index_size /= 4;
  f_close(&fp);

  f_open(&fp, "0:/DICT", FA_READ);
  f_read(&fp, dict_buffer, MP3_DICT_BUFFER_SIZE * 4, &dict_size);
  dict_size /= 8;
  f_close(&fp);

  f_open(&voice_pack_file, "0:/BIN", FA_READ);

  state.decoder = MP3InitDecoder();
  play_queue_head = play_queue_tail = 0;

  return MP3_OK;
}

int MP3_FindIndexByCharCode(int code) {
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
  return MP3_FAIL;
}

int MP3_Enqueue(int fileId) {
  if (fileId < 0 || fileId >= index_size - 1) return MP3_FAIL;
  if (play_queue_head == (play_queue_tail + 1) % MP3_QUEUE_SIZE) return MP3_FAIL;
  play_queue[play_queue_tail] = fileId;
  play_queue_tail = (play_queue_tail + 1) % MP3_QUEUE_SIZE;
  return MP3_OK;
}

int MP3_Speak(char* str) {
  int successCount = 0;
  while (*str) {
    int code = ParseUtf8(&str);
    if (code < 0) return MP3_FAIL;
    int fileId = MP3_FindIndexByCharCode(code);
    if (fileId < 0) continue;
    if (MP3_Enqueue(fileId) == MP3_OK) successCount++;
  }
  return successCount;
}

int MP3_SetVolume(int vol) {
  if (vol < 0 || vol > MP3_MAX_VOLUME) return MP3_FAIL;
  state.volume = vol;
  return MP3_OK;
}

int MP3_GetVolume() { return state.volume; }

int MP3_DecodeFrame() {
  int offset = MP3FindSyncWord(state.readFilePtr, state.endFilePtr - state.readFilePtr);
  if (offset < 0) {
    state.shouldStop = 1;
    return MP3_FAIL;
  }
  state.readFilePtr += offset;
  int bytesLeft = state.endFilePtr - state.readFilePtr;
  int err = MP3Decode(state.decoder, &state.readFilePtr, &bytesLeft,
                      decode_buffer, 0);
  if (err != 0) {
    state.shouldStop = 1;
    return MP3_FAIL;
  }
  MP3GetLastFrameInfo(state.decoder, &state.lastFrameInfo);
  return MP3_OK;
}

int MP3_FillDmaBuffer() {
  int16_t *dmaPtr = dma_buffer + (state.bufferToFill - 1) * state.dmaBufferSize;
  int16_t *dmaPtrStart = dmaPtr;
  int16_t *decodePtr = decode_buffer;
  int16_t *decodeEnd = decode_buffer + state.lastFrameInfo.outputSamps;
  if (state.lastFrameInfo.nChans == 2) {
    while (decodePtr < decodeEnd) {
      int16_t left = *decodePtr++;
      int16_t right = *decodePtr++;
      *dmaPtr++ = (state.outChannels & 0x01) ? left * state.volume / MP3_MAX_VOLUME : 0;
      *dmaPtr++ = (state.outChannels & 0x02) ? right * state.volume / MP3_MAX_VOLUME : 0;
    }
  } else {
    while (decodePtr < decodeEnd) {
      int16_t left = *decodePtr++;
      *dmaPtr++ = (state.outChannels & 0x01) ? left * state.volume / MP3_MAX_VOLUME : 0;
      *dmaPtr++ = (state.outChannels & 0x02) ? left * state.volume / MP3_MAX_VOLUME : 0;
    }
  }
  SCB_CleanDCache_by_Addr((uint32_t *)dmaPtrStart, state.dmaBufferSize * 2);
  return MP3_OK;
}

int MP3_StartPlay(int fileId) {
  if (state.isPlaying) return MP3_FAIL;
  if (fileId < 0 || fileId >= index_size - 1) return MP3_FAIL;

  int offsetInPack = index_buffer[fileId];
  int fileLength = index_buffer[fileId + 1] - offsetInPack;
  f_lseek(&voice_pack_file, offsetInPack);
  f_read(&voice_pack_file, file_buffer, fileLength, &fileLength);

  state.readFilePtr = file_buffer;
  state.endFilePtr = file_buffer + fileLength;

  ID3V2_TagHead *tag = (ID3V2_TagHead *)file_buffer;
  if (strncmp("ID3", (const char *)tag->id, 3) == 0) {
    state.readFilePtr += ((uint32_t)tag->size[0] << 21) |
                         ((uint32_t)tag->size[1] << 14) |
                         ((uint32_t)tag->size[2] << 7) | tag->size[3];
  }

  state.bufferToFill = 1;
  MP3_DecodeFrame();
  MP3FrameInfo* info = &state.lastFrameInfo;
  state.dmaBufferSize = (info->outputSamps / info->nChans) * 2;
  MP3_FillDmaBuffer();

  state.bufferToFill = 2;
  MP3_DecodeFrame();
  MP3_FillDmaBuffer();

  HAL_GPIO_WritePin(PCM5102A_XMT_GPIO_Port, PCM5102A_XMT_Pin, GPIO_PIN_SET);
  HAL_GPIO_WritePin(LED_Onboard_GPIO_Port, LED_Onboard_Pin, GPIO_PIN_SET);
  HAL_I2S_Transmit_DMA(&hi2s1, (uint16_t *)dma_buffer, state.dmaBufferSize * 2);
  state.isPlaying = 1;
  state.shouldStop = 0;
  return MP3_OK;
}

int MP3_StopPlay(int clearQueue) {
  if (state.isPlaying) {
    HAL_I2S_DMAStop(&hi2s1);
    HAL_GPIO_WritePin(PCM5102A_XMT_GPIO_Port, PCM5102A_XMT_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(LED_Onboard_GPIO_Port, LED_Onboard_Pin, GPIO_PIN_RESET);
    state.isPlaying = 0;
    state.shouldStop = 0;
  }
  if (clearQueue) {
    play_queue_head = 0;
    play_queue_tail = 0;
  }
  return MP3_OK;
}

int MP3_PollBuffer() {
  if (state.isPlaying) {
    if (state.bufferToFill > 0) {
      if (state.readFilePtr >= state.endFilePtr) {
        state.shouldStop = 1;
      } else {
        MP3_DecodeFrame();
        MP3_FillDmaBuffer();
        state.bufferToFill = 0;
      }
    } 
  }
  if (!state.isPlaying) {
    // Try to play next song
    if (play_queue_head != play_queue_tail) {
      MP3_StartPlay(play_queue[play_queue_head]);
      play_queue_head = (play_queue_head + 1) % MP3_QUEUE_SIZE;
    }
  }
  return MP3_OK;
}

void HAL_I2S_TxHalfCpltCallback(I2S_HandleTypeDef *hi2s) {
  if (state.shouldStop) {
    MP3_StopPlay(0);
  } else {
    state.bufferToFill = 1;
  }
}

void HAL_I2S_TxCpltCallback(I2S_HandleTypeDef *hi2s) {
  if (state.shouldStop) {
    MP3_StopPlay(0);
  } else {
    state.bufferToFill = 2;
  }
}

int MP3_GetIsPlaying() {
  return state.isPlaying;
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
