# Domoticz-Palazzetti-Plugin

A simple Domoticz Python plugin to control your Palazzetti pellet stove through the Palazzetti Connection Box.

## History

This plugin has been developed to replace a first attempt of Domoticz/Palazzetti Connection Box interface that was based on:
* dummy devices - switches, selector switches, Counter, (buggy) Setpoint
* LUA JSON parser (Domoticz HTTP Poller) - to retrieve data from the Connexion Box
* PHP script to send JSON requests to the Connection Box - used as device action script 
* LUA script to sync data between dummy devices, with a intensive use of ```commandArray["UpdateDevice"] = "idx|nValue|sValue"``` to avoid infinite back and forth at device update.

So the main reason of this plugin was to ease maintenance by reducing the number of script files.
Moreover, there is no more need to maintain devices idx in different scripts, as Domoticz Python plugin framework gives an index-less access to devices attached to the plugin hardware.
BTW, it's also my first walk in Python scripts.

This plugin is being developped based on an Ecofire Ines 9kW Palazzetti pellet stove.

## Key Features

Creates the following Domoticz Devices:
* Pellets Stove On/Off switch
* Status (code) (0, 1, 6, etc)
* Status (label) (OFF, OFF+TIMER, BURNING, etc)
* Fan speed selector switch (1,2,3,4,5,Auto,Hi)
* Timer On/Off switch
* Power level selector switch (1,2,3,4,5)
* Setpoint
* Room temperature
* Exhaust temperature
* Pellet quantity used counter (in Kg)

## Configuration

### Plugin Parameters

| Field | Information|
| ----- | ---------- |
| Connection Box IP Address: | DNS name or IP V4 addresses of the Connection Box |
| Port | The port that the Palazzetti Connection Box is listening on. Default 80 |
| Custom Codes | For custom status labels (see below) |
| Debug | When true the logging level will be much higher to aid with troubleshooting |

### Custom codes

Here are the standard status code/label as used in the Palazzetti Connexion Box web interface:

| Code | Label|
| ----- | ---------- |
| 0 | OFF |
| 1 | OFF TIMER |
| 2 | TESTFIRE |
| 3 | HEATUP |
| 4 | FUELIGN |
| 5 | IGNTEST |
| 6 | BURNING |
| 9 | COOLFLUID |
| 10 | FIRESTOP |
| 11 | CLEANFIRE |
| 12 | COOL |

You can customize labels with ```Custom Codes``` parameter. Simply enter a Python ```dict``` string like this:
```{ "OFF": "Stopped", "1" : "Off with Timer on" }```.
If the ```dict``` syntax is wrong, the custom codes will be ignored when plugin will start or reload.
Both standard codes and labels can be used as key in the ```dict``` definition.


## Change log

| Version | Information|
| ----- | ---------- |
| 0.9.0 | Initial upload version |


## TODO

* Show last alarm





