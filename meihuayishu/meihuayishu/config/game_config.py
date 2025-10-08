"""游戏配置类 - 支持不同彩票玩法的模块化设计"""

class GameConfig:
    """游戏配置类 - 支持不同彩票玩法的模块化设计"""
    
    def __init__(self, game_type="keno8"):
        self.game_type = game_type
        
        # 快乐8配置
        if game_type == "keno8":
            self.total_numbers = 80  # 总号码数
            self.drawn_numbers = 20  # 每期开出号码数
            self.selected_numbers = 10  # 用户选择号码数
            self.prediction_count = 10  # 用户预测号码数（改为10个）
            self.num_node_features = 15  # 节点特征数量
            
            # 快乐8蒙特卡洛配置
            self.monte_carlo_cfg = {
                'n_draws': 10000,        # 模拟次数
                'draw_size': 20,         # 抽取号码数量
                'pick_size': 10,         # 最终选择号码数量
                'check_wuxing': False,   # 是否检查五行平衡
                'check_odd_even': True,  # 是否检查奇偶平衡
                'parallel': True,        # 是否并行处理
                'n_jobs': None           # 并行作业数，None表示自动
            }
            
            # 快乐8回测配置
            self.backtest_cfg = {
                'window_train': 300,     # 训练窗口大小
                'window_step': 5,        # 窗口滑动步长
                'save_results': True     # 是否保存结果
            }
        
        # 双色球配置
        elif game_type == "ssq":
            self.total_numbers = 33  # 红球号码数
            self.drawn_numbers = 6   # 红球开出数
            self.selected_numbers = 6  # 用户选择红球数
            self.prediction_count = 6
            self.num_node_features = 24  # 增加到24个特征，包含位置编码等特征
            
            # 双色球蒙特卡洛配置
            self.monte_carlo_cfg = {
                'n_draws': 10000,        # 模拟次数
                'draw_size': 6,          # 抽取号码数量
                'pick_size': 6,          # 最终选择号码数量
                'check_wuxing': False,   # 是否检查五行平衡
                'check_odd_even': True,  # 是否检查奇偶平衡
                'parallel': True,        # 是否并行处理
                'n_jobs': None           # 并行作业数，None表示自动
            }
            
            # 双色球回测配置
            self.backtest_cfg = {
                'window_train': 200,     # 训练窗口大小
                'window_step': 3,        # 窗口滑动步长
                'save_results': True     # 是否保存结果
            }
        
        # 大乐透配置
        elif game_type == "dlt":
            self.total_numbers = 35  # 前区号码数
            self.drawn_numbers = 5   # 前区开出数
            self.selected_numbers = 5  # 用户选择前区号码数
            self.prediction_count = 5
            self.num_node_features = 15  # 节点特征数量
            
            # 大乐透蒙特卡洛配置
            self.monte_carlo_cfg = {
                'n_draws': 10000,        # 模拟次数
                'draw_size': 5,          # 抽取号码数量
                'pick_size': 5,          # 最终选择号码数量
                'check_wuxing': False,   # 是否检查五行平衡
                'check_odd_even': True,  # 是否检查奇偶平衡
                'parallel': True,        # 是否并行处理
                'n_jobs': None           # 并行作业数，None表示自动
            }
            
            # 大乐透回测配置
            self.backtest_cfg = {
                'window_train': 200,     # 训练窗口大小
                'window_step': 3,        # 窗口滑动步长
                'save_results': True     # 是否保存结果
            }
        
        # 通用参数
        self.historical_weeks = 7    # 历史统计期数
        self.prediction_input_weeks = 3  # 预测输入期数
        
        # 双色球特有参数
        if game_type == "ssq":
            self.historical_weeks = 12  # 双色球历史统计期数减少到12期
        
    def get_config(self):
        """获取配置字典"""
        return {
            'game_type': self.game_type,
            'total_numbers': self.total_numbers,
            'drawn_numbers': self.drawn_numbers,
            'selected_numbers': self.selected_numbers,
            'prediction_count': self.prediction_count,
            'historical_weeks': self.historical_weeks,
            'prediction_input_weeks': self.prediction_input_weeks,
            'num_node_features': self.num_node_features,
            'monte_carlo_cfg': self.monte_carlo_cfg if hasattr(self, 'monte_carlo_cfg') else None,
            'backtest_cfg': self.backtest_cfg if hasattr(self, 'backtest_cfg') else None
        }
    
    def get_monte_carlo_config(self):
        """获取蒙特卡洛配置"""
        return self.monte_carlo_cfg if hasattr(self, 'monte_carlo_cfg') else {}
    
    def get_backtest_config(self):
        """获取回测配置"""
        return self.backtest_cfg if hasattr(self, 'backtest_cfg') else {} 