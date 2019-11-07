#!/usr/bin/python

import io
import os
import sys
import time
import json
import requests
import types
import datetime
from influxdb import InfluxDBClient

# pip install influxdb

HC2_IP = "XXX.XXX.XXX.XXX"
HC2_LOGIN = 'example@example.com'
HC2_PASSWORD = 'password'
INFLUXDB_HOST = 'XXX.XXX.XXX.XXX'
INFLUXDB_PORT = '0000'
INFLUXDB_USER = 'user'
INFLUXDB_PASSWD = 'password'
INFLUXDB_DBNAME = 'telegraf'


#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-

fname = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), ".hc2")

def getHC2Item(name):
    r = requests.get('http://'+HC2_IP+'/api/' + name, auth=(HC2_LOGIN, HC2_PASSWORD))
    if r.status_code==200:  
       return r.json()

def poll(lastPoll):
    try:
	r = requests.get('http://'+HC2_IP+'/api/refreshStates?last='+str(lastPoll), auth=(HC2_LOGIN, HC2_PASSWORD))
	if r.status_code==200:
	    return r.json()
	else:
	    return None
    except requests.exceptions.RequestException as e:  # This is the correct syntax
	logger.error('FIBARO ERROR! Exception {}'.format(e))
	return None
    except: # catch *all* exceptions
	e = sys.exc_info()[0]
	logger.error("FIBARO Unexpected error:", e)
	return None

devices = getHC2Item("devices")
rooms = getHC2Item("rooms")
# sections = getHC2Item("sections")

def getDeviceById(deviceId):
    return next(iter(filter(lambda x: x['id'] == deviceId, devices)), None)

def getDeviceNameById(deviceId):
    device = next(iter(filter(lambda x: x['id'] == deviceId, devices)), None)
    if device != None: return device["name"]
    return None

def getRoomNameByDeviceId(deviceId):
    device = next(iter(filter(lambda x: x['id'] == deviceId, devices)), None)
    if device != None:
       roomID = device["roomID"]
       room = next(iter(filter(lambda x: x['id'] == roomID, rooms)), None)
       if room != None: return room["name"]
    return "No room"

def saveToInfluxDB(id, value, name, room, timestamp, kind):
     DATABASE        = INFLUXDB_DBNAME
     HOST            = INFLUXDB_HOST
     PORT            = INFLUXDB_PORT
     USER            = INFLUXDB_USER
     PASSWORD        = INFLUXDB_PASSWD

     client = InfluxDBClient(host=HOST, port=PORT, username=USER, password=PASSWORD, database=DATABASE)
     #client.drop_database(DATABASE)
     # client.create_database(DATABASE)

     # timetsamp = datetime.datetime.utcnow().isoformat() + 'Z'

     measurements = []
     tags = {}
     tags["sensor_id"] = int(id)
     tags["sensor_name"] = name
     tags["sensor_type"] = kind
     tags["room_name"] = room
     measurements.append({
         "measurement": "devices",
         "time": timestamp * 1000000000, # datetime.datetime.utcnow().isoformat() + 'Z',
         "tags": tags,
         "fields": {
             "value": float(value)
         }
     })
     #print json.dumps(measurements, indent=4, sort_keys=True)
     if measurements: client.write_points(measurements)


last = 0
if os.path.exists(fname):
   with open(fname, "r") as f:
      last = int(f.read())
      f.close()

data = poll(last)
# print(data)
last = int(data["last"])
timestamp = int(data["timestamp"])

with open(fname, 'w') as f:
  f.write('%d' % last)
  f.close()

if "changes" in data:
   for item in data["changes"]:
       if "value" in item:
          # print(item)
          id = item["id"]
          value = item["value"]
          if value == "true": value = 1
          if value == "false": value = 0 

          kind = ""
          device = getDeviceById(id)
          if device is not None:
             if "type" in device:
                kind = device["type"]

          #print(id, value, getDeviceNameById(id), getRoomNameByDeviceId(id))
          saveToInfluxDB(id, value, getDeviceNameById(id), getRoomNameByDeviceId(id), timestamp, kind)
