# Palazzetti Connection Box Python plugin for Domoticz
#
# Author: kinou74, 2018
#
# Changes:
# 20181114 - New Plugin option to choose the Connection Box API.
#            Staring mid-2018, Palazzetti has released a new software and the API URLs changes from PHP to LUA.
#
"""
<plugin key="palazzetti-cbox" name="Palazzetti Connection Box" author="kinou74" version="0.9.1">
    <params>
        <param field="Address" label="Connection Box IP Address" width="200px" required="true" default="127.0.0.1"/>
        <param field="Port" label="Port" width="30px" required="true" default="80"/>
        <param field="Mode4" label="Use new Connection Box LUA API" width="75px">
            <options>
                <option label="True (default)" value="True" default="true" />
                <option label="False" value="False" />
            </options>
        </param>
        <param field="Mode5" label="Custom Codes" width="500px" default="" />
        <param field="Mode6" label="Debug" width="75px">
          <options>
            <option label="True" value="Debug"/>
            <option label="False (default)" value="Normal" default="true" />
          </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import json
import ast
from datetime import datetime,timedelta

class BasePlugin:
    httpConn = None
    nextConnect = 3
    oustandingPings = 0
    
    __UNIT_ONOFF = 1
    __UNIT_POWER = 2
    __UNIT_FAN2LEVEL = 3 # FAN_FAN2LEVEL
    __UNIT_SETP = 4 # SETP
    __UNIT_TMP_ROOM = 5 # TMP_ROOM
    __UNIT_PELLET_QTUSED = 6 # PELLET_QTUSED
    __UNIT_STATUS = 7
    __UNIT_STATUSLABEL = 8
    __UNIT_TIMER_ONOFF = 9
    __UNIT_TMP_PELLET_BACKW = 10
    __UNIT_TMP_EXHAUST = 11
    __UNIT_FAN_FAN1V = 12
    __UNIT_FAN_FAN1RPM = 13
    __UNIT_FAN_FAN2V = 14

    status = -1
    onStatus = 0
    
    nextCommands = []
    
    __statusCodes = { "0": "OFF",
                    "1": "OFF TIMER",
                    "2": "TESTFIRE",
                    "3": "HEATUP",
                    "4": "FUELIGN",
                    "5": "IGNTEST",
                    "6": "BURNING",
                    "9": "COOLFLUID",
                    "10": "FIRESTOP",
                    "11": "CLEANFIRE",
                    "12": "COOL" }
    
    # Custom translated Status codes               
    statusCodes = {}

    alarmCodes = { "241": "CHIMNEY ALARM",
                   "243": "GRATE ERROR",
                   "244": "NTC2 ALARM",
                   "245": "NTC3 ALARM",
                   "247": "DOOR ALARM",
                   "248": "PRESS ALARM",
                   "249": "NTC1 ALARM",
                   "250": "TC1 ALARM",
                   "252": "GAS ALARM",
                   "253": "NOPELLET ALARM" }
    
    # Choice of connection box API
    # True stands for new API with LUA cgi script introduced mid-2018
    # False stands for previous API using the Php frontend application
    useNewLUA_API = True
    __API_URI_PHP = "/sendmsg.php"
    __API_URI_LUA = "/cgi-bin/sendmsg.lua"
    API_URI = __API_URI_LUA

    # JSON keys used in results
    __JSON_KEYS = {
            "php" : {
                "INFO_KEY": "Info",
                "ALL_DATA_KEY": "All Data",
                "STATUS": "STATUS",
                "POWER": "POWER",
                "CHRSTATUS": "CHRSTATUS",
                "SETP": "SETP",
                "PELLET_QTUSED": "PELLET_QTUSED",
                "TMP_ROOM": "TMP_ROOM_WATER",
                "TMP_PELLET_BACKW": "TMP_PELLET_BACKW",
                "TMP_EXHAUST": "TMP_EXHAUST",
                "FAN_FAN2LEVEL": "FAN_FAN2LEVEL" },
            "lua" : {
                "INFO_KEY": "INFO",
                "DATA_KEY": "DATA",
                "STATUS": "STATUS",
                "POWER": "PWR",
                "CHRSTATUS": "CHRSTATUS",
                "SETP": "SETP",
                "PELLET_QTUSED": "PQT",
                "TMP_ROOM": "T5",
                "TMP_PELLET_BACKW": "T2",
                "TMP_EXHAUST": "T3",
                "FAN_FAN2LEVEL": "F2L" }
        }

    def __init__(self):
        return

    def onStart(self):
    
        # duplicate status codes
        self.statusCodes = self.__statusCodes.copy()
    
        # Domoticz.Debug("onStart called")
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(1)
            
        # Use new cbox LUA API instead of PHP ?
        if Parameters["Mode4"] == "False":
            self.useNewLUA_API = False
        else:
            self.useNewLUA_API = True

        # Set some variables according to API choice
        if self.useNewLUA_API:
            # we set variables so that they are up-to-date
            Domoticz.Debug("Will use the new LUA API backend")
            self.API_URI = self.__API_URI_LUA
        else:
            Domoticz.Debug("Will use the old PHP API backend")
            self.API_URI = self.__API_URI_PHP

        if (len(Devices) == 0):
            # types / subtypes reference: https://github.com/domoticz/domoticz/blob/master/hardware/hardwaretypes.h
            # Image index for switches: Fireplace: 10, Fan: 7, Heating: 15, Generic: 
            
            # On/Off switch
            Domoticz.Device(Name="On-Off", Unit=self.__UNIT_ONOFF, TypeName="Switch", Image=10, Used=1).Create()
            
            # Power selector switch
            PowerSelectorOptions = {"LevelActions": "|||||",
                                    "LevelNames": "Off|1|2|3|4|5",
                                    "LevelOffHidden": "true",
                                    "SelectorStyle": "1"}
            Domoticz.Device(Name="Power Level", Unit=self.__UNIT_POWER, TypeName="Selector Switch", Image=10, Options=PowerSelectorOptions, Used=1).Create()
            
            # Fan speed selector switch
            FanSpeedSelectorOptions = {"LevelActions": "|||||||",
                                       "LevelNames": "Off|1|2|3|4|5|Auto|Hi",
                                       "LevelOffHidden": "false",
                                       "SelectorStyle": "1"}
            Domoticz.Device(Name="Fan Speed", Unit=self.__UNIT_FAN2LEVEL, TypeName="Selector Switch", Image=7, Options=FanSpeedSelectorOptions, Used=1).Create()
            
            # Setpoint
            Domoticz.Device(Name="Setpoint", Unit=self.__UNIT_SETP, Type=242, Subtype=1, Image=15, Used=1).Create()
            
            # Room Temperature
            Domoticz.Device(Name="Room Temperature", Unit=self.__UNIT_TMP_ROOM, TypeName="Temperature", Used=1).Create()
            
            #  pellet counter
            Domoticz.Device(Name="Pellets Qty Used", Unit=self.__UNIT_PELLET_QTUSED, Type=113, Subtype=0, Switchtype=3, Used=1).Create()
      
            # Status code
            Domoticz.Device(Name="Status code", Unit=self.__UNIT_STATUS, TypeName="Text", Used=0).Create()
            
            # Status Label
            Domoticz.Device(Name="Status", Unit=self.__UNIT_STATUSLABEL, TypeName="Text", Used=1).Create()
            
            # Timer On/Off switch
            Domoticz.Device(Name="Timer", Unit=self.__UNIT_TIMER_ONOFF, TypeName="Switch",Image=1,  Used=1).Create()
            
            # TMP_PELLET_BACKW
            Domoticz.Device(Name="Pellet Backwall Temperature", Unit=self.__UNIT_TMP_PELLET_BACKW, TypeName="Temperature", Used=0).Create()
            
            # TMP_EXHAUST
            Domoticz.Device(Name="Exhaust Temperature", Unit=self.__UNIT_TMP_EXHAUST, TypeName="Temperature", Used=0).Create()
            
            # __UNIT_FAN_FAN1V
            
            # __UNIT_FAN_FAN1RPM
            Domoticz.Device(Name="FAN_FAN1RPM", Unit=self.__UNIT_FAN_FAN1RPM, Type=243, Subtype=7 , Used=0).Create()

        # prepare first commande before connecting
        self.nextCommands.append("GET+ALLS")

        # no need for CHRD with new API because Chrono status info is returned part of the GET+ALLS cmd
        if not self.useNewLUA_API:
            self.nextCommands.append("GET+CHRD")

        self.httpConn = Domoticz.Connection(Name="cbox", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])
        self.httpConn.Connect()
        
        Domoticz.Heartbeat(10)

    def onStop(self):
        Domoticz.Debug("onStop called")

    def onConnect(self, Connection, Status, Description):
        if (Status == 0):
            Domoticz.Debug("Connected successfully to "+Parameters["Address"]+":"+Parameters["Port"])

            # loop on pending commands                
            while ( len( self.nextCommands ) > 0 ):
              cmd = self.nextCommands.pop(0)
              Domoticz.Debug("onConnect: cmd: " +cmd)
              self.sendConnectionBoxCommand( cmd )    
            
        else:
            Domoticz.Error("Failed to connect ("+str(Status)+") to: "+Parameters["Address"]+":"+Parameters["Port"]+" with error: "+Description)

        return True


    def onMessage(self, Connection, Data):
    
        Response = json.loads( Data["Data"].decode("utf-8", "ignore") )

        # JSON keys map to use
        keys = None
        if self.useNewLUA_API:
            keys = self.__JSON_KEYS["lua"]
        else:
            keys = self.__JSON_KEYS["php"]

        # TODO test if INFO_KEY in Response before trying to get the RSP value directly
        # Assume that the result is a valid json response
        if Response[keys["INFO_KEY"]]["RSP"] == "OK":

            DataResponse = None
            if "All Data" in Response:
                DataResponse = Response["All Data"]
            elif "DATA" in Response:
                DataResponse = Response["DATA"]
            elif "Setpoint" in Response:
                DataResponse = Response["Setpoint"]
            elif "Status" in Response:
                DataResponse = Response["Status"]
            elif "RoomFan" in Response:
                DataResponse = Response["RoomFan"]
            elif "Power" in Response:
                DataResponse = Response["Power"]
            elif "Counters" in Response:
                DataResponse = Response["Counters"]
            elif "Chrono Info" in Response:
                DataResponse = Response["Chrono Info"]

            # PELLET_QTUSED
            if keys["PELLET_QTUSED"] in DataResponse:
                UpdateDevice(self.__UNIT_PELLET_QTUSED, 0, str( DataResponse[keys["PELLET_QTUSED"]] ))

            # ROOM Temperature
            if keys["TMP_ROOM"] in DataResponse:
                UpdateDevice(self.__UNIT_TMP_ROOM, 0, str( DataResponse[keys["TMP_ROOM"]] ))
            
            # TMP_PELLET_BACKW
            if keys["TMP_PELLET_BACKW"] in DataResponse:
                UpdateDevice(self.__UNIT_TMP_PELLET_BACKW, 0, str( DataResponse[keys["TMP_PELLET_BACKW"]] ))
            
            # TMP_EXHAUST
            if keys["TMP_EXHAUST"] in DataResponse:
                UpdateDevice(self.__UNIT_TMP_EXHAUST, 0, str( DataResponse[keys["TMP_EXHAUST"]] ))
            
            # Setpoint
            if keys["SETP"] in DataResponse:
                UpdateDevice(self.__UNIT_SETP, 0, str( DataResponse[keys["SETP"]] ))

            # Status
            if keys["STATUS"] in DataResponse:
                self.status = int( DataResponse[keys["STATUS"]] )

                # Update status code
                Domoticz.Debug("Status code retrieved from cbox:"+str(self.status))
                UpdateDevice(self.__UNIT_STATUS, 3, str(self.status))

                # update onStatus and On/Off Switch according to status code
                if (self.status >= 2 and self.status <= 12):
                    self.onStatus = 1
                    UpdateDevice(self.__UNIT_ONOFF, 1, str("On"))
                else:
                    self.onStatus = 0
                    UpdateDevice(self.__UNIT_ONOFF, 0, str("Off"))

                # Update status label
                UpdateDevice(self.__UNIT_STATUSLABEL, 0, self.statusCodes.get(str(self.status)))
          
          
            # RoomFan
            if keys["FAN_FAN2LEVEL"] in DataResponse:
                newRoomFanLevel = int( DataResponse[keys["FAN_FAN2LEVEL"]] )

                Domoticz.Debug("Fan Speed retrieved from cbox:"+str(newRoomFanLevel))
                if ( newRoomFanLevel >= 1 ) and (newRoomFanLevel <= 5): # 1 to 5
                    value = int(newRoomFanLevel * 10)
                    UpdateDevice(self.__UNIT_FAN2LEVEL, self.onStatus, str(value))
                elif ( newRoomFanLevel == 7 ): # OFF
                    UpdateDevice(self.__UNIT_FAN2LEVEL, 0, 0)
                elif ( newRoomFanLevel == 0 ): # Auto
                    UpdateDevice(self.__UNIT_FAN2LEVEL, self.onStatus, 60)
                elif ( newRoomFanLevel == 6 ): # HI
                    UpdateDevice(self.__UNIT_FAN2LEVEL, self.onStatus, 70)

            # Power level
            if keys["POWER"] in DataResponse:
                newPowerLevel = int( DataResponse[keys["POWER"]] )

                Domoticz.Debug("Power level retrieved from cbox:"+str(newPowerLevel))
                if ( newPowerLevel >= 1 ) and (newPowerLevel <= 5): # 1 to 5
                    value = int(newPowerLevel * 10)
                    UpdateDevice(self.__UNIT_POWER, self.onStatus, str(value))
                else:
                    Domoticz.Error("Unknown power value:"+str(newPowerLevel))

            # Chrono Info
            if keys["CHRSTATUS"] in DataResponse:
                newChronoInfo = int( DataResponse[keys["CHRSTATUS"]] )

                Domoticz.Debug("Chrono info retrieved from cbox:"+str(newChronoInfo))
                if (newChronoInfo == 1):
                    UpdateDevice(self.__UNIT_TIMER_ONOFF, 1, str("On"))
                else:
                    UpdateDevice(self.__UNIT_TIMER_ONOFF, 0, str("Off"))
            # else:
            # TODO what was the reason for Updating TIMER_ONOFF based on status ?!?
            #     if ( self.status == 0):
            #         UpdateDevice(self.__UNIT_TIMER_ONOFF, 0, str("Off"))
            #     elif ( self.status == 1):
            #         UpdateDevice(self.__UNIT_TIMER_ONOFF, 1, str("On"))

        # NO RSP: OK response          
        else:
            Domoticz.Error("Error in Connection Box response: "+str(Status))

        return True 
    
    #    
    # Called when a command is received from Domoticz. The Unit parameters matches the Unit specified in the device definition and should be used to map commands
    # to Domoticz devices. Level is normally an integer but may be a floating point number if the Unit is linked to a thermostat device. This callback should be
    # used to send Domoticz commands to the external hardware. 
    #
    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Command '" + str(Command) + "', Level: " + str(Level) + ", Connected: " + str(self.httpConn.Connected()))
        
        Command = Command.strip()
        action, sep, params = Command.partition(' ')
        action = action.capitalize()
        
        if (Unit == self.__UNIT_FAN2LEVEL): # Fan Speed Selector Switch
            fanLevel = 2
            if (int(Level) >= 10 ) and  (int(Level) <= 50): # 1, 2, 3, 4, 5
                fanLevel = int(int(Level) / 10)  
            elif (int(Level) == 0): # Off
                fanLevel = 7
            elif (int(Level) == 60): # Auto
                fanLevel = 0
            elif (int(Level) == 70): # Hi
                fanLevel = 6
               
            Domoticz.Debug("Setting new fan speed:"+str(fanLevel))
            cmd = "SET+RFAN+"+str(fanLevel)
            self.sendConnectionBoxCommand(cmd)
            
        elif (Unit == self.__UNIT_POWER): # Power Level Selector Switch
            powerLevel = int(int(Level) / 10)
            Domoticz.Debug("Setting new power level:"+str(powerLevel))
            cmd = "SET+POWR+"+str(powerLevel)
            self.sendConnectionBoxCommand(cmd)
            
        elif (Unit == self.__UNIT_ONOFF): # On/Off Switch
            if (action == 'Off'):
              Domoticz.Debug("Switching Off")
              self.onStatus = 0
              # UpdateDevice(self.__UNIT_ONOFF, 0, str("Off"))
              cmd = "CMD+OFF"
              self.sendConnectionBoxCommand(cmd)
            elif (action == 'On'):
              Domoticz.Debug("Switching On")
              self.onStatus = 1
              # UpdateDevice(self.__UNIT_ONOFF, 1, str("On"))
              cmd = "CMD+ON"
              self.sendConnectionBoxCommand(cmd)
            return True
        
        elif (Unit == self.__UNIT_SETP): # Setpoint
            # (ConnectionBox) onCommand called for Unit 4: Command 'Set Level', Level: 20.0, Connected: False
            newSetpoint = int(Level)  # convert into integer to round float
            Domoticz.Debug("onCommand with new Setpoint:"+str(newSetpoint))
            cmd = "SET+SETP+"+str(newSetpoint)
            self.sendConnectionBoxCommand(cmd)
            
        elif (Unit == self.__UNIT_TIMER_ONOFF): # Timer On/Off Switch
            if (action == 'Off'):
              Domoticz.Debug("Switching Timer Off")
              UpdateDevice(self.__UNIT_TIMER_ONOFF, 0, str("Off"))
              cmd = "SET+CSST+0"
              self.sendConnectionBoxCommand(cmd)
            elif (action == 'On'):
              Domoticz.Debug("Switching Timer On")
              UpdateDevice(self.__UNIT_TIMER_ONOFF, 1, str("On"))
              cmd = "SET+CSST+1"
              self.sendConnectionBoxCommand(cmd)
              
        return True


    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Debug("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)


    def onDisconnect(self, Connection):
        Domoticz.Debug("Device "+Parameters["Address"]+":"+Parameters["Port"]+" has disconnected")
        return


    def onHeartbeat(self):

        # TODO test Datetime
        # 2018-11-14 22:29:44 => YYYY-MM-DD HH:mm:SS => %Y-%m-%d %H / %Y-%m-%d %H:%M:%S
        # d = datetime.today()
        # # Domoticz.Debug("Datetime " + d.isoformat())
        # dtFormat = "%Y-%m-%d %H:%M:%S"
        # Domoticz.Debug("Local Datetime " + d.strftime( dtFormat ) )

        # # stoveDateTimeStr = "2018-11-15 07:27:28"
        # stoveDateTimeStr = "2018-11-19 18:28:00"
        # stoveDateTime = datetime.strptime( stoveDateTimeStr, dtFormat )
        # Domoticz.Debug("Stove Datetime " + stoveDateTime.isoformat() )

        # timedelta2 = d - stoveDateTime
        # Domoticz.Debug("Time delta " + str(timedelta2.total_seconds()) +" seconds" )

        # fiveMinDelta = timedelta(minutes=1)

        # if (d -  fiveMinDelta) < stoveDateTime and stoveDateTime < (d + fiveMinDelta):
        #     Domoticz.Debug("+ ou - 1 min")
        # else:
        #     Domoticz.Debug("en dehors des clous")
        
        self.nextConnect = self.nextConnect - 1
        
        if (self.nextConnect <= 0):
            self.nextConnect = 6
            self.updateConnectionBoxStatus()
            
        return True
            
#         if self.httpConn.Connected():
#             # updates
#             if ( self.oustandingPings == 1 or self.oustandingPings == 12 ):
#               Domoticz.Debug("Connection is up for 30s now, time to get an update")
#               self.sendConnectionBoxStatusCommands()
#               self.oustandingPings = self.oustandingPings + 1
#               
#             # forcing disconnect after 3*20 sec
#             elif (self.oustandingPings > 20):
#                 Domoticz.Debug("Forcing to disconnect")
#                 self.httpConn.Disconnect()
#                 self.nextConnect = 0
# 
#             else:
#                 Domoticz.Debug("Sending /null pings")
#                 data = ''
#                 headers = { 'Content-Type': 'text/xml; charset=utf-8', \
#                             'Connection': 'keep-alive', \
#                             'Accept': 'Content-Type: text/html; charset=UTF-8', \
#                             'Host': Parameters["Address"]+":"+Parameters["Port"], \
#                             'User-Agent':'Domoticz/1.0', \
#                             'Content-Length' : "%d"%(len(data)) }
#                 # self.httpConn.Send(data, 'GET', '/null', headers)
#                 self.oustandingPings = self.oustandingPings + 1
#             
#         else:
#             # if not connected try and reconnects every 3 heartbeats
#             self.oustandingPings = 0
#             self.nextConnect = self.nextConnect - 1
#             if (self.nextConnect <= 0):
#                 self.nextConnect = 3
#                 self.httpConn.Connect()
#         return True
        
    def updateConnectionBoxStatus(self):
    
        if self.httpConn.Connected():
            self.sendConnectionBoxCommand("GET+ALLS", False)

            # no need for CHRD with new API because Chrono status info is returned part of GET+ALLS cmd
            if not self.useNewLUA_API:
                self.sendConnectionBoxCommand("GET+CHRD", False)

        else:
            self.nextCommands.append("GET+ALLS")

            # no need for CHRD with new API because Chrono status info is returned part of GET+ALLS cmd
            if not self.useNewLUA_API:
                self.nextCommands.append("GET+CHRD")

            self.httpConn.Connect()
      

    def sendConnectionBoxCommand(self, command, prio = True):
        if self.httpConn.Connected():
            Domoticz.Debug("onHeartbeat called, Connection is alive.")
            
            data = ''
            headers = { 'Content-Type': 'text/xml; charset=utf-8', \
                        'Connection': 'keep-alive', \
                        'Accept': 'Content-Type: text/html; charset=UTF-8', \
                        'Host': Parameters["Address"]+":"+Parameters["Port"], \
                        'User-Agent':'Domoticz/1.0', \
                        'Content-Length' : "%d"%(len(data)) }

            sendData = { 'Verb' : 'GET',
                         'URL'  : self.API_URI+'?cmd='+command,
                         'Headers' : headers
                       }
            self.httpConn.Send(sendData)
            
            
        else:
            if ( self.nextCommands.count(command) == 0 ):
                if prio:
                    self.nextCommands.insert(0, command)
                    Domoticz.Debug("Command "+command+" added(insert) by sendConnectionBoxCommand")
                else:
                    self.nextCommands.append(command)
                    Domoticz.Debug("Command "+command+" added(append) by sendConnectionBoxCommand")
            
            if not self.httpConn.Connecting(): 
              self.httpConn.Connect()
            
            
    def updateCustomStatusCodes(self, customCodesStr):
        customCodesDict = None
        try:
           customCodesDict = ast.literal_eval(customCodesStr)
        except:
          Domoticz.Error("Bad syntax for custom codes:"+customCodesStr)
          
        if customCodesDict == None:
          return
        
        for code, newValue in customCodesDict.items():
          Domoticz.Debug("custom label for: "+code)
          found = False
          
          for key, value in self.statusCodes.items():
            if ( code == key ):
              found = True
              Domoticz.Debug("Code "+code+" found in built-in codes map as key")
              self.statusCodes[key] = newValue
            elif ( code == value ):
              found = True
              Domoticz.Debug("Code "+code+" found in built-in codes map as value")
              self.statusCodes[key] = newValue
              
          if ( not found ):
            Domoticz.Debug("Code "+code+" NOT found in built-in codes map")
        
        Domoticz.Debug("### Final dict of codes ####")
        for key, value in self.statusCodes.items():
          Domoticz.Debug("key: "+key+":"+value)                  
    

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

################################################################################
# Generic helper functions
################################################################################
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

def DumpConfigToLog2():
    # Show parameters
    Domoticz.Debug("Parameters count.....: " + str(len(Parameters)))
    for x in Parameters:
        if Parameters[x] != "":
           Domoticz.Debug("Parameter '" + x + "'...: '" + str(Parameters[x]) + "'")
    
    # Show settings
    Domoticz.Debug("Settings count...: " + str(len(Settings)))
    for x in Settings:
       Domoticz.Debug("Setting '" + x + "'...: '" + str(Settings[x]) + "'")
    
    # Show images
    Domoticz.Debug("Image count..........: " + str(len(Images)))
    for x in Images:
        Domoticz.Debug("Image '" + x + "...': '" + str(Images[x]) + "'")
    
    # Show devices
    Domoticz.Debug("Device count.........: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device...............: " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device Idx...........: " + str(Devices[x].ID))
        Domoticz.Debug("Device Type..........: " + str(Devices[x].Type) + " / " + str(Devices[x].SubType))
        Domoticz.Debug("Device Name..........: '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue........: " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue........: '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device Options.......: '" + str(Devices[x].Options) + "'")
        Domoticz.Debug("Device Used..........: " + str(Devices[x].Used))
        Domoticz.Debug("Device ID............: '" + str(Devices[x].DeviceID) + "'")
        Domoticz.Debug("Device LastLevel.....: " + str(Devices[x].LastLevel))
        Domoticz.Debug("Device Image.........: " + str(Devices[x].Image))
    return

def UpdateDevice(Unit, nValue, sValue):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it 
    if (Unit in Devices):
        if (Devices[Unit].nValue != nValue):
            Devices[Unit].Update(nValue=nValue, sValue=str(sValue))
            Domoticz.Debug("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+") due to different in nValue")
        elif ( str(Devices[Unit].sValue) != str(sValue) ):
            Devices[Unit].Update(nValue=nValue, sValue=str(sValue))
            Domoticz.Debug("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+") due to different in sValue")
    return
    
def DumpHTTPResponseToLog(httpDict):
    if isinstance(httpDict, dict):
        Domoticz.Log("HTTP Details ("+str(len(httpDict))+"):")
        for x in httpDict:
            if isinstance(httpDict[x], dict):
                Domoticz.Log("--->'"+x+" ("+str(len(httpDict[x]))+"):")
                for y in httpDict[x]:
                    Domoticz.Log("------->'" + y + "':'" + str(httpDict[x][y]) + "'")
            else:
                Domoticz.Log("--->'" + x + "':'" + str(httpDict[x]) + "'")
