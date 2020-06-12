#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from __future__ import print_function
import datetime
import glob
import json
import os
import paho.mqtt.client as mqtt
import sys
import time

from config import *

# These two lines mount the device:
#os.system('modprobe w1-gpio')
#os.system('modprobe w1-therm')

def eprint(*args, **kwargs):
    import traceback
    print(*args, file=sys.stderr, **kwargs)
    print(traceback.format_exc())

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def read_rom(device_folder):
    name_file=device_folder+'/name'
    f = open(name_file,'r')
    return f.readline().strip()

def read_temp_raw(device_file):
    start = time.time()
    f = open(device_file, 'r')
    opentime = time.time()
    lines = f.readlines()
    readtime = time.time()
    f.close()
    closetime = time.time()
    #print(f'read_temp_raw done in {(closetime-start)*1000:2f} ms. Open file = {(opentime-start)*1000:2f}, read lines = {(readtime-opentime)*1000:2f}, close = {(closetime-readtime):2f}.')
    return lines

def read_temp(device_folder):
    device_file = device_folder+"/w1_slave"
    lines = read_temp_raw(device_file)
    # Analyze if the last 3 characters are 'YES'.
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    # Find the index of 't=' in a string.
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        # Read the temperature .
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c

def get_ids():
    base_dir = '/sys/bus/w1/devices/'
    # Get all the filenames begin with 28 in the path base_dir.
    # The temp sensors we care about start with this.
    device_folders = glob.glob(base_dir + '28*')
    return device_folders

def base_topic(rom):
    return f'homeassistant/sensor/ds18b20/{rom}'

def send_update(client, rom, tempC):
    print(f'Update: {rom} C={tempC:3.3f}')
    state_topic = f'{base_topic(rom)}/state'

    state_value = {
        "temperature": tempC
    }

    state_msg = json.dumps(state_value)
    dprint(f"Update: msg={state_msg}")

    client.publish(state_topic, payload=state_msg, qos=MQTT_QOS)

def send_config(client, rom):
    print(f'Configure: {rom}')
    config_topic = f'{base_topic(rom)}/config'

    name = f"DS18B20 {rom}"

    config_value = {
        "name": name,
        "state_topic": f"{base_topic(rom)}/state",
        "value_template": f"{{{{ value_json.temperature }}}}", # escaping curlies is weird in python
        "unique_id": rom,
        "device_class": "temperature",
        "unit_of_measurement": "°C",
        "expire_after": UPDATE_INTERVAL*4
    }

    config_msg = json.dumps(config_value)
    dprint(f"Config: msg={config_msg}")

    client.publish(config_topic, payload=config_msg, qos=MQTT_QOS)


# MQTT event callbacks
def on_connect(client, userdata, flags, rc):
    dprint("MQTT: Connected with result code "+str(rc))

def on_disconnect(client, userdata, rc):
    if rc != 0:
        dprint("MQTT: Unexpected disconnection.")

def on_message(client, obj, msg):
    dprint("MQTT: " + msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

def on_publish(client, obj, mid):
    dprint("MQTT: Published " + str(mid))

def on_subscribe(client, obj, mid, granted_qos):
    dprint("MQTT: Subscribed " + str(mid) + " " + str(granted_qos))

def on_log(client, obj, level, string):
    dprint(string)

def connect_mqtt(client):
    connect_attempt = 0
    while connect_attempt < CONNECTION_ATTEMPTS:
        connect_attempt += 1
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            break;
        except:
            eprint(f'Connection attempt {connect_attempt}/{CONNECTION_ATTEMPTS} failed!');
        time.sleep(1)

    client.on_message = on_message
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_subscribe = on_subscribe
    client.on_disconnect = on_disconnect
    client.on_log = on_log

    client.username_pw_set(MQTT_USER, password=MQTT_PASS)
    client.connect(MQTT_HOST, MQTT_PORT, 60)


def main():
    devices = get_ids()

    if not devices:
        eprint("No devices detected")

    # Set up MQTT connection
    mqttc = mqtt.Client()
    if (MQTT_TLS):
        dprint('Using MQTT with TLS')
        if (MQTT_ROOT_CA):
            print(f"Using specific CA cert(s) for MQTT TLS: '{MQTT_ROOT_CA}'")
            mqttc.tls_set(ca_certs=MQTT_ROOT_CA)
        else:
            mqttc.tls_set()
    else:
        print('Using insecure MQTT (no TLS)')
    connect_mqtt(mqttc)
    mqttc.loop_start()

    # Start config/update loop
    last_config = datetime.datetime.now()
    reconfig = True
    while True:
        for device in devices:
            rom = read_rom(device)
            tempC = read_temp(device)
            if reconfig:
                send_config(mqttc, rom)
                reconfig=False
            send_update(mqttc, rom, tempC)

        now = datetime.datetime.now()
        minutes_since_last_config = (now - last_config).seconds/60
        if minutes_since_last_config > CONFIG_INTERVAL:
            reconfig = True
            last_config = now

        time.sleep(UPDATE_INTERVAL)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Received KeyboardInterrupt. Exiting...')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)

    eprint("Died for an unknown reason")
