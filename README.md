# Raspberry Pi controller for a hottub

The goal of this project was to be able to have the hottub constantly on running on the minimum temperature and increase the temperature remotely in time before the actual use (lets say 2h prior). The common problem we were dealing with was that if we wanted to use the hottub in the evening after work we would have to boost the temperature in the morning so it is ready later. This would waste a lot of electricity since it would keep the water hot for longer than necessary. 

## Reverse engineering the panel wiring 

The controller is designed to work with Jacuzzi 2500-154 control panel. This panel has two buttons, one LED and 3 digit display. It connects to the Balboa control board J1 port via a 6 wire telephone style plug.

It required to find out which wire is power and which two are the buttons (there is 5V reading between the power and the button wires). The other 3 wires control the display and the LED.

## Connecting to the Pi

The Pi was connected between the control panel and the board. Lots of work here, details come later.

## Programming controllers

There are two programs running on Pi.

One is a fast C++ program that reads signal from the display wires and record the currently displayed temperature to a file.

The other is a Python program that listens for temperature change http request, reads the current temperature file and changes the target temperature.

We are using <link>https://dweet.io</link> service to communicate with the controller. You can create an IFTTT button widget on your phone to trigger the webhook <link>https://ifttt.com/create/if-button-press-then-make-a-web-request</link>

## Running the controller

Compile the C program.

<code> gcc -Wall -o record record.c -lwiringPi </code>

Install Python dependencies.

<code> pip install -r requirements.txt </code> 

Edit <code>config.ini</code> file.

Run both programs as daemons.

You can set a cron job to run the <code>restarter.py</code> script which restarts both programs automatically if they are not running
