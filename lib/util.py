import pandas as pd
import numpy as np
# from pkindicators import *

# /media/mu6mula/Data/Crypto-Data-Feed/freq-user-data/data
base_data_folder = './data'

def load_json_candles(fname):
    data = pd.read_json(fname)
    data.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
    data.set_index('timestamp', inplace=True)
    return data

# def load_candles(exchange,base,quote,timeframe):
#     fname = f'{base_data_folder}/{exchange}/{base}_{quote}-{timeframe}.json'
#     return load_json_candles(fname)
