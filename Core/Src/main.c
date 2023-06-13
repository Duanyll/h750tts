/* USER CODE BEGIN Header */
/**
 ******************************************************************************
 * @file           : main.c
 * @brief          : Main program body
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2023 STMicroelectronics.
 * All rights reserved.
 *
 * This software is licensed under terms that can be found in the LICENSE file
 * in the root directory of this software component.
 * If no LICENSE file comes with this software, it is provided AS-IS.
 *
 ******************************************************************************
 */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

#include "dma.h"
#include "fatfs.h"
#include "gpio.h"
#include "i2c.h"
#include "i2s.h"
#include "quadspi.h"
#include "sdmmc.h"
#include "usart.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include <string.h>

#include "dmpKey.h"
#include "dmpmap.h"
#include "inv_mpu.h"
#include "inv_mpu_dmp_motion_driver.h"
#include "mp3.h"
#include "mpu6050.h"
#include "retarget.h"
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */
#define APP_ERROR(code, message) \
  printf("{\"code\":%d,\"message\":\"%s\"}\n", code, message)
#define APP_SUCCESS(message) \
  printf("{\"code\":0,\"message\":\"%s\"}\n", message)
/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
/* USER CODE BEGIN PFP */
void APP_HandleJsonData(cJSON* json);
void APP_EchoCommand(cJSON* json);
void APP_LedCommand(cJSON* json);
void APP_PlayCommand(cJSON* json);
void APP_SpeakCommand(cJSON* json);
void APP_StopCommand(cJSON* json);
void APP_VolumeCommand(cJSON* json);
void APP_QueryCommand(cJSON* json);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/**
 * @brief  The application entry point.
 * @retval int
 */
int main(void) {
  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* Enable I-Cache---------------------------------------------------------*/
  SCB_EnableICache();

  /* Enable D-Cache---------------------------------------------------------*/
  SCB_EnableDCache();

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick.
   */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_DMA_Init();
  MX_I2S1_Init();
  MX_SDMMC1_SD_Init();
  MX_USART1_UART_Init();
  MX_USART2_UART_Init();
  MX_QUADSPI_Init();
  MX_FATFS_Init();
  MX_USART3_UART_Init();
  MX_I2C1_Init();
  /* USER CODE BEGIN 2 */
  SDMMC_InitFilesystem();
  RetargetInit(&huart2);
  mpu_dmp_init();
  MPU_Init();  //=====初始化MPU6050
  UART_ResetJsonRX(&huart2);
  MP3_Init();

  MP3_Speak("开机");
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1) {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
    UART_PollJsonData(APP_HandleJsonData);
    MP3_PollBuffer();
  }
  /* USER CODE END 3 */
}

/**
 * @brief System Clock Configuration
 * @retval None
 */
void SystemClock_Config(void) {
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Supply configuration update enable
   */
  HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY);

  /** Configure the main internal regulator output voltage
   */
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

  while (!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) {
  }

  /** Initializes the RCC Oscillators according to the specified parameters
   * in the RCC_OscInitTypeDef structure.
   */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLM = 5;
  RCC_OscInitStruct.PLL.PLLN = 160;
  RCC_OscInitStruct.PLL.PLLP = 2;
  RCC_OscInitStruct.PLL.PLLQ = 4;
  RCC_OscInitStruct.PLL.PLLR = 2;
  RCC_OscInitStruct.PLL.PLLRGE = RCC_PLL1VCIRANGE_2;
  RCC_OscInitStruct.PLL.PLLVCOSEL = RCC_PLL1VCOWIDE;
  RCC_OscInitStruct.PLL.PLLFRACN = 0;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
   */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                                RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2 |
                                RCC_CLOCKTYPE_D3PCLK1 | RCC_CLOCKTYPE_D1PCLK1;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.SYSCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB3CLKDivider = RCC_APB3_DIV2;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_APB2_DIV2;
  RCC_ClkInitStruct.APB4CLKDivider = RCC_APB4_DIV2;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK) {
    Error_Handler();
  }
}

/* USER CODE BEGIN 4 */
void APP_HandleJsonData(cJSON* json) {
  if (json != NULL) {
    cJSON* command = cJSON_GetObjectItemCaseSensitive(json, "command");
    if (cJSON_IsString(command) && (command->valuestring != NULL)) {
      if (strcmp(command->valuestring, "echo") == 0) {
        APP_EchoCommand(json);
      } else if (strcmp(command->valuestring, "led") == 0) {
        APP_LedCommand(json);
      } else if (strcmp(command->valuestring, "play") == 0) {
        APP_PlayCommand(json);
      } else if (strcmp(command->valuestring, "speak") == 0) {
        APP_SpeakCommand(json);
      } else if (strcmp(command->valuestring, "stop") == 0) {
        APP_StopCommand(json);
      } else if (strcmp(command->valuestring, "volume") == 0) {
        APP_VolumeCommand(json);
      } else if (strcmp(command->valuestring, "query") == 0) {
        APP_QueryCommand(json);
      } else {
        APP_ERROR(2, "Unknown command");
        return;
      }
    } else {
      APP_ERROR(1, "Bad json");
      return;
    }
  } else {
    APP_ERROR(1, "Bad json");
    return;
  }
}

void APP_EchoCommand(cJSON* json) {
  // { "command": "echo", "message": "Hello World!" }
  cJSON* message = cJSON_GetObjectItemCaseSensitive(json, "message");
  if (cJSON_IsString(message) && (message->valuestring != NULL)) {
    APP_SUCCESS(message->valuestring);
  } else {
    APP_ERROR(2, "Bad command");
    return;
  }
}

void APP_LedCommand(cJSON* json) {
  // { "command": "led", "on": true | false }
  cJSON* on = cJSON_GetObjectItemCaseSensitive(json, "on");
  if (cJSON_IsBool(on)) {
    if (on->valueint == 1) {
      HAL_GPIO_WritePin(LED_Onboard_GPIO_Port, LED_Onboard_Pin, GPIO_PIN_SET);
    } else {
      HAL_GPIO_WritePin(LED_Onboard_GPIO_Port, LED_Onboard_Pin, GPIO_PIN_RESET);
    }
  } else {
    APP_ERROR(2, "Bad command");
    return;
  }
  APP_SUCCESS("OK");
}

void APP_PlayCommand(cJSON* json) {
  // { "command": "play", "list": [123, 2131, 123] }
  cJSON* list = cJSON_GetObjectItemCaseSensitive(json, "list");
  if (cJSON_IsArray(list)) {
    cJSON* item = NULL;
    cJSON_ArrayForEach(item, list) {
      if (cJSON_IsNumber(item)) {
        MP3_Enqueue(item->valueint);
      }
    }
    APP_SUCCESS("OK");
  } else {
    APP_ERROR(2, "Bad command");
  }
}

void APP_SpeakCommand(cJSON* json) {
  // { "command": "speak", "text": "中文 UTF-8 字符串" }
  cJSON* text = cJSON_GetObjectItemCaseSensitive(json, "text");
  if (cJSON_IsString(text) && (text->valuestring != NULL)) {
    MP3_Speak(text->valuestring);
    APP_SUCCESS("OK");
  } else {
    APP_ERROR(2, "Bad command");
  }
}

void APP_StopCommand(cJSON* json) {
  // { "command": "stop" }
  MP3_StopPlay(1);
  APP_SUCCESS("OK");
}

void APP_VolumeCommand(cJSON* json) {
  // { "command": "volume", "volume": 50 }
  cJSON* volume = cJSON_GetObjectItemCaseSensitive(json, "volume");
  if (cJSON_IsNumber(volume) && MP3_SetVolume(volume->valueint) == MP3_OK) {
    APP_SUCCESS("OK");
  } else {
    APP_ERROR(2, "Bad command");
  }
}

void APP_QueryCommand(cJSON* json) {
  /*
    interface QueryResponseData {
      volume: number;
      isPlaying: boolean;

      isMoving: boolean;
      facing: number;
      distance: number;
    }

    interface SuccessResponse<TData = void> {
      code: 0;
      message: string;
      data: TData;
    }
  */

  cJSON* data = cJSON_CreateObject();
  cJSON_AddNumberToObject(data, "volume", MP3_GetVolume());
  cJSON_AddBoolToObject(data, "isPlaying", MP3_GetIsPlaying());
  cJSON_AddBoolToObject(data, "isMoving", cJSON_True);  // TODO: Add sensor data
  cJSON_AddNumberToObject(data, "facing", 0);
  cJSON_AddNumberToObject(data, "distance", 100);

  cJSON* response = cJSON_CreateObject();
  cJSON_AddNumberToObject(response, "code", 0);
  cJSON_AddStringToObject(response, "message", "OK");
  cJSON_AddItemToObject(response, "data", data);

  char* response_str = cJSON_PrintUnformatted(response);
  printf("%s\n", response_str);

  cJSON_Delete(response);
  free(response);
  free(response_str);
}
/* USER CODE END 4 */

/**
 * @brief  This function is executed in case of error occurrence.
 * @retval None
 */
void Error_Handler(void) {
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1) {
    HAL_GPIO_TogglePin(LED_Onboard_GPIO_Port, LED_Onboard_Pin);
    HAL_Delay(100);
  }
  /* USER CODE END Error_Handler_Debug */
}

#ifdef USE_FULL_ASSERT
/**
 * @brief  Reports the name of the source file and the source line number
 *         where the assert_param error has occurred.
 * @param  file: pointer to the source file name
 * @param  line: assert_param error line source number
 * @retval None
 */
void assert_failed(uint8_t* file, uint32_t line) {
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line
     number, ex: printf("Wrong parameters value: file %s on line %d\r\n", file,
     line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
