from pywebio import *
from pywebio.input import *
from pywebio.output import *

import requests
import json
from datetime import datetime
import plotly.express as px
import pandas as pd

if __name__ == '__main__':
    zipcode = input("PyWebIO Weather Applet 🌞", placeholder="enter your zipcode")
    token = "1ebdf98d274a49a495903913212105"
    
    ### Current Weather ###
    params = dict(key=token, q=zipcode, days=1)
    response = requests.get("http://api.weatherapi.com/v1/forecast.json", params=params)
    
    response_json = response.json()
    city_name = response_json['location']['name']
    country = response_json['location']['country']
    region = response_json['location']['region']
    current_time = response_json['location']['localtime']
    current_temp_c = response_json['current']['temp_c']
    current_temp_f = response_json['current']['temp_f']
    current_day_bool = response_json['current']['is_day']
    current_wind_speed_kph = response_json['current']['wind_kph']
    current_wind_speed_mph = response_json['current']['wind_mph']
    current_precip_in = response_json['current']['precip_in']
    current_precip_mm = response_json['current']['precip_mm']
    
    ### Weather Forecast ###
    
    # hour
    hour_forecast = response_json['forecast']['forecastday'][0]['hour']
    sunrise = response_json['forecast']['forecastday'][0]['astro']['sunrise']
    sunset = response_json['forecast']['forecastday'][0]['astro']['sunset']
    all_hourly_data = []
    for hour in hour_forecast:
        # hourly_data:
        # time, tempC, tempF, CoS, CoR, WSk, WSm in that order
        hourly_data = []
        hourly_data.append(datetime.strptime(hour['time'], '%Y-%m-%d %H:%M').hour)
        hourly_data.append(hour['temp_c'])
        hourly_data.append(hour['temp_f'])
        hourly_data.append(hour['chance_of_snow'])
        hourly_data.append(hour['chance_of_rain'])
        hourly_data.append(hour['wind_kph'])
        hourly_data.append(hour['wind_mph'])
        all_hourly_data.append(hourly_data)
    
    ### FrontEnd Output ###
    # (1) Header
    style(put_text(city_name + ", " + region + " " + zipcode + " 🏠"), 
    'font-size:200%; text-align:center')
    put_html("<hr>")
    style(put_text("Last Updated: " + current_time), "text-align:center; font-size:100%")
    
    # (2) Table
    style(
        put_grid(
            [
                [
                    style(put_image("https://" + response_json['current']['condition']['icon'][2:]),
                        'width: 60%; margin-left: auto; margin-right: auto'),
                    style(put_text(str(int(current_temp_f)) + "F°/" + str(int(current_temp_c)) + "C°"),
                    'font-size:300%; text-align:center; display: flex; align-items: center;')
                ],
                [
                    span(
                        style(
                            put_table([
                                [put_text("🌅 Sunrise/Sunset 🌇"), style(put_text(sunrise + "/" + sunset),
                                'text-align:center;')],
                                [put_text("💨 Wind"), style(put_text(str(int(current_wind_speed_mph)) + "mph/" + str(int(current_wind_speed_kph)) + "kmph"),
                                'text-align:center;')],
                                [put_text("🌧 Precipitation"), style(put_text(str(int(current_precip_in)) + "in/" + str(int(current_precip_mm)) + "mm"),
                                'text-align:center;')]
                            ]),
                            'text-align:center'
                        ),
                        col = 2
                    )
                ]
            ],
            direction = 'row',
            cell_widths='50% 50%'
        )
        , 'margin-left: auto; margin-right: auto; width:75%; margin: 20px 50px 50px 50px; padding: 10px 10px 10px 10px'
    )
    put_html("<hr>")
    
    # (3) Forecast Table
    
    labels = [
                'HR',
                'Temp (C)', 
                'Temp (F)', 
                'Chance of Snow (%)',
                'Chance of Rain (%)',
                'Wind (kmph)',
                'Wind (mph)'
            ]
            
    # style(
    #     put_table(
    #         all_hourly_data, 
    #         header= labels
    #     ),
    #     "border: 1px solid black; color: black; overflow:auto; height:400px; border-radius: 2%; word-break: keep-all"
    # )
    
    ### Graphs
    all_hr_df = pd.DataFrame(all_hourly_data, columns= labels)

    fig_1 = px.line(all_hr_df[["Temp (C)", "Temp (F)"]], 
        title='Temperature',
        labels = {
            "value": "Temperature",
            "index": "Hour",
            "variable": ""
        }
    )
    all_hr_df[["Chance of Snow (%)"]] = all_hr_df[["Chance of Snow (%)"]].astype('int')
    all_hr_df[["Chance of Rain (%)"]] = all_hr_df[["Chance of Rain (%)"]].astype('int')
    fig_2 = px.line(all_hr_df[["Chance of Snow (%)", "Chance of Rain (%)"]], 
        title='Chance of Precipitation',
        labels={
            "value": "Chance of Precipitation (%)",
            "index": "Hour",
            "variable": ""
        }
    )
    fig_3 = px.line(all_hr_df[["Wind (kmph)", "Wind (mph)"]], 
        title='Wind',
        labels = {
            "value": "Wind Speed",
            "index": "Hour",
            "variable": ""
        }
    )
    put_html(fig_1.to_html(include_plotlyjs="require", full_html=False))
    put_html(fig_2.to_html(include_plotlyjs="require", full_html=False))
    put_html(fig_3.to_html(include_plotlyjs="require", full_html=False))

    
    
    
