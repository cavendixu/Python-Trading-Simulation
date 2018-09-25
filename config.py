import collections




MarketData = collections.namedtuple(
    'MarketData',
    [
        'date',
        'buy',
        'sell'
    ]
)

Mkt = MarketData(
    date='trade_date',
    buy='Buy',
    sell='Sell'
)




Config = collections.namedtuple(
    'Config',
    [
        'code',
        'startdate',
        'enddate',
        'notional',
        'commission',
        'multipler'
    ]
)

Param = collections.namedtuple(
    'Param',
    [
        'ma_length',
        'after_days',
        'win_times_sigma',
        'lose_times_sigma',
        'least_percentage',
        'band_width',
        'profit_times_sigma',
        'loss_times_sigma'
    ]
)
