import pandas as pd
from influxdb import InfluxDBClient
from flask import Flask, current_app

app = Flask(__name__)
app.config.from_object('config')

with app.app_context():
    INFLUXDB_HOST     = app.config['INFLUXDB_HOST']
    INFLUXDB_PORT     = app.config['INFLUXDB_PORT']
    INFLUXDB_USERNAME = app.config['INFLUXDB_USERNAME']
    INFLUXDB_PASSWORD = app.config['INFLUXDB_PASSWORD']
    INFLUXDB_NAME     = app.config['INFLUXDB_NAME']


#INFLUXDB_HOST = '127.0.0.1'
#INFLUXDB_NAME = 'telegraf'

client = InfluxDBClient(
                INFLUXDB_HOST,
                INFLUXDB_PORT,
                INFLUXDB_USERNAME,
                INFLUXDB_PASSWORD,
                INFLUXDB_NAME
            )


def get_max_util(hostname, interface, start):
    if interface == 0:
        return -1
    int(start)
    queryurl = '''SELECT max(non_negative_derivative) as bps from (SELECT non_negative_derivative(max(ifHCOutOctets), 1s) *8 from
                        interface_statistics where hostname =~ /%s/ and ifIndex ='%s' AND time >= now()- %sh
                        group by time(5m))''' % (hostname, interface, start)
    result = client.query(queryurl)
    # print queryurl
    points = list(result.get_points(measurement='interface_statistics'))
    if not points:
        return -1
    df = pd.DataFrame(points)
    df = df.to_dict(orient='records')
    result = int(round(df[0]['bps']))
    return result
