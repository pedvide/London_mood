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
    res = client.query('weather in London, UK on' + str(day))
    weather = {}
    for pod in res.pods:
        if pod['@title'] == 'Weather history':
            weather_pod = pod['subpod']
            for data in weather_pod:
                weather[data['@title']] = str(data['plaintext'])
            break

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

    weather_parsed = {}
    weather_parsed['temperature'] = temp
    weather_parsed['wind'] = wind
    weather_parsed['clouds'] = clouds
    weather_parsed['rain'] = rain

    return weather_parsed

def _get_cached_weather(day):
    weather = pd.read_csv('cached_weather.csv')
    try:
        d = weather.loc[weather['day'] == str(day)].to_dict(orient='records')[0]
    except (IndexError, KeyError):
        return None
    for key, value in d.items():
        if pd.isnull(value):
            d[key] = None
    del d['day']
    return d


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
    '''Returns 1.0 for a good day, 0.5 for a meh-day and 0.0 for a bad day'''
    start_day = day
    end_day = day
    news_list = _get_news(start_day, end_day)
    overall_pol, overall_sub = _get_sentiment_textBlob(news_list)

    if overall_pol*overall_sub > 0.02:
        return 1.0
    elif overall_pol*overall_sub > 0.015:
        return 0.5
    else:
        return 0.0

def is_weather_good(day):
    '''Returns 1.0 for a good day, 0.5 for a meh-day and 0.0 for a bad day'''
    # if the day is in between 2016/7/23 and 2017/7/23, use the cache
    if day >= date(2016, 7, 23) and day <= date(2017, 7, 23):
        weather = _get_cached_weather(day)
        if weather is None:  # if missing in cache
            print('get new weather data')
            weather = _get_weather(day)
    else:
        print('get new weather data')
        weather = _get_weather(day)

    good_temp = weather['temperature'] > 15 if weather['temperature'] else True
    good_wind = weather['wind'] < 5 if weather['wind'] else True
    good_clouds = weather['clouds'] < 50 if weather['clouds'] else True
    good_rain = weather['rain'] < 50 if weather['rain'] else True

    if good_temp and good_wind and good_clouds and good_rain:
        return 1.0
    elif good_temp and good_wind:
        return 0.5
    else:
        return 0.0
    return good_temp and good_wind and good_clouds and good_rain

def mood(day):
    '''Returns a value [1, 0], with 1 as a good day and 0 as a bad one.'''
    twitter_mood = is_twitter_happy(day)
    news_mood = are_news_positive(day)
    weather_mood = is_weather_good(day)

    average_mood = (2*twitter_mood + news_mood + weather_mood)/4

    return average_mood, twitter_mood, news_mood, weather_mood

def avg_mood_text(mood):
    average_mood = mood[0]
    if average_mood >= 0.74:
        mood_str = 'Good'
    elif average_mood > 0.5:
        mood_str = 'Meh'
    else:
        mood_str = 'Bad'

    return mood_str


###### CREATE TOTAL MOOD CACHE ####
#today = date.today()
#days = list(daterange(today-timedelta(days=365), today))
#moods = []
#for day in days:
#    print(day)
#    moods.append(mood(day))
#df = pd.DataFrame(moods)
#df.columns = ['average', 'twitter', 'news', 'weather']
#df['day'] = days
#df.to_csv('mood_cache.csv')

###### CREATE WEATHER CACHE ####
#today = date.today()
#weather_lst = []
#days = list(daterange(today-timedelta(days=365), today))
#for day in days:
#    print(day)
#    try:
#        new_data = _get_weather(day)
#        weather_lst.append(new_data)
#        print(new_data)
#    except Exception:
#        weather_lst.append(None)
#df = pd.DataFrame(weather_lst)
#df['days'] = days
#df.to_csv('weather_cache.csv')
