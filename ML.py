from simulation import Simulation
from MMModel import *


class MlTrading(Simulation):

    def __init__(self, config, data):

        super(MlTrading, self).__init__(config, data_source=data)

        self.tc = 1  # 设置调仓频率
        self.max_stock_trading = 5

        self.t = 0  # 记录回测运行的天数
        self.if_trade = False  # 当天是否交易
        self.feasible_stocks = []  # 删除建仓日或者重新建仓日停牌的股票后剩余的可选股票

        model = MMModel(name="model_1121b", path='data/TrainPool/')
        self.model = model.load()
        print(self.model.name)
        self.tradeStrategy = None

    def handle_data(self, data):
        # 如果不需要调仓就不对仓中组合作处理，每日直接跳过即可
        if self.if_trade == True:
            g.tradeStrategy.run(self.current_dt)
            # log.info(g.tradeStrategy.stat)
            self.tradeStrategy.trade(self)


        g.if_trade = False


