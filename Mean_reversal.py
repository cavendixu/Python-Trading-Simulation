from simulation import Simulation
from config import Param
from config import Config
from config import Mkt
import numpy as np
import pandas as pd
import datetime


class Mean_reversal(Simulation):

    def __init__(self, parameters, config, data):

        super(Mean_reversal, self).__init__(config, data_source=data)

        self.parameters = parameters
        # 设置移动均线天数
        self.ma_length = parameters.ma_length
        # 设置判断输赢的天数
        self.after_days = parameters.after_days
        # 赢是几个sigma
        self.win_times_sigma = parameters.win_times_sigma
        # 输是几个sigma
        self.lose_times_sigma = parameters.lose_times_sigma
        # 最小数据比例
        self.least_percentage = parameters.least_percentage
        # 计量输赢时取区间宽度
        self.band_width = parameters.band_width
        # 交易时止盈线
        self.profit_times_sigma = parameters.profit_times_sigma
        # 交易时止损线
        self.loss_times_sigma = parameters.loss_times_sigma

        # 设置全局变量
        self.first_run = True  # 第一次跑
        # 股票的卖出判定
        self.sell_conditions = {}
        # 记录输赢统计
        self.stock_stats = {}
        # 记录最佳买入区间
        self.stock_best_ranges = {}
        # 记录当前日期


    def initiate_statistics(self):
        # 如果是第一次跑
        if self.first_run:
            # 初始化输赢统计
            global stock_stats
            stock_stats = {}
            for contracts in self.contracts:
                # 上个日期
                previous_date = self.line_count
                # 获取历史收盘价数据
                prices = self.get_price(contracts, previous_date)
                # 得到偏离倍数和输赢结果的记录
                my_data = self.collect_data(prices, self.ma_length)
                # 对上面取得的数据进行数量统计
                statistics = self.compute_statistics(my_data)
                # 将统计结果做成DF
                my_df = pd.DataFrame(statistics, index=['value', 'win', 'even', 'lose'], columns=statistics.keys())
                # 转置
                stock_stats[contracts] = my_df.T
            # 更新到全局变量
            self.stock_stats = stock_stats
            # 不再是第一次跑了
            self.first_run = False

    def get_price(self, contracts, previous_date):
        till_now_data = self.data[contracts][0:previous_date]
        return till_now_data

    def collect_data(self, prices, i):
        # 初始化记录
        my_data = []
        # 当i的位加后置天数没有超过数据长度
        while i + self.after_days < len(prices):
            # 取过去ma长度天数的数据
            range_data = prices[i - self.ma_length: i]
            # 算均线
            ma = np.mean(range_data)
            # 算标准差
            sigma = np.std(range_data)
            # 算偏差倍数*10，乘十是因为整数更方便操作
            difference_times_sigma = int((((prices[i] - ma) / sigma) // 0.1))
            # 如果-10< 偏离倍数 <= -1，因为小于-10的也太异常了，因此也不要
            if -100 < difference_times_sigma <= -10:
                # 计算输赢结果
                result = self.win_or_lose(prices.iloc[i], prices[i + 1: i + self.after_days + 1], sigma)
                # 将偏离倍数和输赢结果记录下来
                my_data.append((difference_times_sigma, result))
            # i++
            i += 1
        return my_data

    @staticmethod
    def compute_statistics(my_data):
        # 创建字典进行统计
        statistics = {}
        # 数据还没空的时候
        for pair in my_data:
            # 输赢是怎么样的呀
            result = pair[1]
            # 偏离倍数呢
            value = pair[0]
            # 如果这个偏离倍数还没出现过
            if value not in statistics:
                # 那就记下来！
                statistics[value] = {'lose': 0, 'even': 0, 'win': 0}
            # 输赢结果的统计加一
            statistics[value][result] += 1
        return statistics

    def win_or_lose(self, price, my_list, sigma):
        # 设上限
        upper_bound = price + self.win_times_sigma * sigma
        # 设下限
        lower_bound = price - self.lose_times_sigma * sigma
        # 未来几天里
        for future_price in my_list:
            # 碰到上线了
            if future_price >= upper_bound:
                # 赢
                return 'win'
            # 碰到下线了
            if future_price <= lower_bound:
                # 输
                return 'lose'
        # 要不就是平
        return 'even'

    def handle_data(self):
        # 更新输赢统计
        self.update_statistics()
        # 判断最好的买入区间
        best_ranges = self.get_best_ranges()
        # 产生买入信号
        to_buy = self.buy_signals(best_ranges)
        # 产生卖出信号
        to_sell = self.sell_signals()
        # 卖出股票
        self.sell_stocks(to_sell, to_buy)
        # 买入股票
        self.buy_stocks(to_buy)

    # 更新输赢统计
    # 无输出
    # 更新全局变量的偏离倍数和输赢统计DF
    def update_statistics(self):
        for contracts in self.contracts:
            # 取价格
            prices = self.attribute_history(contracts, 1 + self.ma_length + self.after_days)
            # 算sigma的日子
            past_prices = prices[0:self.ma_length]
            # 对应的当天
            current_price = prices[self.ma_length:self.ma_length+1]
            # print(type(prices))
            # print(type(current_price))
            # 算输赢的日子
            future_prices = prices[self.ma_length + 1:]
            # 算ma
            ma = np.mean(past_prices)
            # 算sigma
            sigma = np.std(past_prices)
            # 计算和ma差几个sigma
            difference_times_sigma = int((current_price - ma) / sigma // 0.1)
            # 上线
            upper_bound = current_price + self.win_times_sigma * sigma
            # 下限
            lower_bound = current_price - self.lose_times_sigma * sigma
            # 判断过后几天的输赢
            result = self.win_or_lose(int(current_price), future_prices, sigma)
            # 把DF转成dict进行操作
            my_dict = stock_stats[contracts].T.to_dict()
            # 在合理区间里的话
            if -100 < difference_times_sigma <= -10:
                # 如果dict里有这个倍数了
                if difference_times_sigma in my_dict:
                    # 直接更新输赢
                    my_dict[difference_times_sigma][result] += 1
                    # 如果没有
                else:
                    # 加进去
                    my_dict[difference_times_sigma] = {'value': difference_times_sigma, 'win': 0, 'even': 0,
                                                       'lose': 0}
                    # 更新输赢
                    my_dict[difference_times_sigma][result] = 1
            # 更新全局变量
            stock_stats[contracts] = pd.DataFrame(my_dict, index=['win', 'even', 'lose'], columns=my_dict.keys()).T

    def attribute_history(self, contracts, window):
        window_data = self.data[contracts][(self.line_count - window):self.line_count]
        return window_data

    # 判断最佳区间
    # 无输出
    # 返回一dict,key为股票，值为最佳买入区域DF
    def get_best_ranges(self):
        global stock_best_ranges
        stock_best_ranges = {}
        for contracts in stock_stats:
            statistics = stock_stats[contracts]
            # 获取偏离倍数
            values = statistics.index
            # 输数
            loses = statistics['lose']
            # 赢数
            wins = statistics['win']
            # 平数
            evens = statistics['even']
            # 总数
            num_data = sum(wins) + sum(loses) + sum(evens)
            mydata = []
            # 在所有位置不会溢出的位置
            for n in range(min(values), max(values) - (self.band_width - 1)):
                # 取在n和（n+宽度）之间的DF行
                stat_in_range = statistics[(values >= n) & (values <= n + self.band_width - 1)]
                # 赢除输（这里输+1，因为可能输=0）
                ratio = float(sum(stat_in_range['win'])) / float((sum(stat_in_range['lose']) + 1))
                # 这区间数据总量
                range_data = float(sum(stat_in_range['win']) + sum(stat_in_range['lose']) + sum(stat_in_range['even']))
                # 如果数据量超过预设的临界值
                if range_data / num_data >= self.least_percentage:
                    # 记录区间的输赢比
                    mydata.append({'low': n, 'high': n + self.band_width, 'ratio': ratio})
            # 区间统计转换成DF
            data_table = pd.DataFrame(mydata)
            # 按输赢比排序
            sorted_table = data_table.sort_values('ratio', ascending=False)
            # 取第一行
            stock_best_range = sorted_table.iloc[0]
            stock_best_ranges[contracts] = stock_best_range
        # 输出结果
        return stock_best_ranges

    # --代码块11.
    # 获取买入信号
    # 输出一list该买入的股票
    def buy_signals(self, best_ranges):
        to_buy = []
        for contracts in self.contracts:
            stock_best_range = best_ranges[contracts]
            # 看现价
            current_price = self.attribute_history(contracts, 1)
            # 取倍数区间低点
            low = float(stock_best_range['low'])
            # 取倍数区间高点
            high = float(stock_best_range['high'])
            # 取赢率
            ratio = float(stock_best_range['ratio'])
            # 获取历史收盘价
            h = self.attribute_history(contracts, self.ma_length)
            # 计算均线
            ma = np.mean(h)
            # 计算标准差
            sigma = np.std(h)
            # 算现价的偏离倍数
            times_sigma = float((current_price - ma) / sigma)
            # 如果在该买的区间里
            # print(type(times_sigma))
            if low <= 10 * times_sigma and 10 * times_sigma <= high:
                # 加入买入列表
                to_buy.append(contracts)
        return to_buy

    # 获取卖出信号
    # 输出一list该卖出的股票
    def sell_signals(self):
        to_sell = []
        # 对于仓内所有股票
        # print(self.position)
        for contracts in self.position:
            if self.position[contracts]['Number'] != 0:
                # 取现价
                current_price = self.get_price(contracts, self.line_count+1)[self.line_count]
                # print(current_price)
                # 查卖出条件
                # print(self.sell_conditions)
                try:
                    conditions = self.sell_conditions[contracts]
                    # print(conditions)
                    # 看看是不是该卖了
                    # print(current_price)
                    if float(current_price) >= float(conditions['high']) or current_price <= conditions['low']:
                        # print('Here')
                        # 加入卖出信号，确保没有重复
                        to_sell.append(contracts)
                    # 如果不需要卖
                    else:
                        # 日数减1
                        self.sell_conditions[contracts]['days'] -= 1
                except:
                    pass
            # print(to_sell)
        return to_sell

    def sell_stocks(self, to_sell, to_buy):
        for contracts in to_sell:
            # print(contracts + '---------sell---------')
            # 如果也在买入名单里
            if contracts in to_buy:
                # 从卖出信号中删掉
                pass
            # 不该买的话
            else:
                # 全卖掉

                self.send_order(contracts, Mkt.sell, self.position[contracts]['Number'], self.lastprice[contracts])  # price ???
                # 如果没有卖干净呢
                if contracts in self.position:
                    # 把天数清零
                    self.sell_conditions[contracts]['days'] = 0

    def buy_stocks(self, to_buy):
        # 有多少钱
        cash_per_stock = self.notional
        for contracts in to_buy:
            self.send_order(contracts, Mkt.buy, int(self.notional / len(to_buy) / self.lastprice[contracts]), self.lastprice[contracts])
        # if len(self.position) == 0:
            # 对于所有买单里的股票
            # print(contracts+'---------buy---------')
            if contracts in self.position:
                # 看现价
                current_price = self.attribute_history(contracts, 1)
                # 获取历史收盘价
                h = self.attribute_history(contracts, self.ma_length)
                ma = np.mean(h)
                # 计算标准差
                sigma = np.std(h)
                # 止损线
                low = current_price - self.loss_times_sigma * sigma
                # 止盈线
                high = current_price + self.profit_times_sigma * sigma
                # 在全局变量中记录卖出条件
                self.sell_conditions[contracts] = {'high': high, 'low': low, 'days': self.after_days - 1}

    def on_bar(self):

        if self.line_count > 300:
            self.initiate_statistics()
            self.handle_data()





if __name__ == '__main__':

    parameters = Param(
        ma_length=30,
        after_days=30,
        win_times_sigma=1,
        lose_times_sigma=1,
        least_percentage=0.05,
        band_width=4,
        profit_times_sigma=1,
        loss_times_sigma=1
    )

    config = Config(
        code=['600000.SH', '600010.SH'],
        startdate="20150101",
        enddate='20180101',
        notional=2000000,
        commission=0.0003,
        multipler=1
    )

    data = pd.read_csv('testData.csv')

    a = Mean_reversal(parameters, config, data)
    a.run()
    # a.initiate_statistics()
    # a.update_statistics()
    # a.handle_data()
    # print(a.attribute_history('601998.SH',8))