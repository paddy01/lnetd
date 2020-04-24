from flask import Flask, Blueprint, render_template, session, current_app
from flask_login import login_required
import pandas as pd
import json
from flask import Flask, redirect, request, jsonify
from flask_cors import CORS, cross_origin
from database import db
from objects_v2.models import Routers,Links,Links_latency,Node_position
from objects_v2.models import External_topology_temp,External_topology,External_position
from objects_v2.models import International_PoP,International_PoP_temp
from objects_v2.models import App_external_flows,Transit_Cost
from base_v2.basic_role import requires_roles

from .generate_data import generate_data
from .mutils import generat_unique_info, generate_traffic_util,get_month_util

from influxdb import InfluxDBClient
from datetime import date, timedelta

#INFLUXDB_HOST = '127.0.0.1'
#INFLUXDB_NAME = 'telegraf_agg'
#client = InfluxDBClient(INFLUXDB_HOST, '8086', '', '', INFLUXDB_NAME)
app = Flask(__name__)
app.config.from_object('config')

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



blueprint = Blueprint(
    'map_blueprint',
    __name__,
    url_prefix = '/map',
    template_folder = 'templates',
    static_folder = 'static'
    )



@blueprint.route('/save_cost_table',methods=['POST','GET'])
@login_required
def save_cost_table():
    arr = request.args['arr']
    df = pd.DataFrame(eval(arr))
    df = df.drop(['index'], axis=1)
    print('this is the df\n',df)
    df.to_sql(name='Transit_Cost', con=db.engine, if_exists='replace' )
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

@blueprint.route('/cost_report')
@login_required
def cost_report():
    try:
      today = date.today().replace(day=1)
      prev = today - timedelta(days=1)
      end_interval = today.strftime("%Y-%m")+"-01"
      start_interval = prev.strftime("%Y-%m")+"-01"
      df = pd.read_sql(db.session.query(Transit_Cost).filter(Transit_Cost.index >=0).statement,db.session.bind)
      df['commit'] = df['commit'].astype(float)
      df['commit_cost'] = df['commit_cost'].astype(float)
      df['burst_cost'] = df['burst_cost'].astype(float)
      #get util for provider and pop for between 1st of each month , that's in the get_month_util
      df['util'] = df.apply(lambda row: get_month_util(row['provider'],row['pop_name']),axis=1)
      #calculate if util is above commit rate
      df['burstable'] = round(df['util'] - df['commit'],2)
      #if it is then pir is not 0
      df['burst'] = df.apply(lambda x: 0 if x['burstable']<0 else x['burstable'], axis=1)
      #calculate the billing cost , commit cost + pir * pir_cost
      df['total'] = df.apply(lambda row: row['commit_cost'] + (row['burst'] * row['burst_cost']),axis=1)
      df['total'] = round(df['total'],2)
      df.drop(['burstable'], axis=1, inplace=True)
      values = df.to_dict(orient='records')
      return render_template('cost_report.html',values=values,start_interval=start_interval,end_interval=end_interval)
    except Exception as e:
      print(e)
      return render_template('cost_report.html',values=[{}])

@blueprint.route('/interface_graph')
@login_required
def interface_graph():
    routers = Routers.query.all()
    router_name = [ router.name for router in routers ]
    print(router_name)
    interface_name = ''
    return render_template('interface_graph.html',router_name=router_name,interface_name=interface_name)

@blueprint.route('/static_map',methods=['GET', 'POST'])
@login_required
def static_map():
    current_user = session['_user_id']
    node_position = pd.read_sql(db.session.query(External_position).filter(External_position.user == current_user).statement,db.session.bind)
    node_position = node_position.to_dict(orient='records')
    df = pd.read_sql(db.session.query(External_topology).filter(External_topology.index >=0).statement,db.session.bind)
    isis_links = df.to_dict(orient='records')
    traffic_values = generate_traffic_util(df)
    return render_template(
                           'static_map.html',values=isis_links,
                                node_position=node_position,traffic_values=traffic_values)

@blueprint.route('/static_time')
@login_required
def static_time():
    current_user = session['_user_id']
    node_position = pd.read_sql(db.session.query(External_position).filter(External_position.user == current_user).statement,db.session.bind)
    node_position = node_position.to_dict(orient='records')
    df = pd.read_sql(db.session.query(External_topology).filter(External_topology.index >=0).statement,db.session.bind)
    isis_links = df.to_dict(orient='records')
    return render_template('static_time.html',values=isis_links, node_position=node_position)

@blueprint.route('/edit_static_map',methods=['GET', 'POST'])
@login_required
@requires_roles('admin')
def edit_static_map():
    current_user = session['_user_id']
    df = pd.read_sql(db.session.query(External_topology_temp).filter(External_topology_temp.index >=0).statement,db.session
.bind)
    isis_links = df.to_dict(orient='records')# External_topology_temp
    df_router_name = pd.read_sql(db.session.query(Links.source.distinct()).statement,db.session.bind)
    router_name = df_router_name['anon_1'].values.tolist()
    return render_template('edit_static_map.html',values=isis_links,router_name=router_name)

@blueprint.route('/external_flow',methods=['GET', 'POST'])
@login_required
def external_flow():
    peer = request.form.get('peer')
    if peer:
        df = pd.read_sql(db.session.query(App_external_flows).filter(App_external_flows.name == peer).statement,db.session.bind)
        transit = df.to_dict(orient='records')
        name = transit[0]['name']
        router_ip = transit[0]['router']
        ifindex = transit[0]['if_index']
        #print('found a peer------------------------',peer,name,router_ip,ifindex)
    else:
        peer = 'AMSIX'
        name = 'AMSIX'
        router_ip = '10.3.3.3'
        ifindex = '68'
        #print(peer,name,router_ip,ifindex)
    diagram = generate_data(name,router_ip,ifindex)
    app_netflow_config = App_external_flows.query.all()
    return render_template('external_flow.html', values=diagram,peer=peer,app_netflow_config=app_netflow_config)


@blueprint.route('/edit_international_pop',methods=['GET', 'POST'])
@login_required
@requires_roles('admin')
def edit_internation_pop():
    df = pd.read_sql(db.session.query(International_PoP_temp).filter(International_PoP_temp.index >=0).statement,db.session.bind)
    df['id'] = df['index']
    isis_links = df.to_dict(orient='records')# External_topology_temp
    df_router_name = pd.read_sql(db.session.query(Links.source.distinct()).statement,db.session.bind)
    columns = [
            { "field": "state","checkbox":True },
            { "field": "id","title":"id","sortable":False,"class":"hide_me"},
            { "field": "index","title":"index","sortable":False,"class":"hide_me"},
            { "field": "name","title":"name","sortable":True,"editable":True},
            { "field": "routers","title":"routers","sortable":False,"editable":True},
            { "field": "region","title":"region","sortable":False,"editable":True},
            { "field": "lat","title":"lat","sortable":False,"editable":True},
            { "field": "lon","title":"lon","sortable":False,"editable":True},
            { "field": "Action","title":"Action","formatter":"TableActions"},
            ]
    return render_template('edit_international_pop.html',values=isis_links,columns=columns)

@blueprint.route('/international_pop')
@login_required
def internation_pop():
    internation_pop = International_PoP.query.all()
    qry = db.session.query(International_PoP).filter(International_PoP.region.like('EA')).statement
    df_ea = pd.read_sql(qry,db.session.bind)
    df_ea = df_ea.to_dict(orient='records')
    qry = db.session.query(International_PoP).filter(International_PoP.region.like('SA')).statement
    df_sa = pd.read_sql(qry,db.session.bind)
    df_sa = df_sa.to_dict(orient='records')
    qry = db.session.query(International_PoP).filter(International_PoP.region.like('EU')).statement
    df_eu = pd.read_sql(qry,db.session.bind)
    df_eu = df_eu.to_dict(orient='records')
    return render_template('international_pop.html', values=internation_pop,df_ea=df_ea,df_sa=df_sa,df_eu=df_eu)

@blueprint.route('/peer_report')
@login_required
def peer_report():
    objects_counters = generat_unique_info()
    objects_counters = sorted(objects_counters , key = lambda i: i['index'])
    #print(objects_counters)
    return render_template('peer_report.html',objects_counters=objects_counters)


@blueprint.route('/get_graph_data_interface',methods=['GET', 'POST'])
@login_required
def get_graph_data_interface():
    INFLUXDB_NAME = 'telegraf'
    #client = InfluxDBClient(INFLUXDB_HOST, '8086', '', '', INFLUXDB_NAME)
    client = InfluxDBClient(
                    INFLUXDB_HOST,
                    INFLUXDB_PORT,
                    INFLUXDB_USERNAME,
                    INFLUXDB_PASSWORD,
                    INFLUXDB_NAME
                )

    rvalue = request.args
    if rvalue['time'] == '24h':
        query = f"""select non_negative_derivative(last(ifHCOutOctets), 1s) *8  as bps_out , non_negative_derivative(last(ifHCInOctets), 1s) *8 as bps_in , last(ifHighSpeed) as capacity
		from interface_statistics where hostname =~/{rvalue['router']}/ and ifName ='{rvalue['interface']}' 
		AND time >= now()- 24h and time < now()
                GROUP BY time(5m) """
    else:
        query = f"""select non_negative_derivative(last(ifHCOutOctets), 1s) *8  as bps_out , non_negative_derivative(last(ifHCInOctets), 1s) *8 as bps_in , last(ifHighSpeed) as capacity
                from interface_statistics where hostname =~/{rvalue['router']}/ and ifName ='{rvalue['interface']}'
                AND time >= now()- 365d and time < now()
                GROUP BY time(1h) """
    #print(query)
    result = client.query(query)
    t = list(result.get_points(measurement='interface_statistics'))
    df = pd.DataFrame(t)
    if df.empty:
        return "status error", "400 No SNMP data for this router and interface"
    #jsonify('No data found'),400 
    df['name'] = rvalue['interface']
    df = df.fillna(0)
    result = df.reindex(columns=["time","bps_in","bps_out","name","capacity"]).to_dict(orient='records')
    #print('888888888888888------',query,result,df)
    return jsonify(result)

@blueprint.route('/get_graph_data',methods=['GET', 'POST'])
@login_required
def get_graph_data():
    rvalue = request.args
    if rvalue['type'] != '':
        query = f'''select sum(cir) as cir, sum(capacity) as capacity, sum(bps_out) as bps_out ,sum(bps_in) as bps_in from h_transit_statistics where country =~/{rvalue['country']}/
        and pop =~/{rvalue['pop']}/
        and type =~ /{rvalue['type']}/
        AND time >= now()- 7d and time < now()
                        GROUP BY time(1h)'''
    else:
        query = f'''select sum(cir) as cir, sum(capacity) as capacity, sum(bps_out) as bps_out ,sum(bps_in) as bps_in from h_transit_statistics where country =~/{rvalue['country']}/
        and pop =~/{rvalue['pop']}/
        and target =~ /{rvalue['target']}/
        AND time >= now()- 7d and time < now()
                        GROUP BY time(1h)'''
    result = client.query(query)
    t = list(result.get_points(measurement='h_transit_statistics'))
    df = pd.DataFrame(t)
    df = df.fillna(0)
    df['div_id'] = rvalue['index']
    df['name'] = rvalue['name']
    df['cir'] = df['cir'] * 1000000
    df['capacity'] = df['capacity'] * 1000000
    result = df.reindex(columns=["time","bps_in","bps_out","div_id","name","cir","capacity"]).to_dict(orient='records')
    #print(df)
    return jsonify(result)
