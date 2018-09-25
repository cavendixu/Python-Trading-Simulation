import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
from config import Mkt
from config import Config

class Simulation(object):

    def __init__(self, config, data_source):

        self.config = config
        self.data = data_source
        self.startdate = config.startdate
        self.enddate = config.enddate
        self.contracts = config.code

        self.position = {}
        for contract in self.contracts:
            self.position[contract] = {'Number': 0, 'AverPrice': 0}

        self.lastprice = {}
        for contract in self.contracts:
            self.lastprice[contract] = None

        self.commission = config.commission
        self.multipler = config.multipler
        self.notional = config.notional
        self.primary_notional = config.notional
        self.realized_PnL = 0
        self.last_PnL = 0
        self.PnL = 0

        self.date = None
        self.tradelog = pd.DataFrame(columns=['date', 'code',  'direction', 'volume', 'price'])
        self.daily_return = pd.DataFrame(columns=['date', 'dailyreturn'])
        self.PnL_list = pd.DataFrame(columns=['date', 'PnL'])
        self.line_count = 0

    def on_bar(self):

        pass

    def send_order(self, contract, direction, volume, price):

        if direction == Mkt.buy:

            if self.notional < volume * price * (self.multipler + self.commission):
                print('资金不足，无法下单')
                return
            else:
                self.position[contract]['AverPrice'] = (self.position[contract]['AverPrice'] * self.position[contract]['Number'] + (price * (1 + self.commission)) * volume) / (self.position[contract]['Number'] + volume)
                self.position[contract]['Number'] += volume
                self.notional -= volume * price * (self.multipler + self.commission)

        elif direction == Mkt.sell:

            if self.position[contract]['Number'] < volume:
                print('头寸不足，无法下单')
                return
            else:
                self.position[contract]['Number'] -= volume
                self.realized_PnL += (price - self.position[contract]['AverPrice'] - price * self.commission) * volume
                self.notional += volume * price * (self.multipler - self.commission)

            if self.position[contract]['Number'] == 0:
                self.position[contract]['AverPrice'] = 0

        temp = pd.Series({
            'date': self.date,
            'code': contract,
            'direction': direction,
            'volume': volume,
            'price': price
                          })
        self.tradelog = self.tradelog.append(temp, ignore_index=True)

    def update_PnL(self):

        self.last_PnL = self.PnL
        self.PnL = 0
        for contract in self.contracts:
            if self.lastprice[contract]:
                self.PnL += (self.lastprice[contract] - self.position[contract]['AverPrice'] - self.commission) * self.position[contract]['Number']

        self.PnL += self.realized_PnL

        try:

            temp = pd.Series({
                'date': self.date,
                'dailyreturn': self.PnL - self.last_PnL
            })

        except:

            temp = pd.Series({
                'date': self.date,
                'dailyreturn': 0
            })

        self.daily_return = self.daily_return.append(temp, ignore_index=True)

        temp = pd.Series({
            'date': self.date,
            'PnL': self.PnL
        })

        self.PnL_list = self.PnL_list.append(temp, ignore_index=True)

    def datasort(self, data, startdate, enddate):

        data.sort_values(by=[Mkt.date], axis=0, ascending=True, inplace=True)
        data.index = range(len(data))
        dt = []
        for i in range(len(data)):

            if isinstance(data[Mkt.date][i], (str,int,np.int64)):

                try:
                    dt.append(datetime.datetime(int(data[Mkt.date][i])//10000, int(data[Mkt.date][i])//100%100, int(data[Mkt.date][i])%100, 0, 0, 0))
                except:
                    try:
                        dt.append(datetime.datetime.strptime(data[Mkt.date][i], "%Y/%m/%d"))
                    except:
                        raise RuntimeError('日期格式不正确！')

            elif isinstance(data[Mkt.date][i], datetime.datetime):

                dt.append(data[Mkt.date][i])

            else:

                raise RuntimeError('日期格式无法识别！')

        data[Mkt.date] = dt

        startdate = datetime.datetime(int(startdate)//10000, int(startdate)//100 % 100, int(startdate)%100, 0, 0, 0)
        enddate = datetime.datetime(int(enddate) // 10000, int(enddate) // 100 % 100, int(enddate) % 100, 0, 0, 0)

        adjust_data = data[(data[Mkt.date] >= startdate) & (data[Mkt.date] <= enddate)]

        try:
            full_list = [Mkt.date]
            full_list.extend(self.contracts)
            adjust_data = adjust_data[full_list]
        except:
            raise RuntimeError('合约不存在！')

        effective_contracts = []
        droped_contracts = []
        for contract in self.contracts:

            temp = adjust_data[np.isnan(adjust_data[contract])]

            if len(temp) > 0:

                droped_contracts.append(contract)

            else:

                effective_contracts.append(contract)

        self.contracts = effective_contracts.copy()
        effective_contracts.insert(0, Mkt.date)
        adjust_data = adjust_data[effective_contracts]

        if len(droped_contracts) > 0:

            for name in droped_contracts:

                print(name, end='  ')

            print('由于停牌被舍弃！')

        return adjust_data

    def pre_handle(self):
        pass

    def print(self):
        PnL_ratio = self.PnL / self.primary_notional
        maxloss = 0
        for i in range(len(self.PnL_list)):
            temp = max(self.PnL_list['PnL'][0:i+1])
            if self.PnL_list['PnL'][i] - temp < maxloss:
                maxloss = self.PnL_list['PnL'][i] - temp

        output = pd.DataFrame(columns=['结果'], index=['绝对收益', '收益率', '收益率（年化）', '交易次数', '最大回撤', '夏普比率（年化）'])
        output['结果']['绝对收益'] = np.round(self.PnL, 2)
        output['结果']['收益率'] = '{:.2%}'.format(PnL_ratio)
        output['结果']['收益率（年化）'] = '{:.2%}'.format(PnL_ratio / len(self.PnL_list) * 250)
        output['结果']['交易次数'] = len(self.tradelog)
        output['结果']['最大回撤'] = np.round(maxloss, 2)
        output['结果']['夏普比率（年化）'] = np.round(PnL_ratio / len(self.PnL_list) * 250 / (np.std([(self.PnL_list['PnL'][i+1] - self.PnL_list['PnL'][i]) / (self.PnL_list['PnL'][i] + self.primary_notional) for i in range(len(self.PnL_list)-1)]) * np.sqrt(250)), 2)
        output.to_csv('~/Desktop\\simulation\\demo\\output.csv', encoding='utf_8_sig')

    def run(self):

        self.data = self.datasort(self.data, self.startdate, self.enddate)

        self.pre_handle()

        for line in range(len(self.data)):

            for contract in self.contracts:
                self.lastprice[contract] = self.data[contract][line]
            self.date = self.data[Mkt.date][line]
            self.line_count = line

            if line < len(self.data) - 1:

                self.on_bar()
                self.update_PnL()

            else:

                for contract in self.contracts:
                    if self.position[contract]['Number'] > 0:
                        self.send_order(contract, 'Sell', self.position[contract]['Number'], self.lastprice[contract])

                self.update_PnL()

if __name__ == '__main__':

    config = Config(
        code=['600000.SH', '600010.SH', '600958.SH'],
        startdate="20150101",
        enddate='20160101',
        notional=20000,
        commission=0.0003,
        multipler=1
    )
    data = pd.read_csv('~/Desktop\\simulation\\demo\\testData.csv')

    a = Simulation(config, data_source=data)
    a.run()
    a.print()

    # print(list(data['600000.SH']))
