import datetime
import pandas as pd
from influxdb import InfluxDBClient
from flask import Flask, current_app

app = Flask(__name__)
app.config.from_object('config')

with app.app_context():
    INFLUXDB_HOST     = app.config['INFLUXDB_HOST']
    INFLUXDB_HOST     = app.config['INFLUXDB_HOST']
    INFLUXDB_PORT     = app.config['INFLUXDB_PORT']
    INFLUXDB_USERNAME = app.config['INFLUXDB_USERNAME']
    INFLUXDB_PASSWORD = app.config['INFLUXDB_PASSWORD']
    INFLUXDB_NAME     = app.config['INFLUXDB_NAME']


def get_interface_ifName(hostname,interface):
#    INFLUXDB_HOST = '127.0.0.1'
#    INFLUXDB_NAME = 'telegraf'
    timestamp = datetime.datetime.utcnow().isoformat()
#	client = InfluxDBClient(INFLUXDB_HOST,'8086','','',INFLUXDB_NAME)

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
