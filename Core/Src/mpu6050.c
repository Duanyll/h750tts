#include "mpu6050.h"

#include "dmpKey.h"
#include "dmpmap.h"
#include "i2c.h"
#include "inv_mpu.h"
#include "inv_mpu_dmp_motion_driver.h"
/**************************************************************************
作  者 ：大鱼电子
淘宝地址：https://shop119207236.taobao.com
**************************************************************************/

// 初始化MPU6050
// 返回值:0,成功
// 其他,错误代码
u8 MPU_Init(void) {
  u8 res;
  MPU_Write_Byte(MPU_PWR_MGMT1_REG, 0X80);  // 复位MPU6050
  delay_ms(100);
  MPU_Write_Byte(MPU_PWR_MGMT1_REG, 0X00);  // 唤醒MPU6050
  MPU_Set_Gyro_Fsr(3);                      // 陀螺仪传感器,±2000dps
  MPU_Set_Accel_Fsr(0);                     // 加速度传感器,±2g
  MPU_Set_Rate(50);                         // 设置采样率50Hz
  MPU_Write_Byte(MPU_INT_EN_REG, 0X01);     //
  MPU_Write_Byte(MPU_USER_CTRL_REG, 0X00);  // I2C主模式关闭
  MPU_Write_Byte(MPU_FIFO_EN_REG, 0X01);    // FIFO
  MPU_Write_Byte(MPU_INTBP_CFG_REG, 0X80);  // INT引脚低电平有效
  res = MPU_Read_Byte(MPU_DEVICE_ID_REG);
  if (res == MPU_ADDR)  // 器件ID正确
  {
    MPU_Write_Byte(MPU_PWR_MGMT1_REG, 0X01);  // 设置CLKSEL,PLL X轴为参考
    MPU_Write_Byte(MPU_PWR_MGMT2_REG, 0X00);  // 加速度与陀螺仪都工作
    MPU_Set_Rate(50);                         // 设置采样率为50Hz
  } else
    return 1;
  return 0;
}
// 设置MPU6050陀螺仪传感器满量程范围
// fsr:0,±250dps;1,±500dps;2,±1000dps;3,±2000dps
// 返回值:0,设置成功
//     其他,设置失败
u8 MPU_Set_Gyro_Fsr(u8 fsr) {
  return MPU_Write_Byte(MPU_GYRO_CFG_REG, fsr << 3);  // 设置陀螺仪满量程范围
}
// 设置MPU6050加速度传感器满量程范围
// fsr:0,±2g;1,±4g;2,±8g;3,±16g
// 返回值:0,设置成功
//     其他,设置失败
u8 MPU_Set_Accel_Fsr(u8 fsr) {
  return MPU_Write_Byte(MPU_ACCEL_CFG_REG,
                        fsr << 3);  // 设置加速度传感器满量程范围
}
// 设置MPU6050的数字低通滤波器
// lpf:数字低通滤波频率(Hz)
// 返回值:0,设置成功
//     其他,设置失败
u8 MPU_Set_LPF(u16 lpf) {
  u8 data = 0;
  if (lpf >= 188)
    data = 1;
  else if (lpf >= 98)
    data = 2;
  else if (lpf >= 42)
    data = 3;
  else if (lpf >= 20)
    data = 4;
  else if (lpf >= 10)
    data = 5;
  else
    data = 6;
  return MPU_Write_Byte(MPU_CFG_REG, data);  // 设置数字低通滤波器
}
// 设置MPU6050的采样率(假定Fs=1KHz)
// rate:4~1000(Hz)
// 返回值:0,设置成功
//     其他,设置失败
u8 MPU_Set_Rate(u16 rate) {
  u8 data;
  if (rate > 1000) rate = 1000;
  if (rate < 4) rate = 4;
  data = 1000 / rate - 1;
  data = MPU_Write_Byte(MPU_SAMPLE_RATE_REG, data);  // 设置数字低通滤波器
  return MPU_Set_LPF(rate / 2);  // 自动设置LPF为采样率的一半
}

// 得到温度值
// 返回值:温度值(扩大了100倍)
short MPU_Get_Temperature(void) {
  u8 buf[2];
  short raw;
  float temp;
  MPU_Read_Len(MPU_ADDR, MPU_TEMP_OUTH_REG, 2, buf);
  raw = ((u16)buf[0] << 8) | buf[1];
  temp = 36.53 + ((double)raw) / 340;
  return temp * 100;
  ;
}
// 得到陀螺仪值(原始值)
// gx,gy,gz:陀螺仪x,y,z轴的原始读数(带符号)
// 返回值:0,成功
//     其他,错误代码
u8 MPU_Get_Gyroscope(short *gx, short *gy, short *gz) {
  u8 buf[6], res;
  res = MPU_Read_Len(MPU_ADDR, MPU_GYRO_XOUTH_REG, 6, buf);
  if (res == 0) {
    *gx = ((u16)buf[0] << 8) | buf[1];
    *gy = ((u16)buf[2] << 8) | buf[3];
    *gz = ((u16)buf[4] << 8) | buf[5];
  }
  return res;
}
// 得到加速度值(原始值)
// gx,gy,gz:陀螺仪x,y,z轴的原始读数(带符号)
// 返回值:0,成功
//     其他,错误代码
u8 MPU_Get_Accelerometer(short *ax, short *ay, short *az) {
  u8 buf[6], res;
  res = MPU_Read_Len(MPU_ADDR, MPU_ACCEL_XOUTH_REG, 6, buf);
  if (res == 0) {
    *ax = ((u16)buf[0] << 8) | buf[1];
    *ay = ((u16)buf[2] << 8) | buf[3];
    *az = ((u16)buf[4] << 8) | buf[5];
  }
  return res;
  ;
}
// IIC连续写
// addr:器件地址
// reg:寄存器地址
// len:写入长度
// buf:数据区
// 返回值:0,正常
//     其他,错误代码
u8 MPU_Write_Len(u8 addr, u8 reg, u8 len, u8 *buf) {
  return Sensors_I2C_WriteRegister(MPU6050_ADDRESS, reg, len, buf);
}
// IIC连续读
// addr:器件地址
// reg:要读取的寄存器地址
// len:要读取的长度
// buf:读取到的数据存储区
// 返回值:0,正常
//     其他,错误代码
u8 MPU_Read_Len(u8 addr, u8 reg, u8 len, u8 *buf) {
  return Sensors_I2C_ReadRegister(MPU6050_ADDRESS, reg, len, buf);
}
// IIC写一个字节
// reg:寄存器地址
// data:数据
// 返回值:0,正常
//     其他,错误代码
u8 MPU_Write_Byte(u8 reg, u8 data) {
  return Sensors_I2C_WriteRegister(MPU6050_ADDRESS, reg, 1, &data);
}
// IIC读一个字节
// reg:寄存器地址
// 返回值:读到的数据
u8 MPU_Read_Byte(u8 reg) {
  u8 res;
  Sensors_I2C_ReadRegister(MPU6050_ADDRESS, reg, 1, &res);
  return res;
}

uint32_t last_update_tick;
int fail_count = 0;

struct MpuData {
  float pitch, roll, yaw;
  short a1, a2, a3;
} mpuData;

void MPU6050_freshData() {
  if (HAL_GetTick() - last_update_tick < 15) return;
  float pitch, roll, yaw;
  short acc1, acc2, acc3;
  int res = mpu_dmp_get_data(&pitch, &roll, &yaw, &acc1, &acc2, &acc3);
  if (res == 0) {
    last_update_tick = HAL_GetTick();
    fail_count = 0;
    mpuData.a1 = acc1;
    mpuData.a2 = acc2;
    mpuData.a3 = acc3;
    mpuData.pitch = pitch;
    mpuData.roll = roll;
    mpuData.yaw = yaw;
  } else {
    fail_count++;
    if (fail_count > 10) {
      fail_count = 0;
      // MPU_Init();
      // mpu_dmp_init();
    }
  }
}

void MPU6050_getData(float *pitch, float *roll, float *yaw, short *a1,
                     short *a2, short *a3) {
  *pitch = mpuData.pitch;
  *roll = mpuData.roll;
  *yaw = mpuData.yaw;
  *a1 = mpuData.a1;
  *a2 = mpuData.a2;
  *a3 = mpuData.a3;
}