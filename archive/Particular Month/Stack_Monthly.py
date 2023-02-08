

# In[1]:

import pandas as pd
import numpy as np
import os
import sys
import plotly
import plotly.graph_objs as go
    

# In[2]:


from arctic import Arctic, CHUNK_STORE

conn = Arctic('10.213.120.5')
conn.initialize_library('entsoe', lib_type=CHUNK_STORE)
conn.list_libraries()
lib = conn['entsoe']


# In[3]:


def last_day_of_month(date_value):
    return date_value.replace(day = monthrange(date_value.year, date_value.month)[1])


# In[4]:


# function to change timezone from UTC to local time

def changing_timezone(x):
    ts = x.index.tz_localize('utc').tz_convert('Europe/Brussels')
    y = x.set_index(ts)
    return y.tz_localize(None)


# In[5]:


# Input country

country = input("Enter the perimeter (DE/FR/BE/ES/IT/PL) : ")



# Input a month

from datetime import datetime
from datetime import timedelta
from calendar import monthrange

# Input month and year
    
month = int(input("Enter a Month Number (1 to 12): "))
year = int(input("Enter a Year (2015 onwards): "))
    
ref_date = datetime(year=year, month=month, day=1).date()

start_date = ref_date + timedelta(days = - 1)
end_date = last_day_of_month(ref_date) + timedelta(days = 1)



# Read Spot price

read = 'DayAheadPrices'
prefix = read + '_' + country 

DA_price = lib.read(prefix, chunk_range=pd.date_range(start_date, end_date))


# In[8]:


if country == 'DE':
    interco = ['FR','CH','PL'] # NL to be added
elif country == 'FR':
    interco = ['DE','BE','CH','IT','ES'] # UK to be added
elif country == 'BE':
    interco = ['FR'] # NL and UK to be added
elif country == 'ES':
    interco = ['FR']
elif country == 'IT':
    interco = ['FR','CH','AT']
elif country == 'PL':
    interco = ['DE'] # to add CZ? 


# In[9]:


df_interco = pd.DataFrame(columns=[])
for i in interco:
    prefix = read + '_' + i 
    spot = lib.read(prefix, chunk_range=pd.date_range(start_date, end_date))
    df_interco = pd.merge(df_interco,spot ,how='outer',right_index=True, left_index=True)

df_DA_price = pd.merge(DA_price, df_interco,how='outer',right_index=True, left_index=True)



# Read demand data

read = 'ActualTotalLoad'
prefix = read + '_' + country 

demand = lib.read(prefix, chunk_range=pd.date_range(start_date, end_date))

# convert 15 min data to hourly data
demand = demand.resample('H').mean()



# Read power generation data

read = 'AggregatedGenerationPerType'
prefix = read + '_' + country 

gen = lib.read(prefix, chunk_range=pd.date_range(start_date, end_date))

# convert 15 min data to hourly data
gen = gen.resample('H').mean()



# Read cross border flows

read = 'ScheduledCommercialExchanges'

# exports
df_exports = pd.DataFrame(columns=[])
for i in interco:
    prefix = read + '_' + country + '_' + i 
    out_flows = lib.read(prefix, chunk_range=pd.date_range(start_date, end_date))
    df_exports = pd.merge(df_exports,out_flows ,how='outer',right_index=True, left_index=True)    
    
# imports
df_imports = pd.DataFrame(columns=[])
for j in interco:
    prefix = read + '_' + j + '_' + country
    in_flows = lib.read(prefix, chunk_range=pd.date_range(start_date, end_date))
    df_imports = pd.merge(df_imports,in_flows ,how='outer',right_index=True, left_index=True) 

df_flows = df_exports.subtract(df_imports.values)



# changing timezones 

df_DA_price = changing_timezone(df_DA_price)
demand = changing_timezone(demand)
gen = changing_timezone(gen)
df_flows =changing_timezone(df_flows)


# merging data to a single dataframe

var = [df_DA_price,demand,gen,df_flows]     
df_merge = pd.DataFrame(columns=[])

for df in var:
    df_merge = pd.merge(df_merge, df,how='outer',right_index=True, left_index=True)


# keeping only the data for the selected input date

df_data = df_merge.loc[(df_merge.index.month==month)&(df_merge.index.year==year)]


# In[29]:


def create_plot(
    title = None,
    df = None,
    country_code = country,
    list_interco = None,
    list_colors = None,
    list_flows = None,
    list_DA_prices = None,
    list_gen_types = None,
    list_gen_types_labels = None,
    ):
    
    from plotly.subplots import make_subplots
    
    #-----------------------------------------------------------------------------
    fig = plotly.subplots.make_subplots(
        rows=3, cols=1, 
        subplot_titles = (
            'Spot Price',
            'Generation and Demand',
            'Cross Border Flows DA: (+): Exports, (-): Imports',
        ),
        shared_xaxes=True,
        vertical_spacing=0.05,
        #specs=[[{"secondary_y": True}], [{"secondary_y": False}], [{"secondary_y": False}]]
    )
    #-----------------------------------------------------------------------------
    # Spot price
    
    for col, color in zip(list_DA_prices, list_colors):
        trace = go.Scatter(
            x = df.index, 
            y = df[col], 
            name = col,
            line_color = color,
            )
        fig.append_trace(trace, 1, 1)
    
    
    #-----------------------------------------------------------------------------
    
    # Generation
    
    for col_gen_type, label in zip(list_gen_types, list_gen_types_labels):
        try:
            trace = go.Bar(
                x = df.index, 
                y = df[col_gen_type], 
                name = label,
                    #marker_color = color,
                    #legendgroup = country,
                    #showlegend=False,
                )
            fig.append_trace(trace, 2, 1)
        except KeyError:
            pass
            
    # Demand
    
    trace = go.Scatter(
        x = df.index, 
        y = df['ActualTotalLoad'+'_'+country_code], 
        name = 'Demand',
        #visible = 'legendonly',
        line_color = 'black',
    )
    fig.add_trace(trace, 2, 1, 
                  #secondary_y=True
                 )
    fig.update_layout(yaxis_title='MW')

    #-----------------------------------------------------------------------------
    # flows
    
    for flow, country, color in zip(list_flows, list_interco, list_colors[1:]):
        trace = go.Bar(
            x = df.index, 
            y = df[flow], 
            name = 'Flows '+ country,
            marker_color = color,
            legendgroup = country,
            )
        fig.append_trace(trace, 3, 1)
    fig.update_layout(yaxis_title='MW')
  
    #-----------------------------------------------------------------------------
    fig.update_layout(
        title_text = title,
        barmode='relative',
        bargap=0,
        #bargroupgap=0,
       xaxis3_rangeslider_visible=True, xaxis3_rangeslider_thickness=0.05 ,
        
        xaxis=dict(
            autorange=True,
            #rangeslider=dict(
                #autorange=True,
            #),
            #type="date",
            #title='Date and Time'
        ),
        
        # xaxis2_rangeslider_visible=True,
        
        yaxis1 = dict(
            anchor = "x",
            autorange = True,
            title_text = "€/MWh"
            
        ),
        
        yaxis2 = dict(
            anchor = "x",
            autorange = True,
            title_text = "MWh/h",
        ),
        
        yaxis3 = dict(
            anchor = "x",
            autorange = True,
            title_text = "MWh/h",
        ),
    )
    
    return fig


# In[30]:


gen_tech = [
        'Nuclear',
        'Biomass',
        'Hydro R-o-R',
        'Hard coal',
        'Lignite',
        'CCGT',
        'Pumped Storage',
        'Hydro Reservoir',
        'Wind Offshore',
        'Wind Onshore',
        'Solar',
                ]

fig = create_plot(
    
    title = country + ' Electricity Generation - ' + ref_date.strftime("%B") + '/' + str(year),
    
    df = df_data,
    
    country_code = country,
    
    list_interco = interco,
    
    list_colors = ['deepskyblue', 'red', 'orange', 'green','silver','maroon'],
    
    list_flows = list(df_flows.columns.values),
    
    list_DA_prices = list(df_DA_price.columns.values),
    

     list_gen_types = [

        'ActualGenerationOutput' + ' ' + country + ' ' + 'Nuclear',
        'ActualGenerationOutput' + ' ' + country + ' ' + 'Biomass',
        'ActualGenerationOutput' + ' ' + country + ' ' + 'Hydro Run-of-river and poundage',

        'ActualGenerationOutput' + ' ' + country + ' ' + 'Fossil Hard coal',
        'ActualGenerationOutput' + ' ' + country + ' ' + 'Fossil Brown coal/Lignite',
        'ActualGenerationOutput' + ' ' + country + ' ' + 'Fossil Gas',
         
        'ActualGenerationOutput' + ' ' + country + ' ' + 'Hydro Pumped Storage',
        'ActualGenerationOutput' + ' ' + country + ' ' + 'Hydro Water Reservoir',
         
        'ActualGenerationOutput' + ' ' + country + ' ' + 'Wind Offshore',
        'ActualGenerationOutput' + ' ' + country + ' ' + 'Wind Onshore',
        'ActualGenerationOutput' + ' ' + country + ' ' + 'Solar',

                        ],
    
    list_gen_types_labels = gen_tech

)
outdir = 'plots/'
outfile = country + '_' + 'Stack' + '_' + ref_date.strftime("%B") + '_' + str(ref_date.year) + '.html'

plotly.offline.plot(fig, filename = os.path.join(outdir, outfile))





