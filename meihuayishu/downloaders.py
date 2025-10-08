"""
彩票数据下载器模块 - 支持多种彩票数据的自动下载和更新

功能：
1. 支持快乐8、双色球等多种彩票数据下载
2. 自动解析和标准化数据格式
3. 支持增量更新和全量更新
4. 提供命令行接口
"""

import os
import sys
import time
import logging
import requests
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from pathlib import Path
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data" / "raw"

class BaseDataLoader:
    """彩票数据下载器基类"""
    
    def __init__(self, config=None):
        self.config = config or {}
        output_dir = self.config.get('output_path', DEFAULT_DATA_DIR)
        self.data_dir = Path(output_dir)
        self.url = self.config.get('url', '')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # 创建数据目录
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def download(self, url=None, force_update=False):
        """下载数据
        
        Args:
            url: 数据源URL，如果为None则使用默认URL
            force_update: 是否强制更新数据
            
        Returns:
            str: 下载的数据文件路径
        """
        url = url or self.url
        if not url:
            raise ValueError("未指定数据源URL")
        
        # 构建本地文件路径
        filename = self._get_filename_from_url(url)
        filepath = self.data_dir / filename
        
        # 检查是否需要更新
        if os.path.exists(filepath) and not force_update:
            file_age = time.time() - os.path.getmtime(filepath)
            # 如果文件存在且不超过24小时，直接返回
            if file_age < 86400:  # 24小时 = 86400秒
                logging.info(f"使用本地缓存数据: {filepath} (更新于 {file_age/3600:.1f} 小时前)")
                return filepath
        
        # 下载数据
        logging.info(f"正在从 {url} 下载数据...")
        try:
            disable_proxy = os.environ.get("MEIHUA_DISABLE_PROXY", "").lower() in {"1", "true", "yes"}
            if disable_proxy:
                logging.info("已忽略系统代理设置，直接发起请求")
                with requests.Session() as session:
                    session.trust_env = False
                    response = session.get(url, headers=self.headers, timeout=30)
            else:
                response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()  # 检查请求是否成功
            
            # 保存数据
            with open(filepath, 'wb') as f:
                f.write(response.content)

            logging.info(f"数据已下载并保存至: {filepath}")
            return filepath
        except Exception as e:
            logging.error(f"下载数据失败: {str(e)}")
            # 如果本地有缓存，使用缓存
            if os.path.exists(filepath):
                logging.info(f"使用本地缓存数据: {filepath}")
                return filepath
            raise
    
    def _get_filename_from_url(self, url):
        """从URL中提取文件名"""
        # 默认使用URL的最后一部分作为文件名
        filename = url.split('/')[-1]
        if not filename:
            # 如果无法从URL提取文件名，使用时间戳
            filename = f"data_{int(time.time())}.txt"
        return filename
    
    def parse(self, filepath):
        """解析数据文件
        
        Args:
            filepath: 数据文件路径
            
        Returns:
            pandas.DataFrame: 解析后的数据
        """
        # 由子类实现具体解析逻辑
        raise NotImplementedError("子类必须实现parse方法")
    
    def load(self, force_update=False):
        """加载数据（下载+解析）
        
        Args:
            force_update: 是否强制更新数据
            
        Returns:
            pandas.DataFrame: 加载的数据
        """
        try:
            # 下载数据
            filepath = self.download(force_update=force_update)
            
            # 解析数据
            data = self.parse(filepath)
            
            return data
        except Exception as e:
            logging.error(f"加载数据失败: {str(e)}")
            # 返回空DataFrame
            return pd.DataFrame()

class Kuaile8Loader(BaseDataLoader):
    """快乐8数据下载器"""
    
    def __init__(self, config=None):
        super().__init__(config)
        # 设置默认URL
        if not self.url:
            self.url = 'https://data.17500.cn/kl8_asc.txt'
    
    def parse(self, filepath):
        """解析快乐8数据文件
        
        Args:
            filepath: 数据文件路径
            
        Returns:
            pandas.DataFrame: 解析后的数据
        """
        logging.info(f"正在解析快乐8数据: {filepath}")
        
        try:
            # 读取文件内容
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # 解析数据行
            data = []
            
            for line_idx, line in enumerate(lines):
                line = line.strip()
                if not line or len(line) < 10:  # 跳过空行或太短的行
                    continue
                
                try:
                    # 将行按空格分割
                    parts = line.split()
                    
                    # 第一部分是期号，第二部分是日期
                    if len(parts) < 22:  # 至少需要期号、日期和20个号码
                        logging.warning(f"行 {line_idx+1} 数据不完整，跳过: {line[:50]}...")
                        continue
                    
                    draw_no = parts[0]  # 期号是第一个部分
                    draw_date_str = parts[1]  # 日期是第二个部分
                    
                    # 尝试解析日期
                    try:
                        draw_date = pd.to_datetime(draw_date_str)
                    except:
                        logging.warning(f"无法解析日期: {draw_date_str}, 行 {line_idx+1}")
                        continue
                    
                    # 提取开奖号码 - 是第3到第22个部分 (索引2-21)
                    numbers = []
                    for i in range(2, 22):
                        if i < len(parts) and parts[i].isdigit():
                            numbers.append(int(parts[i]))
                        else:
                            logging.warning(f"期号 {draw_no} 第{i-1}个号码格式错误: {parts[i] if i < len(parts) else 'missing'}")
                    
                    # 确保有20个号码
                    if len(numbers) != 20:
                        logging.warning(f"期号 {draw_no} 号码数量不匹配: {len(numbers)} != 20")
                        # 如果号码不足，可以选择跳过或填充
                        if len(numbers) < 10:  # 如果号码太少，直接跳过
                            continue
                    
                    # 添加到数据列表
                    data.append({
                        'draw_date': draw_date,
                        'draw_no': draw_no,
                        'numbers': numbers  # 直接使用列表，不需要嵌套
                    })
                    
                except Exception as e:
                    logging.error(f"解析行 {line_idx+1} 时出错: {str(e)}, 行内容: {line[:50]}...")
            
            # 创建DataFrame
            if not data:
                logging.warning("没有有效的数据行")
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            
            # 按日期排序，最新的在前面（与双色球保持一致）
            df = df.sort_values('draw_date', ascending=False)
            
            # 确保numbers列是列表格式
            df['numbers'] = df['numbers'].apply(lambda x: [x] if isinstance(x, list) else [[x]])
            
            logging.info(f"成功解析 {len(df)} 条记录")
            return df
            
        except Exception as e:
            logging.error(f"解析文件时发生错误: {str(e)}")
            return pd.DataFrame()
    
    def get_latest_draw_info(self):
        """获取最新一期开奖信息
        
        Returns:
            dict: 最新一期开奖信息
        """
        df = self.load()
        if df.empty:
            return None
        
        # 获取最新一期
        latest = df.iloc[0]
        
        return {
            'draw_date': latest['draw_date'].strftime('%Y-%m-%d'),
            'draw_no': latest['draw_no'],
            'numbers': latest['numbers'][0] if isinstance(latest['numbers'], list) else latest['numbers'],
        }

class DoubleColorBallLoader(BaseDataLoader):
    """双色球数据下载器"""
    
    def __init__(self, config=None):
        super().__init__(config)
        # 设置默认URL
        if not self.url:
            self.url = 'https://data.17500.cn/ssq_asc.txt'
    
    def parse(self, filepath):
        """解析双色球数据文件"""
        logging.info(f"正在解析双色球数据: {filepath}")
        
        try:
            # 读取文件内容
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.readlines()
            
            # 解析数据行
            data = []
            
            for line in content:
                parts = line.strip().split()
                if len(parts) < 8:  # 至少需要期号、日期、6个红球和1个蓝球
                    continue
                
                try:
                    draw_no = parts[0]
                    draw_date = parts[1]
                    # 红球是第3-8个数字
                    red_numbers = [int(parts[i]) for i in range(2, 8)]
                    # 蓝球是第9个数字
                    blue_number = int(parts[8])
                    
                    # 添加到数据列表
                    data.append({
                        'draw_date': pd.to_datetime(draw_date),
                        'draw_no': draw_no,
                        'red_numbers': red_numbers,
                        'blue_number': blue_number
                    })
                except (ValueError, IndexError) as e:
                    logging.warning(f"解析行出错: {line.strip()}, 错误: {str(e)}")
                    continue
            
            # 转换为DataFrame
            df = pd.DataFrame(data)
            
            # 按日期排序，最新的在前面
            if not df.empty:
                df = df.sort_values(by='draw_date', ascending=False)
            
            logging.info(f"成功解析 {len(df)} 条双色球数据记录")
            return df
            
        except Exception as e:
            logging.error(f"解析双色球数据失败: {str(e)}")
            return pd.DataFrame()

class DataUpdater:
    """数据更新管理器 - 管理多种彩票数据的更新"""
    
    def __init__(self):
        default_dir = str(DEFAULT_DATA_DIR)
        self.loaders = {
            'keno8': Kuaile8Loader({
                'url': 'https://data.17500.cn/kl8_asc.txt',
                'output_path': default_dir
            }),
            'ssq': DoubleColorBallLoader({
                'url': 'https://data.17500.cn/ssq_asc.txt',
                'output_path': default_dir
            })
        }
    
    def update_all(self, force_update=False):
        """更新所有彩票数据
        
        Args:
            force_update: 是否强制更新
            
        Returns:
            dict: 各类彩票数据的更新状态
        """
        results = {}
        
        for game_type, loader in self.loaders.items():
            logging.info(f"正在更新 {game_type} 数据...")
            try:
                df = loader.load(force_update=force_update)
                results[game_type] = {
                    'success': not df.empty,
                    'count': len(df),
                    'latest': df.iloc[0]['draw_date'].strftime('%Y-%m-%d') if not df.empty else None
                }
                logging.info(f"{game_type} 数据更新成功，共 {len(df)} 条记录")
            except Exception as e:
                logging.error(f"{game_type} 数据更新失败: {str(e)}")
                results[game_type] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results
    
    def update_game(self, game_type, force_update=False):
        """更新指定彩票数据
        
        Args:
            game_type: 彩票类型
            force_update: 是否强制更新
            
        Returns:
            pandas.DataFrame: 更新后的数据
        """
        if game_type not in self.loaders:
            raise ValueError(f"不支持的彩票类型: {game_type}")
        
        loader = self.loaders[game_type]
        return loader.load(force_update=force_update)
    
    def get_latest_draw(self, game_type):
        """获取最新一期开奖信息
        
        Args:
            game_type: 彩票类型
            
        Returns:
            dict: 最新一期开奖信息
        """
        if game_type not in self.loaders:
            raise ValueError(f"不支持的彩票类型: {game_type}")
        
        if game_type == 'keno8' and hasattr(self.loaders[game_type], 'get_latest_draw_info'):
            return self.loaders[game_type].get_latest_draw_info()
        
        # 通用方法
        df = self.loaders[game_type].load(force_update=False)
        if df.empty:
            return None
        
        latest = df.iloc[0]
        result = {
            'draw_date': latest['draw_date'].strftime('%Y-%m-%d'),
            'draw_no': latest['draw_no'],
        }
        
        # 根据不同彩票类型添加号码信息
        if game_type == 'keno8':
            result['numbers'] = latest['numbers'][0] if isinstance(latest['numbers'], list) else latest['numbers']
        elif game_type == 'ssq':
            result['red_numbers'] = latest['red_numbers']
            result['blue_number'] = latest['blue_number']
        
        return result

def main():
    """命令行入口函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='彩票数据下载更新工具')
    parser.add_argument('--game', type=str, choices=['keno8', 'ssq', 'all'], default='all',
                        help='要更新的彩票类型 (keno8: 快乐8, ssq: 双色球, all: 全部)')
    parser.add_argument('--force', action='store_true', help='强制更新数据')
    parser.add_argument('--latest', action='store_true', help='只显示最新一期信息')
    parser.add_argument('--output', type=str, help='输出文件路径 (JSON格式)')
    
    args = parser.parse_args()
    
    updater = DataUpdater()
    
    if args.latest:
        # 显示最新一期信息
        if args.game == 'all':
            results = {}
            for game in ['keno8', 'ssq']:
                results[game] = updater.get_latest_draw(game)
        else:
            results = updater.get_latest_draw(args.game)
        
        # 输出结果
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        else:
            print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        # 更新数据
        if args.game == 'all':
            results = updater.update_all(force_update=args.force)
        else:
            df = updater.update_game(args.game, force_update=args.force)
            results = {
                args.game: {
                    'success': not df.empty,
                    'count': len(df),
                    'latest': df.iloc[0]['draw_date'].strftime('%Y-%m-%d') if not df.empty else None
                }
            }
        
        # 输出结果
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        else:
            print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main() 
