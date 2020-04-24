from flask import Flask, Blueprint, render_template, request, session, current_app
from flask_login import login_required
from objects_v2.models import Routers,Links,Links_latency,Node_position,Links_Model,App_config,Layer1Topology
from database import db
from collections import Counter,OrderedDict
import pandas as pd
from .get_demand_netflow import *
import json
from influxdb import InfluxDBClient
from sqlalchemy import or_,and_
from .snmp_influx import get_max_util
from .mutils import *
import collections
from functools import reduce

app = Flask(__name__)
app.config.from_object('config')

blueprint = Blueprint(
    'data_blueprint',
    __name__,
    url_prefix = '/data',
    template_folder = 'templates',
    static_folder = 'static'
    )

@blueprint.route('/add_layer1')
@login_required
def add_layer1():
    df = pd.read_sql(db.session.query(Layer1Topology).filter(Layer1Topology.id >=0).statement,db.session.bind)
    layer1_links = df.to_dict(orient='records')
    columns = [
            { "field": "state","checkbox":True},
            { "field": "id","title":"id","sortable":False,"class":"hide_me"},
            { "field": "source","title":"Source","sortable":True,"editable":True},
            { "field": "target","title":"Target","sortable":False,"editable":True},
            { "field": "layer3_mapping","title":"Layer3 Mapping","sortable":True,"editable":True},
            { "field": "status","title":"Status","sortable":False},
            { "field": "Action","title":"Action","formatter":"TableActions"},
            ]
    return render_template('add_layer1_topology.html', values=layer1_links,columns=columns)

@blueprint.route('/model_layer1')
@login_required
def topology_layer1():
    current_user = str(session['_user_id'])
    node_position = pd.read_sql(db.session.query(Node_position).filter(Node_position.user == current_user ).statement,db.session.bind)
    node_position = node_position.to_dict(orient='records')
    df = pd.read_sql(db.session.query(Links).filter(Links.index >=0).statement,db.session.bind)
    isis_links = df.to_dict(orient='records')
    layer1_links = Layer1Topology.query.all()
    return render_template('topology_layer1.html', values=isis_links, node_position=node_position,layer1_links=layer1_links)

@blueprint.route('/topology')
@login_required
def topology():
    current_user = str(session['_user_id'])
    node_position = pd.read_sql(db.session.query(Node_position).filter(Node_position.user == current_user ).statement,db.session.bind)
    node_position = node_position.to_dict(orient='records')
    df = pd.read_sql(db.session.query(Links).filter(Links.index >=0).statement,db.session.bind)
    isis_links = df.to_dict(orient='records')
    return render_template('topology.html', values=isis_links, node_position=node_position)

@blueprint.route('/topology_region1')
@login_required
def topology_region1():
    current_user = str(session['_user_id'])
    node_position = pd.read_sql(db.session.query(Node_position).filter(Node_position.user == current_user ).statement,db.session.bind)
    node_position = node_position.to_dict(orient='records')
    df = pd.read_sql(db.session.query(Links).filter(Links.index >=0).statement,db.session.bind)
    isis_links = df.to_dict(orient='records')
    return render_template('topology_region1.html', values=isis_links, node_position=node_position)

@blueprint.route('/topology_nested')
@login_required
def topology_nested():
    current_user = session['_user_id']
    node_position = pd.read_sql(db.session.query(Node_position).filter(Node_position.user == current_user).statement,db.session.bind)
    node_position = node_position.to_dict(orient='records')
    try:
        df = pd.read_sql(db.session.query(Links).filter(Links.index >=0).statement,db.session.bind)
        df['node'] = df['source']
        df['source'] = df.apply(lambda row: row['source'][:2],axis=1)
        df['target'] = df.apply(lambda row: row['target'][:2],axis=1)
        df = df[df['source'] != df['target']]
        isis_links = df.to_dict(orient='records')
    except Exception as e:
        isis_links = []
    #print isis_links
    return render_template('topology_nested.html', values=isis_links,node_position=node_position)

@blueprint.route('/topology_nested_aggregated')
@login_required
def topology_nested_aggregated():
    current_user = session['_user_id']
    node_position = pd.read_sql(db.session.query(Node_position).filter(Node_position.user == current_user).statement,db.session.bind)
    node_position = node_position.to_dict(orient='records')
    try:
        df = pd.read_sql(db.session.query(Links).filter(Links.index >=0).statement,db.session.bind)
        df = df[df['source'] != df['target']]
        df['source'] = df.apply(lambda row: row['source'][:2],axis=1)
        df['target'] = df.apply(lambda row: row['target'][:2],axis=1)
        df_aggregate = df.groupby(['source','target']).agg({'util':'sum','capacity':'sum'}).reset_index()
        df_aggregate.loc[:, 'l_ip_r_ip'] = pd.Series([tuple(sorted(each)) for each in list(zip(df_aggregate.source.values.tolist(), df_aggregate.target.values.tolist()))])
        isis_links = df_aggregate.to_dict(orient='records')
    except Exception as e:
        isis_links = []
    #print isis_links
    return render_template('topology_nested_aggregated.html', values=isis_links,node_position=node_position)

@blueprint.route('/topology_errors')
@login_required
def topology_errors():
    current_user = str(session['_user_id'])
    node_position = pd.read_sql(db.session.query(Node_position).filter(Node_position.user == current_user).statement,db.session.bind)
    node_position = node_position.to_dict(orient='records')
    df = pd.read_sql(db.session.query(Links).filter(Links.index >=0).statement,db.session.bind)
    isis_links = df.to_dict(orient='records')
    #print isis_links
    return render_template('topology_errors.html', values=isis_links, node_position=node_position)

@blueprint.route('/topology_latency')
@login_required
def topology_latency():
    current_user = session['_user_id']
    node_position = pd.read_sql(db.session.query(Node_position).filter(Node_position.user == current_user).statement,db.session.bind)
    node_position = node_position.to_dict(orient='records')
    df = pd.read_sql(db.session.query(Links_latency).filter(Links_latency.index >=0).statement,db.session.bind)
    isis_links = df.to_dict(orient='records')
    return render_template('topology_latency.html', values=isis_links, node_position=node_position)

@blueprint.route('/filter_topology',methods=['GET', 'POST'])
@login_required
def filter_topology():
    current_user = session['_user_id']
    node_position = pd.read_sql(db.session.query(Node_position).filter(Node_position.user == current_user).statement,db.session.bind)
    node_position = node_position.to_dict(orient='records')
    source_filter = request.form.get('source_filter')
    target_filter = request.form.get('source_filter')
    df = pd.read_sql(db.session.query(Links).filter(Links.index >=0).statement,db.session.bind)
    isis_links = df.to_dict(orient='records')
    return render_template('filter_topology.html',values=isis_links,
        source_filter = source_filter,
        target_filter = target_filter,
        node_position = node_position)


@blueprint.route('/model_demand', methods=['GET', 'POST'])
@login_required
def model_demand():
    current_user = session['_user_id']
    node_position = pd.read_sql(db.session.query(Node_position).filter(Node_position.user == current_user).statement,db.session.bind)
    node_position = node_position.to_dict(orient='records')
    netflow_demands = get_demand_netflow()
    df = pd.read_sql(db.session.query(Links).filter(Links.index >=0).statement,db.session.bind)
    df['util'] = 0
    df['id'] = df['index']
    isis_links = df.to_dict(orient='records')
    df_router_name = pd.read_sql(db.session.query(Links.source.distinct()).statement,db.session.bind)
    router_name = df_router_name['anon_1'].values.tolist()
    columns = [
            { "field": "state","checkbox":True},
            { "field": "id","title":"id","sortable":False,"class":"hide_me"},
            { "field": "index","title":"index","sortable":False,"class":"hide_me"},
            { "field": "source","title":"source","sortable":True,"editable":True},
            { "field": "target","title":"target","sortable":False,"editable":True},
            { "field": "l_ip","title":"l_ip","sortable":False,"editable":True},
            { "field": "metric","title":"metric","sortable":False,"editable":True},
            { "field": "l_int","title":"l_int","sortable":False},
            { "field": "r_ip","title":"r_ip","sortable":False,"editable":True},
            { "field": "l_ip_r_ip","title":"l_ip_r_ip","sortable":False,"class":"hide_me"},
            { "field": "util","title":"util","sortable":False},
            { "field": "capacity","title":"capacity","sortable":False,"editable":True},
            { "field": "Action","title":"Action","formatter":"TableActions"},
            ]
    columns_demands = [
            { "field": "state","checkbox":True,},
            { "field": "id","title":"id","sortable":False,"class":"hide_me"},
            { "field": "index","title":"index","sortable":False,"class":"hide_me"},
            { "field": "source","title":"source","sortable":True,"editable":True},
            { "field": "target","title":"target","sortable":True,"editable":True},
            { "field": "demand","title":"demand","sortable":False,"editable":True},
            { "field": "Action","title":"Action","formatter":"TableActions_demands"},
            ]
    return render_template('model_demand.html',values=isis_links,columns=columns,router_name=router_name,netflow_demands=netflow_demands,
                           node_position=node_position, columns_demands=columns_demands)

@blueprint.route('/model_edit')
@login_required
def model_edit():
    current_user = session['_user_id']
    node_position = pd.read_sql(db.session.query(Node_position).filter(Node_position.user == current_user).statement,db.session.bind)
    node_position = node_position.to_dict(orient='records')
    netflow_demands = get_demand_netflow()
    isis_links = {}
    df_router_name = pd.read_sql(db.session.query(Links.source.distinct()).statement,db.session.bind)
    router_name = df_router_name['anon_1'].values.tolist()
    columns = [
            { "field": "state","checkbox":True},
            { "field": "id","title":"id","sortable":False,"class":"hide_me"},
            { "field": "index","title":"index","sortable":False,"class":"hide_me"},
            { "field": "source","title":"source","sortable":True,"editable":True},
            { "field": "target","title":"target","sortable":False,"editable":True},
            { "field": "l_ip","title":"l_ip","sortable":False,"editable":True},
            { "field": "metric","title":"metric","sortable":False,"editable":True},
            { "field": "l_int","title":"l_int","sortable":False},
            { "field": "r_ip","title":"r_ip","sortable":False,"editable":True},
            { "field": "l_ip_r_ip","title":"l_ip_r_ip","sortable":False,"class":"hide_me"},
            { "field": "util","title":"util","sortable":False},
            { "field": "capacity","title":"capacity","sortable":False,"editable":True},
	    { "field": "Action","title":"Action","formatter":"TableActions"},
            ]
    columns_demands = [
            { "field": "state","checkbox":True,},
            { "field": "id","title":"id","sortable":False,"class":"hide_me"},
            { "field": "index","title":"index","sortable":False,"class":"hide_me"},
            { "field": "source","title":"source","sortable":True,"editable":True},
            { "field": "target","title":"target","sortable":True,"editable":True},
            { "field": "demand","title":"demand","sortable":False,"editable":True},
            { "field": "Action","title":"Action","formatter":"TableActions_demands"},
            ]
    model_name = Links_Model.query.with_entities(Links_Model.model_name).distinct()
    return render_template('model_edit.html',values=isis_links,columns=columns,router_name=router_name,netflow_demands=netflow_demands,
                           node_position=node_position, model_name=model_name , columns_demands=columns_demands)

@blueprint.route('/traffic_links',methods=['GET', 'POST'])
@login_required
def traffic_links():
#    INFLUXDB_HOST = '127.0.0.1'
#    INFLUXDB_NAME = 'telegraf'
#    client = InfluxDBClient(INFLUXDB_HOST,'8086','','',INFLUXDB_NAME)
    with app.app_context():
        INFLUXDB_HOST     = app.config['INFLUXDB_HOST']
        INFLUXDB_PORT     = app.config['INFLUXDB_PORT']
        INFLUXDB_USERNAME = app.config['INFLUXDB_USERNAME']
        INFLUXDB_PASSWORD = app.config['INFLUXDB_PASSWORD']
        INFLUXDB_NAME     = app.config['INFLUXDB_NAME']

#    client = InfluxDBClient(INFLUXDB_HOST, INFLUXDB_PORT, INFLUXDB_USERNAME, INFLUXDB_PASSWORD, INFLUXDB_NAME)
    client = InfluxDBClient(
                    INFLUXDB_HOST,
                    INFLUXDB_PORT,
                    INFLUXDB_USERNAME,
                    INFLUXDB_PASSWORD,
                    INFLUXDB_NAME
                )


    source_filter = request.form.get('source_cc')
    target_filter = request.form.get('target_cc')
    interval = request.form.get('time_cc')
    if (source_filter ==None) or (target_filter == None) or (interval == None):
        source_filter = "gb%"
        target_filter = "fr%"
        #interval = 480
        interval = 24
    else:
        source_filter = source_filter + "%"
        target_filter = target_filter + "%"

    qry = db.session.query(Links).filter(
            and_(Links.source.like(source_filter) , Links.target.like(target_filter))).statement
    df = pd.read_sql(qry,db.session.bind)
    if not df.empty:
        df['max_util'] = df.apply(lambda row: get_max_util(row['source'],row['l_int'],interval),axis=1)
        isis_links = df.to_dict(orient='records')
        total_capacity=df['capacity'].sum()
    else:
        isis_links = []
    df_countries = pd.read_sql(db.session.query(Routers.country.distinct()).statement,db.session.bind)
    countries = df_countries.to_dict(orient='records')
    #get the last 24h for each link between the countries
    df_variable = []
    if len(isis_links) == 0:
        max_value = 0
        total_capacity = 0
        df_csv = 0
        df_year = 0
    else:
        #create a dict for each link
        df_dict=df.to_dict(orient='records')
        for i in df_dict:
            queryurl = '''SELECT non_negative_derivative(mean(ifHCOutOctets), 1s) *8 from interface_statistics
                            where hostname =~ /%s/ and ifIndex ='%s' AND time >= now()- %sh
                            group by time(5m)''' %(i['source'],i['l_int'],interval)
            result = client.query(queryurl)
            points = list(result.get_points(measurement='interface_statistics'))
            df_max = pd.DataFrame(points)
            if not df_max.empty:
                df_variable.append(df_max)
        #print df_variable
        #merge the values
        df_merged = reduce(lambda  left,right: pd.merge(left,right,on=['time'],how='outer'), df_variable).fillna(0)
        #print df_merged
        #get the sum
        df_merged['bps']=df_merged.drop('time', axis=1).sum(axis=1)
        df_merged = df_merged.sort_values(by=['time'])
        #with the sum pass this to graph
        df_csv=df_merged.to_dict(orient='records')
        #df_csv=df_merged.reindex(columns=["time","bps"]).to_csv(index=False)
        max_value = df_merged['bps'].max()
        max_value = max_value/1000000
        df_year = generate_year_graph(source_filter[:-1],target_filter[:-1])
        df_year = df_year.to_dict(orient='records')
    return render_template('traffic_links.html', values=isis_links,
		countries=countries,max_value=int(max_value),graph=df_csv,
        	total_capacity=total_capacity,s_c=source_filter[:-1],t_c=target_filter[:-1],
		df_year = df_year
		)

@blueprint.route('/topology_time')
@login_required
def topology_time():
    current_user = str(session['_user_id'])
    node_position = pd.read_sql(db.session.query(Node_position).filter(Node_position.user == current_user ).statement,db.session.bind)
    node_position = node_position.to_dict(orient='records')
    df = pd.read_sql(db.session.query(Links).filter(Links.index >=0).statement,db.session.bind)
    isis_links = df.to_dict(orient='records')
    return render_template('topology_time.html', values=isis_links, node_position=node_position)

@blueprint.route('/model_demand_lsp', methods=['GET', 'POST'])
@login_required
def model_demand_lsp():
    current_user = session['_user_id']
    node_position = pd.read_sql(db.session.query(Node_position).filter(Node_position.user == current_user).statement,db.session.bind)
    node_position = node_position.to_dict(orient='records')
    netflow_demands = get_demand_netflow()
    df = pd.read_sql(db.session.query(Links).filter(Links.index >=0).statement,db.session.bind)
    df['util'] = 0
    df['id'] = df['index']
    isis_links = df.to_dict(orient='records')
    df_router_name = pd.read_sql(db.session.query(Links.source.distinct()).statement,db.session.bind)
    router_name = df_router_name['anon_1'].values.tolist()
    columns = [
            { "field": "state","checkbox":True},
            { "field": "id","title":"id","sortable":False,"class":"hide_me"},
            { "field": "index","title":"index","sortable":False,"class":"hide_me"},
            { "field": "source","title":"source","sortable":True,"editable":True},
            { "field": "target","title":"target","sortable":False,"editable":True},
            { "field": "l_ip","title":"l_ip","sortable":False,"editable":True},
            { "field": "metric","title":"metric","sortable":False,"editable":True},
            { "field": "l_int","title":"l_int","sortable":False},
            { "field": "r_ip","title":"r_ip","sortable":False,"editable":True},
            { "field": "l_ip_r_ip","title":"l_ip_r_ip","sortable":False,"class":"hide_me"},
            { "field": "util","title":"util","sortable":False},
            { "field": "capacity","title":"capacity","sortable":False,"editable":True},
            { "field": "Action","title":"Action","formatter":"TableActions"},
            ]
    columns_lsp = [
            { "field": "state","checkbox":True,},
            { "field": "id","title":"id","sortable":False,"class":"hide_me"},
            { "field": "index","title":"index","sortable":False,"class":"hide_me"},
            { "field": "source","title":"source","sortable":True,"editable":True},
            { "field": "target","title":"target","sortable":True,"editable":True},
            { "field": "ero","title":"ero","sortable":False,"editable":True},
            { "field": "metric","title":"metric","sortable":False,"editable":True},
            { "field": "util","title":"util","sortable":False,"editable":True},
            { "field": "Action","title":"Action","formatter":"TableActions_lsp"},
            ]
    columns_demands = [
            { "field": "state","checkbox":True,},
            { "field": "id","title":"id","sortable":False,"class":"hide_me"},
            { "field": "index","title":"index","sortable":False,"class":"hide_me"},
            { "field": "source","title":"source","sortable":True,"editable":True},
            { "field": "target","title":"target","sortable":True,"editable":True},
            { "field": "demand","title":"demand","sortable":False,"editable":True},
            { "field": "Action","title":"Action","formatter":"TableActions_demands"},
            ]
    return render_template('model_demand_lsp.html',values=isis_links,columns=columns,router_name=router_name,netflow_demands=netflow_demands,
                           node_position=node_position, columns_lsp=columns_lsp, columns_demands=columns_demands)

@blueprint.route('/topology_netbox')
@login_required
def topology_netbox():
    app_config_current = App_config.query.all()
    nb_url = app_config_current[0].nb_url
    nb_token = app_config_current[0].nb_token
    current_user = str(session['_user_id'])
    node_position = pd.read_sql(db.session.query(Node_position).filter(
        Node_position.user == current_user).statement, db.session.bind)
    node_position = node_position.to_dict(orient='records')
    df1 = get_netbox_connections(nb_token,nb_url)
    df1['capacity'] = 1000
    df1['util'] = 100
    isis_links = df1.to_dict(orient='records')
    #isis_links = [{'source': 'ke-pe3-nbi', 'target': 'ke-pe2-nbi', 'l_ip': 'ge-0/0/3', 'r_ip': 'ge-0/0/3', 'l_ip_r_ip': "('ge-0/0/3', 'ge-0/0/3')"}, {'source': 'ke-pe3-nbi', 'target': 'ke-pe2-nbi', 'l_ip': 'ge-0/0/0', 'r_ip': 'ge-0/0/1', 'l_ip_r_ip': "('ge-0/0/0', 'ge-0/0/1')"}, {'source': 'ke-pe2-nbi', 'target': 'ke-pe3-nbi', 'l_ip': 'ge-0/0/3', 'r_ip': 'ge-0/0/3', 'l_ip_r_ip': "('ge-0/0/3', 'ge-0/0/3')"}, {'source': 'ke-pe2-nbi', 'target': 'ke-pe3-nbi', 'l_ip': 'ge-0/0/1', 'r_ip': 'ge-0/0/0', 'l_ip_r_ip': "('ge-0/0/0', 'ge-0/0/1')"}]
    return render_template('topology_netbox.html', values=isis_links, node_position=node_position)
