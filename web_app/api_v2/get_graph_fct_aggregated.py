import datetime
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


def get_graph_aggregated(source,target):
#   INFLUXDB_HOST = '127.0.0.1'
#   INFLUXDB_NAME = 'telegraf_agg'

    timestamp = datetime.datetime.utcnow().isoformat()
#   client = InfluxDBClient(INFLUXDB_HOST,'8086','','',INFLUXDB_NAME)

    client = InfluxDBClient(
                    INFLUXDB_HOST,
                    INFLUXDB_PORT,
                    INFLUXDB_USERNAME,
                    INFLUXDB_PASSWORD,
                    INFLUXDB_NAME
                )


    queryurl = '''SELECT sum(bps_out) as bps from 
                      h_interface_statistics where source =~ /%s/ and target =~ /%s/ 
                      AND time > now()- 7d GROUP BY time(1h)''' %(source,target) 
    result = client.query(queryurl)
    points = list(result.get_points(measurement='h_interface_statistics'))
    df = pd.DataFrame(points)
    df1=df.reindex(columns=["time","bps"]).to_csv(index=False)
    return df1
