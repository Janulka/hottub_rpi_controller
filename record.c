// Compile and run with:
//
// $ gcc -Wall -o record record.c -lwiringPi && sudo ./record

#include <wiringPi.h>
#include <math.h>
#include <stdio.h>

int CLOCK_PIN = 8;
int DATA_PIN = 9;

int ZERO_GAP = 1000;
int SEGMENT_DATA_SIZE = 21;

int data_to_digits[13][7] = {
  {1, 1, 1, 1, 1, 1, 0}, // 0
  {0, 1, 1, 0, 0, 0, 0}, // 1
  {1, 1, 0, 1, 1, 0, 1}, // 2
  {1, 1, 1, 1, 0, 0, 1}, // 3
  {0, 1, 1, 0, 0, 1, 1}, // 4
  {1, 0, 1, 1, 0, 1, 1}, // 5
  {1, 0, 1, 1, 1, 1, 1}, // 6
  {1, 1, 1, 0, 0, 0, 0}, // 7
  {1, 1, 1, 1, 1, 1, 1}, // 8
  {1, 1, 1, 1, 0, 1, 1}, // 9
  {0, 0, 0, 0, 1, 0, 0}, // 0 + LED ON
  {0, 1, 1, 0, 1, 0, 0}, // 1 + LED ON
  {0, 0, 0, 0, 0, 0, 0}, // 0 nothing displayed
};

int convert(int* data) {
  for (int d = 0; d < 13; ++d) {
    for (int i = 0; i < 7; ++i) {
      if (data_to_digits[d][i] == data[i]) {
        if (i == 6) {
	  if (d == 12) {
            return 0; 
	  }
          return (d % 10);
        }
      } else {
        break;
      }
    }
  }
  return -1;
}

int main (void) {
  if (wiringPiSetup() == -1) {
    printf("Setup wiringPi failed!\n");
    return 1;
  }
  printf("Recording temperature!\n");
  pinMode(CLOCK_PIN, INPUT);
  pinMode(DATA_PIN, INPUT);

  int num_samples = 100000;
  int clock[num_samples];
  int data[num_samples];

  int temperature = 0;
  int current_temperature = -1;
  int output_temperature_in_file = -1;
  int temperature_count = 0;

  //int temp_output_temperature_in_file = -1;

  while (1) { 
    // Record data.
    for (int i = 0; i < num_samples; i++) {
      clock[i] = digitalRead(CLOCK_PIN);
      data[i] = digitalRead(DATA_PIN);
    }

    // Find the start.
    int zero_counter = 0;
    int start_index = -1;
    for (int i = 0; i < num_samples; i++) {
      if (start_index < 0) {
        if (clock[i] == 1) {
          zero_counter = 0;
        } else {
          zero_counter++;
          if (zero_counter >= ZERO_GAP) {
            start_index = i;
          }
        }
      } else {
        if (clock[i] == 0) {
          start_index = i;
        } else {
          break;
        }
      }
    }

    // Process.
    int rising_edge_count = 0;
    int ones_counter = 0;
    zero_counter = 0;

    int segment_data[SEGMENT_DATA_SIZE];
    for (int i = 0; i < SEGMENT_DATA_SIZE; i++) {
      segment_data[i] = -1;
    }
    int segment_data_index = 0;

    //printf("start index %i\n", start_index);
    for (int i = start_index; i < num_samples-1; i++) {
      if (clock[i] == 1 && clock[i + 1] == 0) {
        segment_data[segment_data_index] = data[i+1];
        segment_data_index++;
        rising_edge_count++;
	//printf("rising_edge_count %i\n", rising_edge_count);
      }

      if (clock[i] == 0) {
        zero_counter++;
        if (zero_counter >= ZERO_GAP) {
	  //printf("zero_counter %i\n", zero_counter);
          int segment_index = 0;
          temperature = 0;
          for (int n = 0; n < 3; ++n) {
            int segment[7];
            for (int i = 0; i < 7; ++i) {
              segment[i] = segment_data[segment_index];
              segment_index++;
	      //printf("digit %i segment %i data %i\n", n, i, segment[i]);
            }
            int segment_number = convert(segment);
            if (segment_number < 0) {
              temperature = -1;
              break;
            }
	    //printf("digit read %i\n", segment_number);
            if (n == 0) {
              temperature += 100 * segment_number;
            } else if (n == 1) {
              temperature += 10 * segment_number;
            } else {
              temperature += segment_number;
            }
          }
	  //printf("temperature %i\n", temperature);
          break;
        }
      } else {
        ones_counter++;
        zero_counter = 0;
      }
    }

    if (temperature < 1) {
      continue;
    }

    //printf("valid temperature read %i\n", temperature);
    if (current_temperature < 0) {
      current_temperature = temperature;
    }

    if (temperature == current_temperature) {
      temperature_count++;
      if (temperature_count >= 10) {
        if (output_temperature_in_file != temperature) {
          output_temperature_in_file = temperature;
          FILE *f1 = fopen("/home/pi/current_temperature.txt", "w");
          fprintf(f1, "%d\n", temperature);
          fclose(f1);
          printf("Wrote %d to current temperature file.\n", temperature);
	  FILE *f2 = fopen("/home/pi/temperature_log.txt", "a");
	  fprintf(f2, "%d\n", temperature);
	  fclose(f2);
        }
      }
    } else {
      temperature_count = 0;
      current_temperature = temperature;
    }
  }
  return 0 ;
}
