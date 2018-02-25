# Palazzetti Connection Box plugin for Domoticz
#
# Author: kinou74, 2018
#
#
#
"""
<plugin key="palazzetti-cbox" name="Palazzetti Connection Box" author="kinou74" version="0.9.0">
    <params>
        <param field="Address" label="Connection Box IP Address" width="200px" required="true" default="127.0.0.1"/>
        <param field="Port" label="Port" width="30px" required="true" default="80"/>
        <param field="Mode5" label="Custom Codes" width="500px" default="" />
        <param field="Mode6" label="Debug" width="75px">
          <options>
            <option label="True" value="Debug"/>
            <option label="False" value="Normal" default="true" />
          </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import json
import ast

class BasePlugin:
    httpConn = None
    runAgain = 6

    __UNIT_ONOFF = 1
    __UNIT_POWER = 2
    __UNIT_FAN2LEVEL = 3 # FAN_FAN2LEVEL
    __UNIT_SETP = 4 # SETP
    __UNIT_ROOMTEMP = 5
    __UNIT_COUNTER = 6
    __UNIT_STATUS = 7
    __UNIT_STATUSLABEL = 8
    __UNIT_TIMER_ONOFF = 9
    __UNIT_TMP_PELLET_BACKW = 10
    __UNIT_TMP_EXHAUST = 11
    __UNIT_FAN_FAN1V = 12
    __UNIT_FAN_FAN1RPM = 13
    __UNIT_FAN_FAN2V = 14

    headers = None
    
    status = -1
    onStatus = 0
    
    # nextCmd = None
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
    
    def __init__(self):
        return

    def onStart(self):
    
        # duplicate status codes
        self.statusCodes = self.__statusCodes.copy()
    
        # Domoticz.Debug("onStart called")
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(1)
        # else:
        #    Domoticz.Debugging(0)
            
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
            Domoticz.Device(Name="Room Temperature", Unit=self.__UNIT_ROOMTEMP, TypeName="Temperature", Used=1).Create()
            
            #  pellet counter
            Domoticz.Device(Name="Pellets Qty Used", Unit=self.__UNIT_COUNTER, Type=113, Subtype=0, Switchtype=3, Used=1).Create()
      
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
            
            # __UNIT_FAN_FAN2V

            

        # a little bit of cleaning            
        # if ("palazzetti-cbox" in Images):
        #   Domoticz.Image('icon.zip').Delete()


        # Devices[self.__UNIT_STATUS].Update(nValue=0, sValue=str(self.status), Image=8)   
        # Devices[9].Update( nValue= 1, sValue= 'On', Image= Images["palazzetti-cbox"].ID )
        
        
        # Loop on custome codes
        if ( Parameters["Mode5"] ):
          self.updateCustomeStatusCodes( Parameters["Mode5"] )
          
        
        
        # Log config
        # DumpConfigToLog()
        # DumpConfigToLog2()
        
        self.httpConn = Domoticz.Connection(Name="cbox", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])
        
        # prepare first commande before connecting
        # self.nextCmd = "GET+ALLS"
        self.nextCommands.append("GET+ALLS")
        self.nextCommands.append("GET+CHRD")
        self.httpConn.Connect()

        Domoticz.Heartbeat(20)


    def onStop(self):
        Domoticz.Debug("onStop called")


#    def onConnect(self, Connection, Status, Description):
#        if (Status == 0):
#            Domoticz.Debug("Connected successfully to: "+Parameters["Address"]+":"+Parameters["Port"])
#            
#            # Headers = {"Connection": "keep-alive", "Accept": "Content-Type: text/html; charset=UTF-8"}
#            # self.CBoxConn.Send({"Verb":"GET", "URL":"/sendmsg.php?cmd=GET+STAT"})
#            
#            sendData = { 'Verb' : 'GET',
#                         'URL'  : '/plop',
#                         'Headers' : { 'Content-Type': 'text/plain; charset=utf-8', \
#                                       'Connection': 'keep-alive', \
#                                       'Accept': 'Content-Type: text/html; charset=UTF-8', \
#                                       'Host': Parameters["Address"]+":"+Parameters["Port"], \
#                                       'User-Agent':'Domoticz/1.0' }
#                       }
#            # Connection.Send(sendData)
            
    def onConnect(self, Connection, Status, Description):
        if (Status == 0):
            Domoticz.Debug("Connected successfully to "+Parameters["Address"]+":"+Parameters["Port"])
            
            #if ( self.nextCmd != None ):
            #    self.sendConnectionBoxCommand(self.nextCmd)
            #    self.nextCmd = None
                
            while ( len( self.nextCommands ) > 0 ):
              cmd = self.nextCommands.pop(0)
              Domoticz.Debug("onConnect: cmd: " +cmd)
              self.sendConnectionBoxCommand( cmd )    
            
        else:
            Domoticz.Error("Failed to connect ("+str(Status)+") to: "+Parameters["Address"]+":"+Parameters["Port"]+" with error: "+Description)
        return True


    def onMessage(self, Connection, Data, Status, Extra):
        # Domoticz.Debug("onMessage called")
        Domoticz.Debug("onMessage: Status="+str(Status))
        
        strData = Data.decode("utf-8", "ignore")
        Response = json.loads(strData)
        
        if (Response["Info"]["RSP"] == "OK"):

          if ("All Data" in Response):
              # PELLET_QTUSED
              UpdateDevice(self.__UNIT_COUNTER, 0, str(Response["All Data"]["PELLET_QTUSED"]))
              # ROOM Temperature
              UpdateDevice(self.__UNIT_ROOMTEMP, 0, str(Response["All Data"]["TMP_ROOM_WATER"]))
              # TMP_PELLET_BACKW
              UpdateDevice(self.__UNIT_TMP_PELLET_BACKW, 0, str(Response["All Data"]["TMP_PELLET_BACKW"]))
              # TMP_EXHAUST
              UpdateDevice(self.__UNIT_TMP_EXHAUST, 0, str(Response["All Data"]["TMP_EXHAUST"]))
              # FAN_FAN1RPM
              UpdateDevice(self.__UNIT_FAN_FAN1RPM, 0, str(Response["All Data"]["FAN_FAN1RPM"]))
              
              
          # Setpoint
          if ("All Data" in Response or "Setpoint" in Response):
              if ("All Data" in Response):
                  UpdateDevice(self.__UNIT_SETP, 0, str(Response["All Data"]["SETP"]))
              else:
                  UpdateDevice(self.__UNIT_SETP, 0, str(Response["Setpoint"]["SETP"]))
          
          # Status
          if ("All Data" in Response or "Status" in Response):
              if ("All Data" in Response):
                  self.status = int(Response["All Data"]["STATUS"])
              else:
                  self.status = int(Response["Status"]["STATUS"])
          
              # Update status
              UpdateDevice(self.__UNIT_STATUS, 3, str(self.status))

              # update onStatus according to real status
              if (self.status >= 2 and self.status <= 12):
                  self.onStatus = 1
                  UpdateDevice(self.__UNIT_ONOFF, 1, str("On"))
              else:
                  self.onStatus = 0
                  UpdateDevice(self.__UNIT_ONOFF, 0, str("Off"))
              
              # Update status label
              # TODO, update with UpdateDevice
              UpdateDevice(self.__UNIT_STATUSLABEL, 0, self.statusCodes.get(str(self.status)))
          
          
          # RoomFan    
          if ("All Data" in Response or "RoomFan" in Response):
              newRoomFanLevel = -1
              if ("All Data" in Response):
                  newRoomFanLevel = int(Response["All Data"]["FAN_FAN2LEVEL"])
              else:
                  newRoomFanLevel = int(Response["RoomFan"]["FAN_FAN2LEVEL"])
          
              Domoticz.Debug("New Fan Speed from Palazzetti:"+str(newRoomFanLevel))
              if ( newRoomFanLevel >= 1 ) and (newRoomFanLevel <= 5): # 1 to 5
                value = int(newRoomFanLevel * 10)
                UpdateDevice(self.__UNIT_FAN2LEVEL, self.onStatus, str(value))
              elif ( newRoomFanLevel == 7 ): # OFF
                UpdateDevice(self.__UNIT_FAN2LEVEL, 0, 0)
              elif ( newRoomFanLevel == 0 ): # Auto
                UpdateDevice(self.__UNIT_FAN2LEVEL, self.onStatus, 60)
          
          # Power level
          if ("All Data" in Response or "Power" in Response):
              newPowerLevel = 0
              if ("All Data" in Response):
                  newPowerLevel = int(Response["All Data"]["POWER"])
              else:
                  newPowerLevel = int(Response["Power"]["POWER"])
          
              Domoticz.Debug("New Power value from Palazzetti:"+str(newPowerLevel))
              if ( newPowerLevel >= 1 ) and (newPowerLevel <= 5): # 1 to 5
                value = int(newPowerLevel * 10)
                UpdateDevice(self.__UNIT_POWER, self.onStatus, str(value))
              else:
                Domoticz.Error("Unknown power value:"+str(newPowerLevel))
          
          # Chrono Info
          # TODO find request to get status
          if ("Chrono Info" in Response):
              newChronoInfo = int(Response["Chrono Info"]["CHRSTATUS"])
              Domoticz.Debug("Chrono info value from Palazzetti:"+str(newChronoInfo))
              if (newChronoInfo == 1):
                  UpdateDevice(self.__UNIT_TIMER_ONOFF, 1, str("On"))
              else:
                  UpdateDevice(self.__UNIT_TIMER_ONOFF, 0, str("Off"))
          else:
              if ( self.status == 0):
                  UpdateDevice(self.__UNIT_TIMER_ONOFF, 0, str("Off"))
              elif ( self.status == 1):
                  UpdateDevice(self.__UNIT_TIMER_ONOFF, 1, str("On"))
                  
        
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
        # Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Command '" + str(Command) + "', Level: " + str(Level) + ", Connected: " + str(self.httpConn.Connected()))
        
        Command = Command.strip()
        action, sep, params = Command.partition(' ')
        action = action.capitalize()
        
        if (Unit == self.__UNIT_FAN2LEVEL): # Fan Speed Selector Switch
            #
            fanLevel = 1
            if (int(Level) >= 10 ) and  (int(Level) <= 50): # 1, 2, 3, 4, 5
              fanLevel = int(int(Level) / 10)  
            elif (int(Level) == 60): # Auto
              fanLevel = 0
            elif (int(Level) == 0): # Off
               fanLevel = 7
               
            Domoticz.Debug("Setting new fan speed:"+str(fanLevel))
            cmd = "SET+RFAN+"+str(fanLevel)
            self.sendConnectionBoxCommand(cmd)
            # Connection.Send('', 'GET', '/sendmsg.php?cmd=SET+FAN+'+fanLevel, headers)
            
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
              cmd = "SET+CSST+0"
              self.sendConnectionBoxCommand(cmd)
            elif (action == 'On'):
              Domoticz.Debug("Switching Timer On")
              cmd = "SET+CSST+1"
              self.sendConnectionBoxCommand(cmd)
            return True



    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Debug("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Debug("Device "+Parameters["Address"]+":"+Parameters["Port"]+" has disconnected")
        return


    def onHeartbeat(self):
        if (self.httpConn.Connecting() or self.httpConn.Connected()):
            Domoticz.Debug("onHeartbeat called, Connection is alive.")
            
            ## self.nextCommands.append("GET+CHRD")
            self.sendConnectionBoxCommand("GET+ALLS")
            self.sendConnectionBoxCommand("GET+CHRD")
            # self.nextCommands.append("GET+CHRD")
        else:
        
            # if (self.nextCmd == None):
            #    self.nextCmd = "GET+ALLS"
                
            if ( self.nextCommands.count("GET+ALLS") == 0 ):
              self.nextCommands.append("GET+ALLS")
              Domoticz.Debug("Command GET+ALLS appended by onHeartbeat")
            
            if ( self.nextCommands.count("GET+CHRD") == 0 ):
              self.nextCommands.append("GET+CHRD")
              Domoticz.Debug("Command GET+CHRD appended by onHeartbeat")
              
            self.httpConn.Connect()


    def sendConnectionBoxCommand(self, command):
        if (self.httpConn.Connecting() or self.httpConn.Connected()):
            Domoticz.Debug("onHeartbeat called, Connection is alive.")
            
            data = ''
            headers = { 'Content-Type': 'text/xml; charset=utf-8', \
                        'Connection': 'keep-alive', \
                        'Accept': 'Content-Type: text/html; charset=UTF-8', \
                        'Host': Parameters["Address"]+":"+Parameters["Port"], \
                        'User-Agent':'Domoticz/1.0', \
                        'Content-Length' : "%d"%(len(data)) }
            Domoticz.Debugging(0)
            self.httpConn.Send(data, 'GET', '/sendmsg.php?cmd='+command, headers)
            
            if Parameters["Mode6"] == "Debug":
              Domoticz.Debugging(1)
        
        else:
            # self.runAgain = self.runAgain - 1
            # if self.runAgain <= 0:
            # self.nextCmd = command
            if ( self.nextCommands.count(command) == 0 ):
              self.nextCommands.append(command)
              Domoticz.Debug("Command "+command+" appended by sendConnectionBoxCommand")
            
            self.httpConn.Connect()
            
            
    def updateCustomeStatusCodes(self, customCodesStr):
        customCodesDict = None
        try:
           customCodesDict = ast.literal_eval(customCodesStr)
        except:
          # break
          Domoticz.Error("Bad syntax for custom codes:"+customCodesStr)
          
        
        if customCodesDict == None:
          return
        
        # Domoticz.Debug("Custom codes dict:")
        # Domoticz.Debug(customCodesDict)
          
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

def onMessage(Connection, Data, Status, Extra):
    global _plugin
    _plugin.onMessage(Connection, Data, Status, Extra)

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
