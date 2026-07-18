#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
样品管理同步系统 — 服务器配置
"""
import os

# 服务器主机和端口（Railway 会自动设置 $PORT 环境变量）
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5000))
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

# 数据库路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "sample_data.db")
