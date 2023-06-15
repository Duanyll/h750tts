/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    i2c.c
  * @brief   This file provides code for the configuration
  *          of the I2C instances.
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
#include "i2c.h"

/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

I2C_HandleTypeDef hi2c1;

/* I2C1 init function */
void MX_I2C1_Init(void)
{

  /* USER CODE BEGIN I2C1_Init 0 */

  /* USER CODE END I2C1_Init 0 */

  /* USER CODE BEGIN I2C1_Init 1 */

  /* USER CODE END I2C1_Init 1 */
  hi2c1.Instance = I2C1;
  hi2c1.Init.Timing = 0x10C0ECFF;
  hi2c1.Init.OwnAddress1 = 0;
  hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hi2c1.Init.OwnAddress2 = 0;
  hi2c1.Init.OwnAddress2Masks = I2C_OA2_NOMASK;
  hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
  if (HAL_I2C_Init(&hi2c1) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Analogue filter
  */
  if (HAL_I2CEx_ConfigAnalogFilter(&hi2c1, I2C_ANALOGFILTER_ENABLE) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Digital filter
  */
  if (HAL_I2CEx_ConfigDigitalFilter(&hi2c1, 0) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN I2C1_Init 2 */

  /* USER CODE END I2C1_Init 2 */

}

void HAL_I2C_MspInit(I2C_HandleTypeDef* i2cHandle)
{

  GPIO_InitTypeDef GPIO_InitStruct = {0};
  RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = {0};
  if(i2cHandle->Instance==I2C1)
  {
  /* USER CODE BEGIN I2C1_MspInit 0 */

  /* USER CODE END I2C1_MspInit 0 */

  /** Initializes the peripherals clock
  */
    PeriphClkInitStruct.PeriphClockSelection = RCC_PERIPHCLK_I2C1;
    PeriphClkInitStruct.I2c123ClockSelection = RCC_I2C123CLKSOURCE_D2PCLK1;
    if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct) != HAL_OK)
    {
      Error_Handler();
    }

    __HAL_RCC_GPIOB_CLK_ENABLE();
    /**I2C1 GPIO Configuration
    PB7     ------> I2C1_SDA
    PB8     ------> I2C1_SCL
    */
    GPIO_InitStruct.Pin = MPU6050_SDA_Pin|MPU6050_SCL_Pin;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_OD;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    GPIO_InitStruct.Alternate = GPIO_AF4_I2C1;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

    /* I2C1 clock enable */
    __HAL_RCC_I2C1_CLK_ENABLE();
  /* USER CODE BEGIN I2C1_MspInit 1 */

  /* USER CODE END I2C1_MspInit 1 */
  }
}

void HAL_I2C_MspDeInit(I2C_HandleTypeDef* i2cHandle)
{

  if(i2cHandle->Instance==I2C1)
  {
  /* USER CODE BEGIN I2C1_MspDeInit 0 */

  /* USER CODE END I2C1_MspDeInit 0 */
    /* Peripheral clock disable */
    __HAL_RCC_I2C1_CLK_DISABLE();

    /**I2C1 GPIO Configuration
    PB7     ------> I2C1_SDA
    PB8     ------> I2C1_SCL
    */
    HAL_GPIO_DeInit(MPU6050_SDA_GPIO_Port, MPU6050_SDA_Pin);

    HAL_GPIO_DeInit(MPU6050_SCL_GPIO_Port, MPU6050_SCL_Pin);

  /* USER CODE BEGIN I2C1_MspDeInit 1 */

  /* USER CODE END I2C1_MspDeInit 1 */
  }
}

/* USER CODE BEGIN 1 */
/**
  * @brief  写寄存器，这是提供给上层的接�?
	* @param  slave_addr: 从机地址
	* @param 	reg_addr:寄存器地�?
	* @param len：写入的长度
	*	@param data_ptr:指向要写入的数据
  * @retval 正常�?0，不正常为非0
  */
int Sensors_I2C_WriteRegister(unsigned char slave_addr,
                                        unsigned char reg_addr,
                                        unsigned short len, 
                                        unsigned char *data_ptr)
{
	HAL_StatusTypeDef status = HAL_OK;
	status = HAL_I2C_Mem_Write(&hi2c1, slave_addr, reg_addr, I2C_MEMADD_SIZE_8BIT,data_ptr, len,I2C_FLAG_TIMEOUT); 
	/* �?查�?�讯状�?? */
	if(status != HAL_OK)
	{
		/* 总线出错处理 */
	}
	while (HAL_I2C_GetState(&hi2c1) != HAL_I2C_STATE_READY)
	{
		
	}
	/* �?查SENSOR是否就绪进行下一次读写操�? */
	while (HAL_I2C_IsDeviceReady(&hi2c1, slave_addr, I2C_FLAG_TIMEOUT, I2C_FLAG_TIMEOUT) == HAL_TIMEOUT);
	/* 等待传输结束 */
	while (HAL_I2C_GetState(&hi2c1) != HAL_I2C_STATE_READY)
	{
		
	}
	return status;
}

/**
  * @brief  读寄存器，这是提供给上层的接�?
	* @param  slave_addr: 从机地址
	* @param 	reg_addr:寄存器地�?
	* @param len：要读取的长�?
	*	@param data_ptr:指向要存储数据的指针
  * @retval 正常�?0，不正常为非0
  */
int Sensors_I2C_ReadRegister(unsigned char slave_addr,
                                       unsigned char reg_addr,
                                       unsigned short len, 
                                       unsigned char *data_ptr)
{
	HAL_StatusTypeDef status = HAL_OK;
	status =HAL_I2C_Mem_Read(&hi2c1,slave_addr,reg_addr,I2C_MEMADD_SIZE_8BIT,data_ptr,len,I2C_FLAG_TIMEOUT);    
	/* �?查�?�讯状�?? */
	if(status != HAL_OK)
	{
		/* 总线出错处理 */
	}
	while (HAL_I2C_GetState(&hi2c1) != HAL_I2C_STATE_READY)
	{
		
	}
	/* �?查SENSOR是否就绪进行下一次读写操�? */
	while (HAL_I2C_IsDeviceReady(&hi2c1, slave_addr, I2C_FLAG_TIMEOUT, I2C_FLAG_TIMEOUT) == HAL_TIMEOUT);
	/* 等待传输结束 */
	while (HAL_I2C_GetState(&hi2c1) != HAL_I2C_STATE_READY)
	{
		
	}
	return status;
}
/* USER CODE END 1 */
