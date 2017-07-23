# -*- coding: utf-8 -*-
"""
Created on Fri Jul 21 15:13:59 2017

@author: villanueva
"""

import requests
import requests_cache
requests_cache.install_cache()

from datetime import date, datetime, timedelta
import pandas as pd

import wolframalpha

from textblob import TextBlob

import re

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)

def _get_twitter_mood(continent, city, start_day, end_day, granularity='day'):

    twitter_url_base = 'http://wefeel.csiro.au/api/emotions/primary/timepoints'

    epoch_start = round((datetime.fromordinal(start_day.toordinal()) -
                         datetime.utcfromtimestamp(0)).total_seconds()*1000)
    epoch_end = round((datetime.fromordinal(end_day.toordinal()) -
                       datetime.utcfromtimestamp(0)).total_seconds()*1000)

    parameters = {'granularity': granularity,
                  'continent': continent, 'timezone': city,
                  'start': epoch_start, 'end': epoch_end}

    mood_response = requests.get(twitter_url_base, params=parameters)

    if(mood_response.ok):
        json_data = mood_response.json()
        mood = pd.DataFrame.from_dict(json_data)
        mood['time'] = pd.to_datetime(mood['start'], utc=True)
        mood = pd.concat([mood.drop(['counts', 'localStart', 'start'], axis=1),
                          mood['counts'].apply(pd.Series)], axis=1).drop(['*'], axis=1)

        mood = mood.set_index('time')
        return mood.div(mood.sum(axis=1), axis=0)

    else:
        mood_response.raise_for_status()
        return

    # plot mood as a function of time
#    mood.plot()
    ##day = datetime(year=2017, month=5, day=22)
    ##day = datetime(year=2017, month=6, day=3)
#    start_day = date.today() - timedelta(days=365)
#    end_day = date.today() - timedelta(days=1)
    #
    #mood = get_twitter_mood(continent, city, start_day, end_day)
    #
    #mood['sadness'].nlargest()
    ##time
    ##2017-05-23    0.238388 manchester attack
    ##2016-11-09    0.184787 Trump wins election
    ##2017-01-28    0.179557 Trump's travel ban?
    ##2016-12-27    0.169789 end of christmas??
    ##2017-07-20    0.168618 ?
    #
    #mood['joy'].nsmallest()
    ##time
    ##2016-11-09    0.435758 Trump wins election
    ##2017-05-23    0.435932 manchester attack
    ##2016-12-27    0.479624 end of christmas??
    ##2017-04-22    0.480509
    ##2017-01-22    0.486061



def _get_weather(day):

    client = wolframalpha.Client('P7JGX8-GWXE5T2LHR')
    res = client.query('weather in London, UK on' + '2017-5-10')
    weather = {}
    for pod in res.pods:
        if pod['@title'] == 'Weather history':
            weather_pod = pod['subpod']
            for data in weather_pod:
                weather[data['@title']] = str(data['plaintext'])
            break

    weather_parsed = {}

    temp_match = re.search(r'average: (\d*) °C', weather.get('Temperature', ''))
    if temp_match:
        temp = int(temp_match.group(1))
    else:
        temp = None
    wind_match = re.search(r'average: (\d*) m/s', weather.get('Wind speed', ''))
    if wind_match:
        wind = int(wind_match.group(1))
    else:
        wind = None
    clouds_match = re.search(r'clear: (\d*\.?\d*)%', weather.get('Cloud cover', ''))
    if clouds_match:
        clouds = 100-float(clouds_match.group(1))
    else:
        clouds = None
    rain_match = re.search(r'rain: (\d*\.?\d*)%', weather.get('Conditions', ''))
    if rain_match:
        rain = float(rain_match.group(1))
    else:
        rain = None

    weather_parsed['temperature'] = temp
    weather_parsed['wind'] = wind
    weather_parsed['clouds'] = clouds
    weather_parsed['rain'] = rain

    return weather


def _get_news(start_day, end_day):
    guardian_url_base = 'http://content.guardianapis.com/search'

    api_key = 'e7f918dc-b450-4bf9-a1d5-d18c9f8e7949'

    parameters = {'api-key': api_key,
                  'from-date': start_day, 'to-date': end_day,
                  'q': 'london', 'section': None, 'type': None,
                  'show-fields': 'body'}

    news_response = requests.get(guardian_url_base, params=parameters)

    if(news_response.ok):
        json_data = news_response.json()['response']
        pages = json_data['pages']
        news_list = json_data['results']
        for page in range(2, pages+1):
            news_response = requests.get(guardian_url_base, params=parameters)
            next_json_data = news_response.json()['response']
            news_list.extend(next_json_data['results'])

        news_content = [{'title': news['webTitle'], 'body': news['fields']['body']}
                        for news in news_list]

        clean_html = re.compile('<.*?>')
        for news in news_content:
            news['body'] = re.sub(clean_html, '', news['body'])

    else:
        news_response.raise_for_status()

    return news_content


def _get_sentiment_textBlob(news_list):
    overall_pol = overall_sub = 0
    for news in news_list:
        text = TextBlob(news['body'])
        sentiment = text.sentiment
        news['sentiment'] = sentiment
        overall_pol += sentiment.polarity
        overall_sub += sentiment.subjectivity

    overall_pol /= len(news_list)
    overall_sub /= len(news_list)

    return overall_pol, overall_sub


def is_twitter_happy(day):
    '''Returns 1.0 for a good day, 0.5 for a meh-day and 0.0 for a bad day'''
    continent = 'europe'
    city = 'london'

    start_day = day
    end_day = day

    mood = _get_twitter_mood(continent, city, start_day, end_day)
    mood['good'] = (mood['joy'] + mood['love']) > 0.57
    mood['bad'] = (mood['anger'] + mood['fear'] + mood['sadness']) > 0.25

    return (int(mood['good']) - int(mood['bad']))/2 + 0.5

def are_news_positive(day):
    '''Returns a number [-1, 1]'''
    start_day = day
    end_day = day
    news_list = _get_news(start_day, end_day)
    overall_pol, overall_sub = _get_sentiment_textBlob(news_list)

    return overall_pol*overall_sub > 0.02

def is_weather_good(day):

    weather = _get_weather(day)

    good_temp = weather['temperature'] > 15
    good_wind = weather['wind'] < 10
    good_clouds = weather['clouds'] < 20
    good_rain = weather['rain'] < 20

    return good_temp and good_wind and good_clouds and good_rain

#day = date(year=2017, month=5, day=25)
today = date.today()
#twitter_lst = []
#news_lst = []
weather_lst = []
days = list(daterange(today-timedelta(days=365), today))
for day in days:
    print(day)
#    try:
#        twitter_lst.append(is_twitter_happy(day))
#    except Exception:
#        twitter_lst.append(None)
#    try:
#        news_lst.append(are_news_positive(day))
#    except Exception:
#        news_lst.append(None)
    try:
        weather_lst.append(_get_weather(day))
    except Exception:
        weather_lst.append(None)
