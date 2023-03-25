# import libraries

import pandas as pd
import numpy as np
import os
import sys

from datetime import datetime
from datetime import timedelta

import plotly
import plotly.graph_objs as go

import warnings
warnings.filterwarnings("ignore")

import time
start_time = time.time()

# connecting to database

from arctic import Arctic, CHUNK_STORE
conn = Arctic('localhost')
conn.initialize_library('entsoe', lib_type=CHUNK_STORE)
# conn.list_libraries()
lib_entsoe = conn['entsoe']

# function to change timezone from UTC to local time

def changing_timezone(x):
    ts = x.index.tz_localize('utc').tz_convert('Europe/Brussels')
    y = x.set_index(ts)
    return y.tz_localize(None)

# enter country

print('Welcome to the Stack Model Tool.')
print('You need to enter some inputs below.')
country = input("1. Enter the perimeter as shown here --> DE/FR/BE/PL/IT : ")

# enter date range
ref_start_date = input("2. Enter start date (dd/mm/yyyy): ")
ref_end_date = input("3. Enter end date (dd/mm/yyyy): ")

start_date = datetime.strptime(ref_start_date, '%d/%m/%Y') + timedelta(days = - 1)
end_date = datetime.strptime(ref_end_date, '%d/%m/%Y') + timedelta(days = 1)

# Read Spot price
var = 'DayAheadPrices_12.1.D'
prefix = var + '_' + country 

DA_price = lib_entsoe.read(prefix, chunk_range=pd.date_range(start_date, end_date))

if country == 'DE':
    interco = ['AT','BE','CZ','DK','FR','LU','NL','PL', 'SE','CH']
elif country == 'FR':
    interco = ['BE','DE','IT','ES','CH','GB']
elif country == 'BE':
    interco = ['FR','DE','LU','NL','GB']
elif country == 'ES':
    interco = ['FR','PT']
elif country == 'IT':
    interco = ['AT','GR','FR','MT','ME','SI','CH']
elif country == 'NL':
    interco = ['BE','DK','DE','NO','GB']
elif country == 'PL':
    interco = ['CZ','DE','LT','SK','SE', #'UA'
               ]
elif country == 'GB':
    interco = ['BE','FR','IE','NL']

df_interco = pd.DataFrame(columns=[])
for i in interco:
    prefix = var + '_' + i 
    try:
        spot_n = lib_entsoe.read(prefix, chunk_range=pd.date_range(start_date, end_date))
        df_interco = pd.merge(df_interco,spot_n,how='outer',right_index=True, left_index=True)
    except Exception:
        pass
df_DA_price = pd.merge(DA_price, df_interco,how='outer',right_index=True, left_index=True)

# Read demand data
read =  'ActualTotalLoad_6.1.A'
prefix = read + '_' + country 

demand = lib_entsoe.read(prefix, chunk_range=pd.date_range(start_date, end_date))

# Read power generation data
read = 'AggregatedGenerationPerType_16.1.B_C'
prefix = read + '_' + country 

gen = lib_entsoe.read(prefix, chunk_range=pd.date_range(start_date, end_date))

# Read cross border flows
read = 'PhysicalFlows_12.1.G'

# exports
df_exports = pd.DataFrame(columns=[])
for i in interco:
    prefix = read + '_' + country + '_' + i 
    try:
        out_flows = lib_entsoe.read(prefix, chunk_range=pd.date_range(start_date, end_date))
        df_exports = pd.merge(df_exports,out_flows ,how='outer',right_index=True, left_index=True)    
    except Exception:
        pass

# imports
df_imports = pd.DataFrame(columns=[])
for j in interco:
    prefix = read + '_' + j + '_' + country
    try:
        in_flows = lib_entsoe.read(prefix, chunk_range=pd.date_range(start_date, end_date))
        df_imports = pd.merge(df_imports,in_flows ,how='outer',right_index=True, left_index=True) 
    except Exception:
        pass
    
df_flows = df_imports.subtract(df_exports.values)

# add net imports column
df_flows['Net_Imports'] = df_flows.sum(axis =1, skipna= True)

# merging data to a single dataframe
var = [df_DA_price,demand,gen,df_flows]     
df_merge = pd.DataFrame(columns=[])

for df in var:
    df_merge = pd.merge(df_merge, df,how='outer',right_index=True, left_index=True)

df_merge = changing_timezone(df_merge)

# convert 15 min data to hourly data
df_merge = df_merge.resample('H').mean()

#keeping only the data for the selected input date
df_data = df_merge.loc[(df_merge.index>=datetime.strptime(ref_start_date, '%d/%m/%Y'))&(df_merge.index<end_date)]

# calculate res% & residual load
var = 'ActualGenerationOutput'
try:
    df_data['RES_generation'] =(df_data[var + ' ' + country + ' ' + 'Solar'] + df_data[var + ' ' + country+ ' ' + 'Wind Onshore'] + df_data[var + ' ' + country + ' ' + 'Wind Offshore'])
except KeyError:
    df_data['RES_generation'] =(df_data[var + ' ' + country + ' ' + 'Solar'] + df_data[var + ' ' + country+ ' ' + 'Wind Onshore'])
                            
df_data['RES_penetration'] = (df_data['RES_generation']/df_data['ActualTotalLoad'+'_'+country])*100
df_data['Residual_load'] = df_data['ActualTotalLoad'+'_'+country] - df_data['RES_generation']
    
def create_plot(
    title = None,
    df = None,
    countries_code = None,
    list_flows = None,
    list_DA_prices = None,
    gen_types = None,
    avcap_gen_types = None,
    gen_code = None,
    perimeter = None
    ):
    
    from plotly.subplots import make_subplots
    
    #-----------------------------------------------------------------------------
    fig = plotly.subplots.make_subplots(
        rows=3, cols=1, 
        subplot_titles = (
            'Spot Price',
            'Generation',
            'CrossBorder Flows: (+): Imports, (-): Exports',
        ),
        shared_xaxes=True,
        vertical_spacing=0.10,
        specs=[[{"secondary_y": False}], [{"secondary_y": True}], [{"secondary_y": False}]]
    )
    #-----------------------------------------------------------------------------
    # Spot prices
    
    var = 'DayAheadPrices'
    trace = go.Scatter(
            x = df.index, 
            y = df[var+'_'+perimeter], 
            name = perimeter,
            line_color = countries_code[perimeter]
            )
    fig.append_trace(trace, 1, 1)

    
    for col in list_DA_prices:
        trace = go.Scatter(
            x = df.index, 
            y = df[var+'_'+col], 
            name = col,
            line_color = countries_code[col],
            visible = 'legendonly',
            )
        
        fig.add_trace(trace, 1, 1)
    
    #-----------------------------------------------------------------------------
    
    # Generation
    var = 'ActualGenerationOutput'
    for col_gen_type, label in zip(gen_types, gen_code):
        try:
            trace = go.Bar(
                x = df.index, 
                y = df[var + ' ' + perimeter + ' ' + col_gen_type], 
                name = gen_code[col_gen_type]["name"],
                marker_color = gen_code[col_gen_type]["colour"],
                hovertemplate='%{x},%{y:.1f}'
                )
            fig.append_trace(trace, 2, 1)
        except KeyError:
            pass
    
    # CrossBorder Trade
    
    trace = go.Bar(
                x = df.index, 
                y = df['Net_Imports'], 
                name = 'CrossBorder Trade',
                marker_color = 'orchid',
                hovertemplate='%{x},%{y:.1f}'
                )
    fig.add_trace(trace, 2, 1)
        
    # Demand
    
    trace = go.Scatter(
        x = df.index, 
        y = df['ActualTotalLoad'+'_'+perimeter], 
        name = 'Demand',
        visible = 'legendonly',
        line = dict(color='black', width=4),
         hovertemplate='%{x},%{y:.1f}'
    )
    fig.add_trace(trace, 2, 1
                 )

    # RES penetration
    
    trace = go.Scatter(
        x = df.index, 
        y = df['RES_penetration'], 
        name = 'RES_penetration',
        visible = 'legendonly',
        line = dict(color='royalblue', width=4,dash='dash'),
         hovertemplate='%{x},%{y:.1f}'
    )
    fig.add_trace(trace, 2, 1, 
                  secondary_y=True
                 )
    
    # Residual load
    
    trace = go.Scatter(
        x = df.index, 
        y = df['Residual_load'], 
        name = 'Residual_load',
        visible = 'legendonly',
        line = dict(color='maroon', width=3,dash='dot'),
        hovertemplate='%{x},%{y:.1f}'
    )
    fig.add_trace(trace, 2, 1)
    
    #-----------------------------------------------------------------------------
    # flows each country
    
    var = 'CrossBorderPhysicalFlow'
    for col in list_flows:
        trace = go.Bar(
            x = df.index, 
            y = df[var+'_'+col+'_'+perimeter], 
            name = col,
            marker_color = countries_code[col],
             hovertemplate='%{x},%{y:.1f}'
            #showlegend=False,
            )
        fig.append_trace(trace, 3, 1)
      
    #-----------------------------------------------------------------------------
    # Add figure title

    fig.update_layout(
        title_text = title,
        barmode='relative',
        bargap=0,
        plot_bgcolor="#FFF",
        
        xaxis=dict(
            autorange=True,
            linecolor = "#BCCCDC",
            showgrid=True
        ),
                
        yaxis1 = dict(
            anchor = "x",
            autorange = True,
            title_text = "€/MWh",
            linecolor = "#BCCCDC",
            showgrid=True
            
        ),
        
        yaxis2 = dict(
            anchor = "x",
            #range = [0,80000],
            autorange = True,
            title_text = "MWh/h",
            linecolor = "#BCCCDC"
        ),
        
        yaxis3 = dict(
            anchor = "x",
            autorange = True,
            #range=[0,100],
            title_text = "RES_pen (%)",
            side = 'right',
            linecolor = "#BCCCDC"
        ),
        
        yaxis4 = dict(
            anchor = "x",
            autorange = True,
            #range=[-10000,10000],
            title_text = "MWh/h",
            linecolor = "#BCCCDC"
        ),
    )
    
    return fig

countries_dict = {
  "DE": "indianred",
  "FR": "royalblue",
  "BE": "rosybrown",
  "ES": "tomato",
  "IT": "green",
  "NL": "orange",
  "GB": "navy",
  "AT": "coral",
  "CZ": "firebrick",
  "CH": "lawngreen",
  "DK": "teal",
  "LU": "orchid",
  "PL": "silver",
  "PT": "darkgreen",
  "IE": "pink",
  "GR": "azure",
  "NO": "orangered",
  "SE": "thistle",
  "SK": "crimson",
  "LT": "purple",
  "MT": "olive",
  "SI": "salmon",
  "ME": "gold",

}

gen_tech_dict = { 
    "Nuclear" : {
        'name' : 'Nuclear',
        'colour' : 'indianred'
    },
    "Biomass" : {
        'name' : 'Biomass',
        'colour' : 'darkgreen'
    },
     "Fossil Hard coal" : {
        'name' : 'Hard Coal',
        'colour' : 'brown'
    },
     "Fossil Brown coal/Lignite" : {
        'name' : 'Lignite',
        'colour' : 'saddlebrown'
    },
     "Fossil Gas" : {
        'name' : 'CCGT',
        'colour' : 'silver'
    },
     "Hydro Run-of-river and poundage" : {
        'name' : 'Hydro R-o-R',
        'colour' : 'blue'
    },
     "Hydro Pumped Storage" : {
        'name' : 'Pumped Storage',
        'colour' : 'orange'
    },
     "Hydro Water Reservoir" : {
        'name' : 'Hydro Reservoir',
        'colour' : 'plum'
    },
     "Solar" : {
        'name' : 'Solar',
        'colour' : 'gold'
    },
     "Wind Offshore" : {
        'name' : 'Wind Offshore',
        'colour' : 'green'
    },
     "Wind Onshore" : {
        'name' : 'Wind Onshore',
        'colour' : 'steelblue'
    },
    
}
    
fig = create_plot(
    
    title = country + ' Electricity Generation',
    #+ ref_date.strftime("%B") + '/' + str(year),
    
    df = df_data,
    
    countries_code = countries_dict,
    
    #list_interco = interco,
    
    #list_colors = ['deepskyblue', 'red', 'orange', 'green','silver','maroon'],
    
    list_flows = list(df_flows.drop(['Net_Imports'], axis=1).columns.str[24:26]),
    
    list_DA_prices = list(df_DA_price.columns.str[-2:].drop(country)),
    
    gen_types = [

         'Nuclear',
         'Biomass',
         'Hydro Run-of-river and poundage',
         'Hydro Water Reservoir',
        
         'Fossil Hard coal',
         'Fossil Gas',
         'Fossil Brown coal/Lignite',
         'Hydro Pumped Storage',
        
         'Wind Offshore',
         'Wind Onshore',
         'Solar'
                      
    ],

    avcap_gen_types = [
         'Nuclear',
         'Natural_Gas',
         'Thermal_Coal',
         'Lignite',
         'Coal'
    ],
    
    gen_code = gen_tech_dict,
    
    perimeter = country,
)

outfile = country + '_' + 'Stack' + '.html'

plotly.offline.plot(fig, filename = os.path.join(os.getcwd() + '/plots', outfile))