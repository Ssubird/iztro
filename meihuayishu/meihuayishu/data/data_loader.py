"""数据加载器 - 负责加载和预处理彩票历史数据"""

import os
import random
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path

from meihuayishu.downloaders import DoubleColorBallLoader
from meihuayishu.downloaders import Kuaile8Loader as ExternalKuaile8Loader

class Kuaile8Loader:
    """快乐8数据加载器简单实现（仅用于模拟数据）"""
    def __init__(self, config=None):
        self.config = config or {}
        
    def load(self, force_update=False):
        """加载数据（简单实现）"""
        print("使用模拟数据...")
        # 生成模拟数据
        data = []
        for i in range(200):
            # 安全生成日期
            month = (i // 28) % 12 + 1  # 确保月份在1-12之间
            day = (i % 28) + 1  # 确保日在1-28之间（所有月份都有效）
            draw_date = pd.Timestamp(f"2024-{month:02d}-{day:02d}")
            
            numbers = sorted(random.sample(range(1, 81), 20))
            data.append({
                'draw_date': draw_date,
                'draw_no': f'sim_{i+1}',
                'numbers': [numbers]
            })
        return pd.DataFrame(data)

PACKAGE_ROOT = Path(__file__).resolve().parents[2]


class RealDataLoader:
    """真实数据加载器 - 使用downloaders模块加载真实彩票数据"""
    
    def __init__(self, config):
        self.config = config
        self.loader = None
        
        # 根据游戏类型创建对应的数据加载器（使用外部下载器）
        output_dir = PACKAGE_ROOT / "data" / "raw"
        if config.game_type == "keno8":
            self.loader = ExternalKuaile8Loader({
                'url': 'https://data.17500.cn/kl8_asc.txt',
                'output_path': str(output_dir)
            })
            print("✅ 已初始化快乐8真实数据下载器")
        elif config.game_type == "ssq":
            self.loader = DoubleColorBallLoader({
                'url': 'https://data.17500.cn/ssq_asc.txt',
                'output_path': str(output_dir)
            })
            print("✅ 已初始化双色球真实数据下载器")
        else:
            raise ValueError(f"游戏类型 {config.game_type} 暂不支持真实数据下载")
    
    def load_historical_data(self, force_update=False, max_periods=None):
        """
        加载真实历史数据
        
        Args:
            force_update: 是否强制更新数据
            max_periods: 最大期数限制
            
        Returns:
            list: 标准化的历史数据
        """
        logging.info("正在加载真实历史数据...")
        print(f"📥 正在从网络下载真实彩票数据{'(强制更新)' if force_update else ''}...")
        
        try:
            # 使用数据下载器加载数据
            df = self.loader.load(force_update=force_update)
            
            if df.empty:
                logging.error("未能加载到真实数据，将使用模拟数据")
                print("❌ 数据下载失败，使用模拟数据代替")
                return self._generate_fallback_data(max_periods or 200)
            
            # 转换为标准格式
            historical_data = self._convert_to_standard_format(df, max_periods)
            
            logging.info(f"成功加载 {len(historical_data)} 期真实历史数据")
            print(f"✅ 成功加载 {len(historical_data)} 期真实历史数据")
            return historical_data
            
        except Exception as e:
            logging.error(f"加载真实数据失败: {str(e)}")
            logging.info("使用模拟数据作为后备方案")
            print(f"❌ 加载数据失败: {str(e)}")
            print("🔄 使用模拟数据作为后备方案")
            return self._generate_fallback_data(max_periods or 200)
    
    def _convert_to_standard_format(self, df, max_periods=None):
        """
        将pandas DataFrame转换为标准格式
        
        Args:
            df: 原始数据DataFrame
            max_periods: 最大期数
            
        Returns:
            list: 标准化的历史数据
        """
        historical_data = []
        
        # 按日期排序，取最新的数据
        df = df.sort_values('draw_date', ascending=False)
        
        if max_periods:
            df = df.head(max_periods)
        
        # 反转，使最老的数据在前面
        df = df.iloc[::-1].reset_index(drop=True)
        
        for idx, row in df.iterrows():
            try:
                if self.config.game_type == "keno8":
                    # 解析快乐8号码
                    if isinstance(row['numbers'], str):
                        # 如果numbers是字符串，需要解析
                        numbers = eval(row['numbers'])
                    else:
                        numbers = row['numbers']
                    
                    # 快乐8数据格式：numbers 是包含一个列表的列表 [[1,2,3...]] 或直接是列表 [1,2,3...]
                    if isinstance(numbers, list):
                        if len(numbers) > 0 and isinstance(numbers[0], list):
                            # 取第一个子列表
                            actual_numbers = numbers[0]
                        else:
                            actual_numbers = numbers
                    else:
                        logging.warning(f"期号 {row.get('draw_no', 'unknown')} 数据格式异常")
                        continue
                elif self.config.game_type == "ssq":
                    # 解析双色球号码 (只考虑红球)
                    actual_numbers = row['red_numbers']
                    # 这里还可以额外存储蓝球号码
                    blue_number = row.get('blue_number')
                else:
                    logging.warning(f"未知游戏类型: {self.config.game_type}")
                    continue
                
                # 确保号码数量正确
                if len(actual_numbers) != self.config.drawn_numbers:
                    logging.warning(f"期号 {row.get('draw_no', 'unknown')} 号码数量不匹配: {len(actual_numbers)} != {self.config.drawn_numbers}")
                    # 如果号码过多，取前N个；如果过少，跳过
                    if len(actual_numbers) > self.config.drawn_numbers:
                        actual_numbers = actual_numbers[:self.config.drawn_numbers]
                    else:
                        continue
                
                data_entry = {
                    'period': row.get('draw_no', f'period_{idx+1}'),
                    'numbers': sorted(actual_numbers),
                    'timestamp': row['draw_date'].strftime('%Y-%m-%d') if pd.notna(row['draw_date']) else '2024-01-01',
                    'source': 'real_data'
                }
                
                # 对于双色球，额外存储蓝球号码
                if self.config.game_type == "ssq" and 'blue_number' in row:
                    data_entry['blue_number'] = row['blue_number']
                
                historical_data.append(data_entry)
                
            except Exception as e:
                logging.warning(f"处理数据行 {idx} 时出错: {str(e)}")
                continue
        
        return historical_data
    
    def _generate_fallback_data(self, num_periods):
        """生成后备模拟数据"""
        logging.info(f"生成 {num_periods} 期模拟数据作为后备")
        
        historical_data = []
        for i in range(num_periods):
            # 安全生成日期
            month = (i // 28) % 12 + 1  # 确保月份在1-12之间
            day = (i % 28) + 1  # 确保日在1-28之间（所有月份都有效）
            
            draw = sorted(random.sample(
                range(1, self.config.total_numbers + 1), 
                self.config.drawn_numbers
            ))
            
            data_entry = {
                'period': f'sim_{i+1}',
                'numbers': draw,
                'timestamp': f"2024-{month:02d}-{day:02d}",
                'source': 'simulation'
            }
            
            # 对双色球额外生成蓝球
            if self.config.game_type == "ssq":
                data_entry['blue_number'] = random.randint(1, 16)
            
            historical_data.append(data_entry)
        
        return historical_data

class DataGenerator:
    """数据生成器 - 兼容真实数据和模拟数据"""
    
    def __init__(self, config):
        self.config = config
        self.real_loader = RealDataLoader(config)
        
    def generate_single_draw(self):
        """生成单期开奖号码（模拟用）"""
        return sorted(random.sample(
            range(1, self.config.total_numbers + 1), 
            self.config.drawn_numbers
        ))
    
    def load_historical_data(self, use_real_data=True, num_periods=200, force_update=False):
        """
        加载历史数据
        
        Args:
            use_real_data: 是否使用真实数据
            num_periods: 期数限制
            force_update: 是否强制更新
            
        Returns:
            list: 历史数据
        """
        if use_real_data:
            return self.real_loader.load_historical_data(
                force_update=force_update, 
                max_periods=num_periods
            )
        else:
            return self.generate_historical_data(num_periods)
    
    def generate_historical_data(self, num_periods=200):
        """生成模拟历史开奖数据"""
        historical_draws = []
        for i in range(num_periods):
            # 安全生成日期
            month = (i // 28) % 12 + 1  # 确保月份在1-12之间
            day = (i % 28) + 1  # 确保日在1-28之间（所有月份都有效）
            
            draw = self.generate_single_draw()
            historical_draws.append({
                'period': i + 1,
                'numbers': draw,
                'timestamp': f"2024-{month:02d}-{day:02d}",
                'source': 'simulation'
            })
        return historical_draws 

# ================== 兼容脚本的统一 DataLoader ==================
class DataLoader:
    """统一的数据加载器接口 - 兼容旧脚本调用 (load_historical_data, load_latest_data, prepare_prediction_data)"""
    
    def __init__(self, config, use_real_data=False):
        self.config = config
        self.use_real_data = use_real_data
        self.generator = DataGenerator(config)
        
        # 预加载历史数据（可选）
        self._historical_df = None
    
    # ------------------------------------------------------------
    # 历史数据
    # ------------------------------------------------------------
    def load_historical_data(self, force_update=False):
        """加载历史数据 (DataFrame 格式)"""
        historical_list = self.generator.load_historical_data(
            use_real_data=self.use_real_data,
            num_periods=500,
            force_update=force_update
        )
        df = pd.DataFrame(historical_list)
        self._historical_df = df
        return df
    
    # ------------------------------------------------------------
    # 最新数据
    # ------------------------------------------------------------
    def load_latest_data(self, force_update=False):
        """加载最新一期数据 (DataFrame)"""
        if self._historical_df is None or force_update:
            self.load_historical_data(force_update=force_update)
        
        if self._historical_df.empty:
            raise ValueError("历史数据为空，无法获取最新数据")
        
        latest_row = self._historical_df.iloc[[-1]].copy()
        return latest_row
    
    # ------------------------------------------------------------
    # 预测输入准备
    # ------------------------------------------------------------
    def prepare_prediction_data(self, latest_df):
        """根据最新数据准备模型输入
        
        这里采用简化实现：直接返回pandas DataFrame
        若需要图结构或Tensor，可在此处扩展
        """
        return latest_df 