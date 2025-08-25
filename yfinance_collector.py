import yfinance as yf
import pandas as pd
import datetime
import pytz

### Put everyting into pandas for pre-processing, after import into postgresql db. Use redis for cache whenever retrieving from api.

def collect_news(ticker: str) -> pd.DataFrame:
    desired_timezone = 'US/Eastern'
    news = yf.Search(ticker,news_count=1).news # only returns news for the past day
    filtered_news = list(filter(lambda d: 'relatedTickers' in d, news))

    df = pd.DataFrame(filtered_news)
    df['providerPublishTime'] = df['providerPublishTime'].map(
        lambda ts: datetime.datetime.fromtimestamp(ts, tz=pytz.timezone(desired_timezone))
    )
    df.drop(['uuid', 'type', 'thumbnail'], axis=1, inplace=True)
    
    return df

print(collect_news("PLTR"))



