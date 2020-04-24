import sqlite3
import pandas as pd
import re
from sqlalchemy import create_engine, text
import sys

import datetime
import pandas as pd
from influxdb import InfluxDBClient

from flask import Flask, current_app

app = Flask(__name__)
app.config.from_object('config')

#INFLUXDB_HOST = '127.0.0.1'
#INFLUXDB_NAME = 'telegraf'
#client = InfluxDBClient(INFLUXDB_HOST, '8086', '', '', INFLUXDB_NAME)

with app.app_context():
    INFLUXDB_HOST     = app.config['INFLUXDB_HOST']
    INFLUXDB_PORT     = app.config['INFLUXDB_PORT']
    INFLUXDB_USERNAME = app.config['INFLUXDB_USERNAME']
    INFLUXDB_PASSWORD = app.config['INFLUXDB_PASSWORD']
    INFLUXDB_NAME     = app.config['INFLUXDB_NAME']


client = InfluxDBClient(
                INFLUXDB_HOST,
                INFLUXDB_PORT,
                INFLUXDB_USERNAME,
                INFLUXDB_PASSWORD,
                INFLUXDB_NAME
            )


pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

def get_interface_ifName(hostname,interface):
    try:
        timestamp = datetime.datetime.utcnow().isoformat()
#        client = InfluxDBClient(INFLUXDB_HOST,'8086','','',INFLUXDB_NAME)
        client = InfluxDBClient(
                        INFLUXDB_HOST,
                        INFLUXDB_PORT,
                        INFLUXDB_USERNAME,
                        INFLUXDB_PASSWORD,
                        INFLUXDB_NAME
                    )

        queryurl = "show tag values with key = ifName where hostname =~ /%s/ and ifIndex ='%s'" %(hostname,interface)
        result = client.query(queryurl)
        points = list(result.get_points(measurement='interface_statistics'))
        df = pd.DataFrame(points)
        df.columns = ['Ifindex', 'IfName']
        df1=df.to_dict(orient='records')
        return str(df1[0]['IfName'])
    except Exception as e:
        print(e)
        return 'ge-0/0/0'

def get_util_interface(hostname, interface, direction):
    try:
        if direction == 'in':
            direction = 'ifHCInOctets'
        else:
            direction = 'ifHCOutOctets'
        timestamp = datetime.datetime.utcnow().isoformat()
        queryurl = '''SELECT non_negative_derivative(last(%s), 1s) *8 as bps from interface_statistics
                          where hostname =~ /%s/ and ifName = '%s' AND time >= now()- 10m and time <=now()
                          GROUP BY time(5m)''' % (direction, hostname, interface)
        result = client.query(queryurl)
        # print(queryurl,result)
        points = list(result.get_points(measurement='interface_statistics'))
        df = pd.DataFrame(points)
        df = df.to_dict(orient='records')
        result = int(round(df[0]['bps']))
        return result
    except Exception as e:
        return -1

def generate_from_igp():
    conn = sqlite3.connect("/opt/lnetd/web_app/database.db")
    try:
        df_links = pd.read_sql("SELECT * FROM Links", conn)
        df_links = df_links.drop(['index'], axis=1)
        df_links = df_links.drop(['metric','l_ip','r_ip','capacity', 'errors','util'], axis = 1)
        df_links['node'] = df_links['source']
        df_links['graph_status'] = '1'
        df_links['alert_status'] = '1'
        df_links['interface'] = df_links.apply(lambda row: get_interface_ifName(
            row['node'], row['l_int']), axis=1)
        df_links = df_links.drop(['l_int'], axis = 1)
        df_final = df_links

        df_final['l_ip_r_ip'] = df_final['l_ip_r_ip'].astype(str)
        df_final = df_final.reset_index(drop=True)
        df_final['id'] = df_final.index
        return df_final
    except:
        return pd.DataFrame()
