#include <Arduino.h>
#include "driver/i2s.h"
#include "driver/adc.h"

static const int SAMPLE_RATE = 16000;
static const int CHUNK_SAMPLES = 512;   // ~32ms
static uint16_t adc_buf[CHUNK_SAMPLES];
static int16_t  pcm_buf[CHUNK_SAMPLES];

void setup_adc_i2s() {
  // ADC1 channel for GPIO34 is ADC1_CHANNEL_6
  adc1_config_width(ADC_WIDTH_BIT_12);
  adc1_config_channel_atten(ADC1_CHANNEL_6, ADC_ATTEN_DB_11); // wider input range

  i2s_config_t cfg = {};
  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX | I2S_MODE_ADC_BUILT_IN);
  cfg.sample_rate = SAMPLE_RATE;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
  cfg.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;
  cfg.communication_format = I2S_COMM_FORMAT_I2S_MSB;
  cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count = 8;
  cfg.dma_buf_len = 256;
  cfg.use_apll = false;

  i2s_driver_install(I2S_NUM_0, &cfg, 0, NULL);
  i2s_set_adc_mode(ADC_UNIT_1, ADC1_CHANNEL_6);
  i2s_adc_enable(I2S_NUM_0);
}

void setup() {
  Serial.begin(2000000);
  delay(200);
  setup_adc_i2s();
}

void loop() {
  size_t bytesRead = 0;
  i2s_read(I2S_NUM_0, adc_buf, sizeof(adc_buf), &bytesRead, portMAX_DELAY);
  int n = bytesRead / 2; // uint16 samples

  // Remove DC offset per chunk, convert to signed 16-bit PCM
  int32_t mean = 0;
  for (int i = 0; i < n; i++) mean += (adc_buf[i] & 0x0FFF);
  mean /= n;

  for (int i = 0; i < n; i++) {
    int32_t s = (adc_buf[i] & 0x0FFF) - mean; // center around 0
    // scale up a bit (SPW2430 is small signal)
    s = s * 16;
    if (s > 32767) s = 32767;
    if (s < -32768) s = -32768;
    pcm_buf[i] = (int16_t)s;
  }

  Serial.write((uint8_t*)pcm_buf, n * sizeof(int16_t));
}
