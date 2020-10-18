import pandas as pd
import numpy as np
import random
import plotly.express as px
import cutecharts.charts as ctc
import twitter
from linkedin_api import Linkedin
from wordcloud import WordCloud
from collections import Counter
from textblob import TextBlob
from googletrans import Translator
import seaborn as sn
import matplotlib.pyplot as plt
import altair as alt
import json
import emojis
import regex
import re
import string
import os

#docs folder 
Docs_PATH = 'Path'

#Getting list of bank entities
Banks_names = pd.read_csv(Docs_PATH + 'Lista de bancos MX 2020.csv')
bank_list = Banks_names['LinkedIn'].to_list()

#Collecting credentials
f = open(Docs_PATH + 'credentials.json')
credentials = json.load(f)

#Collecting stopwords
stp = open(Docs_PATH + 'stopwords.json')
stopwords = json.load(stp)
stopwords_list = stopwords['words']

#---------------------------------------------------------------------------------LinkedIn----------------------------------------------------------------------------------------
# Authenticate using any Linkedin account credentials
user = credentials['linkedin']['user']
password = credentials['linkedin']['password']
company = 'banco-santander'


def LikedIn_collect(user,password,company):
      api = Linkedin(user,password)
      aux=api.get_company(company)
      name = aux['name']
      
      #General followers
      followers = aux['followingInfo']['followerCount']
      
      #Hashtags:
      if 'associatedHashtagsResolutionResults' not in aux.keys():
            hashtag_list = 'None hashtags associated'
            hashfollowers_min = np.NaN
            hashfollowers_avg = np.NaN
            hashfollowers_max = np.NaN
      else: 
            hashtag_list = [aux['associatedHashtagsResolutionResults'][v]['feedTopic']['topic']['name'] for v in aux['associatedHashtagsResolutionResults']]
            hashfollowers_min = np.min([aux['associatedHashtagsResolutionResults'][v]['followAction']['followingInfo']['followerCount'] for v in aux['associatedHashtagsResolutionResults']])
            hashfollowers_avg = np.mean([aux['associatedHashtagsResolutionResults'][v]['followAction']['followingInfo']['followerCount'] for v in aux['associatedHashtagsResolutionResults']])
            hashfollowers_max = np.max([aux['associatedHashtagsResolutionResults'][v]['followAction']['followingInfo']['followerCount'] for v in aux['associatedHashtagsResolutionResults']])
      
      #DF
      df = pd.DataFrame({'name':name,
                         'followers':followers,
                         'hashtags':[hashtag_list],
                         'hashfoll_min':hashfollowers_min,
                         'hashfoll_avg':hashfollowers_avg,
                         'hashfoll_max':hashfollowers_max})
      
      return df

def Data_integrator(user,password,bank_list):
      df = pd.DataFrame()
      for v in bank_list:
            linkedin_df = LikedIn_collect(user,password,v)
            df = pd.concat([df,linkedin_df], ignore_index = True)
            print(v)
      
      return df
    
def Get_bank_names(df):
      commercial_names = df['name'].to_list()
      return commercial_names

#---------------------------------------------------------------------------------LinkedIn----------------------------------------------------------------------------------------

#Credentials
consumer_key = credentials['twitter']['consumer_key']
consumer_secret = credentials['twitter']['consumer_secret']
access_token = credentials['twitter']['access_token']
access_token_secret = credentials['twitter']['access_token_secret']



# initialize api instance
twitter_api = twitter.Api(consumer_key=consumer_key,
                        consumer_secret=consumer_secret,
                        access_token_key=access_token,
                        access_token_secret=access_token_secret)

# test authentication
twitter_api.VerifyCredentials()

def Get_tweets(search_keyword,since_date,until_date,count):
      # Get data
      tweets = twitter_api.GetSearch(search_keyword, since = since_date, until = until_date, count = count)

      #DF
      tweet_date = [tweet.created_at for tweet in tweets]
      tweet_content = [tweet.text for tweet in tweets]
      tweet_favorite_count = [tweet.favorite_count for tweet in tweets]
      tweet_retweet_count = [tweet.retweet_count for tweet in tweets]

      df = pd.DataFrame({'date':tweet_date,
                        'tweet':tweet_content,
                        'favorite_count':tweet_favorite_count,
                        'retweets_count':tweet_retweet_count})
      
      df['day_num'] = df['date'].apply(lambda x: x[8:10])
      
      return df

#Collecting tweets
#df = pd.DataFrame()
#for w in commercial_names:
#      print(w)
#      for v in range(9,18):
#            if v < 10:
#                  day_n = '2020-10-0{0}'.format(v)
#                  day_m = '2020-10-0{0}'.format(v + 1)
#            else:
#                  day_n = '2020-10-{0}'.format(v)  
#                  day_m = '2020-10-{0}'.format(v + 1)
                  
#            print(day_n)
#            aux = Get_tweets(search_keyword = w, since_date = day_n,until_date = day_m, count = 100)
#            aux['bank'] = w
#            df = pd.concat([df,aux], ignore_index = True)

#df.to_csv(Docs_PATH + 'Twitter_data_modified_09-17.csv', index=False)
#df = pd.read_csv(Docs_PATH + 'Twitter_data_modified_08-16.csv')
#aux.head()

def Get_hash(text):
      hashs_list = [hash for hash in text.split() if hash.startswith('#')]
      return hashs_list

def Get_emojis_unique(df):
      #Get all possible emojis
      df['emojis'] = df['tweet'].apply(lambda x: emojis.get(x))
      return df

def Get_emojis_list(df):
      emojis_list =[] 

      for _ in range(0, df.shape[0]):
            emojis_list = emojis_list + list(df['emojis'][_])

      emojis_list = list(set(emojis_list))
      return emojis_list

def Get_emojis_all(text, emojis_list):
      #get emojis from each row
      emj_list = []
      data = regex.findall(r'\X',text)
      for v in data:
            if v in emojis_list:
                  emj_list.append(v)
      return emj_list

def Get_unified_hash(df):
      common = ['banco','banca', 'grupo']
      hashtags = ' '.join(df['hashtags'])
      hashtags = hashtags.split()
      clean_hashtags = [v for v in hashtags if v.lower() not in common]
      cleaned_hashtags = ' '.join(clean_hashtags)
      return cleaned_hashtags

def cleaner(df,stopwords_list):
      #Dates
      df['date'] = pd.to_datetime(df['date'], infer_datetime_format=True)
      df['date'] = df['date'].apply(lambda x: x.strftime('%Y-%m-%d'))
      
      #Tweets
      df['tweet'] = df['tweet'].str.lower()
      df['tweet'] = df['tweet'].str.replace('[0-9]','')
      df['tweet'] = df['tweet'].str.replace('\n','')
      df['tweet'] = df['tweet'].str.replace('[%s]' % re.escape(string.punctuation),'')
      df['tweet'] = df['tweet'].str.replace('[‘’“”…]','')
      df['tweet'] = df['tweet'].str.replace(r'\[.*?\]','')
      df['tweet'] = df['tweet'].str.split('https', expand = True)
      df['tweet'].replace('á','a', regex = True, inplace = True)
      df['tweet'].replace('é','e', regex = True, inplace = True)
      df['tweet'].replace('í','i', regex = True, inplace = True)
      df['tweet'].replace('ó','o', regex = True, inplace = True)
      df['tweet'].replace('ú','u', regex = True, inplace = True)
      df['tweet'] = df['tweet'].str.replace(r'[^\w\s]','')
      df['tweet'] = df['tweet'].apply(lambda x: " ".join(x for x in x.split() if x not in stopwords_list))
      
      df['tweet'] = df['tweet'].str.strip()
      df.drop(columns = ['emojis'], inplace = True)
      
      return df


def tweet_traductor(tweet):
      translator = Translator()
      lang = translator.detect(tweet)
      if lang.lang == 'en':
            text_ready = tweet
      else:
            text_ready = translator.translate(tweet)
            text_ready = text_ready.text
      return text_ready

def Get_polarity_subjetivity(df):
      pol = lambda x: TextBlob(x).sentiment.polarity
      sub = lambda x: TextBlob(x).sentiment.subjectivity

      df['polarity'] = df['tweet'].apply(pol)
      df['subjectivity'] = df['tweet'].apply(sub)
      df['polarity'] = df['polarity'].round(2)
      df['subjectivity'] = df['subjectivity'].round(2)
      
      return df

#---------------------------------------------------------------------------------Plotting----------------------------------------------------------------------------------------
def easy_barplot(df,x,y,title):
      
    colors = ['mediumpurple','lightsteelblue','cadetblue','coral','darksalmon','thistle','teal','indianred','dodgerblue']
    
    fig = px.bar(df, y=y, x=x, text=y,
                color_discrete_sequence = [random.choice(colors)])
    
    fig.update_traces(texttemplate='%{text:.2s}',
                        textposition='outside')

    fig.update_layout(title_text = title,
                    uniformtext_minsize=8,
                    title_x = 0.5,
                    uniformtext_mode='hide')
    fig.show()
    
def cute_barplot(df,x,y,label_x,label_y,title):
      chart = ctc.Bar(title,width='800px',height='400px')
      chart.set_options(
      labels=list(df[x]),
      x_label=label_x,
      y_label=label_y
      )
      chart.add_series('Count',list(df[y]))
      
      chart.render_notebook()    

def Plot_emojis_by(df):
      l = df['bank'].unique()
      for i in range(len(l)):
            dummy_df = df[df['bank'] == l[i]]
            total_emojis_list = list([a for b in dummy_df['All_emojis'] for a in b])
            emoji_dict = dict(Counter(total_emojis_list))
            emoji_dict = sorted(emoji_dict.items(), key=lambda x: x[1], reverse=True)
            print('Emoji Distribution for', l[i])
            author_emoji_df = pd.DataFrame(emoji_dict, columns=['emoji', 'count'])
            #Plot
            fig = px.pie(author_emoji_df, values='count', names='emoji')
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(title_text = 'Emojis share',
                    uniformtext_minsize=8,
                    title_x = 0.5)
            fig.show()
            
def Plot_hashtag_wordcloud(cleaned_hashtags,max_words):
      wordcloud = WordCloud(width = 800,
                      height = 400,
                      max_words = max_words,
                      background_color='white').generate(text = cleaned_hashtags)
      
      wordcloud.to_file('wordcloud.png')

      plt.figure(figsize = (15,10))
      plt.imshow(wordcloud)
      plt.axis('off')

      plt.show()
def Plot_alt_barplot(df,x,y):
      brush = alt.selection_interval()
      bars = alt.Chart(df).mark_bar().encode(
            y='{0}:Q'.format(y),
            color=alt.condition(brush, '{0}:N'.format(x), alt.value('lightgray')),
            x='{0}:N'.format(x)).add_selection(brush)
      return bars