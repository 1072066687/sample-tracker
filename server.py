#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
样品管理同步系统 — Flask 服务器
提供 API 接口和网页看板
"""

import os
import sys
import sqlite3
import json
from datetime import datetime

from flask import Flask, request, jsonify, render_template

# 添加当前目录到 sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import server_config

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)


# ==================== 数据库初始化 ====================

def get_db_path() -> str:
    """获取数据库文件路径，确保目录存在"""
    db_path = server_config.DB_PATH
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)
    return db_path


def get_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库，创建表结构"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT,
            shop_name TEXT,
            name TEXT,
            colors TEXT,
            sizes TEXT,
            cost REAL,
            PRIMARY KEY(id, shop_name)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id TEXT,
            shop_name TEXT,
            date TEXT,
            product_name TEXT,
            color TEXT,
            size TEXT,
            quantity INTEGER,
            unit_cost REAL,
            total_cost REAL,
            creator TEXT,
            note TEXT,
            PRIMARY KEY(id, shop_name)
        )
    """)
    conn.commit()
    conn.close()


# ==================== API 端点 ====================

@app.route("/api/sync", methods=["POST"])
def api_sync():
    """桌面端同步数据端点"""
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"status": "error", "message": "无效的JSON数据"}), 400

    if not data:
        return jsonify({"status": "error", "message": "请求体为空"}), 400

    shop_name = data.get("shop_name", "")
    if not shop_name:
        return jsonify({"status": "error", "message": "缺少 shop_name"}), 400

    products = data.get("products", [])
    records = data.get("records", [])
    sync_time = data.get("sync_time", datetime.now().isoformat())

    conn = get_connection()
    cursor = conn.cursor()

    record_count = 0

    # 存储产品配置
    for product in products:
        product_id = product.get("id", "")
        if not product_id:
            continue
        colors_str = json.dumps(product.get("colors", []), ensure_ascii=False)
        sizes_str = json.dumps(product.get("sizes", []), ensure_ascii=False)
        cursor.execute("""
            INSERT OR REPLACE INTO products (id, shop_name, name, colors, sizes, cost)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            product_id,
            shop_name,
            product.get("name", ""),
            colors_str,
            sizes_str,
            product.get("cost", 0.0),
        ))

    # 存储发样记录（按 id + shop_name 去重）
    for record in records:
        record_id = record.get("id", "")
        if not record_id:
            continue
        cursor.execute("""
            INSERT OR IGNORE INTO records
                (id, shop_name, date, product_name, color, size,
                 quantity, unit_cost, total_cost, creator, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record_id,
            shop_name,
            record.get("date", ""),
            record.get("product_name", ""),
            record.get("color", ""),
            record.get("size", ""),
            record.get("quantity", 0),
            record.get("unit_cost", 0.0),
            record.get("total_cost", 0.0),
            record.get("creator", ""),
            record.get("note", ""),
        ))
        if cursor.rowcount > 0:
            record_count += 1

    conn.commit()
    conn.close()

    return jsonify({
        "status": "ok",
        "record_count": record_count,
        "product_count": len(products),
        "sync_time": sync_time,
    })


@app.route("/api/data", methods=["GET"])
def api_data():
    """网页看板获取数据端点"""
    shop = request.args.get("shop", "全部")

    conn = get_connection()
    cursor = conn.cursor()

    # 获取所有店铺名称
    cursor.execute("SELECT DISTINCT shop_name FROM products ORDER BY shop_name")
    shops = [row["shop_name"] for row in cursor.fetchall()]

    # 获取产品
    if shop and shop != "全部":
        cursor.execute("SELECT * FROM products WHERE shop_name = ? ORDER BY name", (shop,))
    else:
        cursor.execute("SELECT * FROM products ORDER BY shop_name, name")

    products = []
    for row in cursor.fetchall():
        try:
            colors = json.loads(row["colors"]) if row["colors"] else []
        except (json.JSONDecodeError, TypeError):
            colors = []
        try:
            sizes = json.loads(row["sizes"]) if row["sizes"] else []
        except (json.JSONDecodeError, TypeError):
            sizes = []
        products.append({
            "id": row["id"],
            "shop_name": row["shop_name"],
            "name": row["name"],
            "colors": colors,
            "sizes": sizes,
            "cost": row["cost"],
        })

    # 获取记录
    if shop and shop != "全部":
        cursor.execute("SELECT * FROM records WHERE shop_name = ? ORDER BY date DESC", (shop,))
    else:
        cursor.execute("SELECT * FROM records ORDER BY shop_name, date DESC")

    records = []
    for row in cursor.fetchall():
        records.append({
            "id": row["id"],
            "shop_name": row["shop_name"],
            "date": row["date"],
            "product_name": row["product_name"],
            "color": row["color"],
            "size": row["size"],
            "quantity": row["quantity"],
            "unit_cost": row["unit_cost"],
            "total_cost": row["total_cost"],
            "creator": row["creator"],
            "note": row["note"],
        })

    conn.close()

    return jsonify({
        "shops": shops,
        "records": records,
        "products": products,
    })


@app.route("/")
def index():
    """网页看板首页"""
    return render_template("dashboard.html")


# ==================== 启动 ====================

if __name__ == "__main__":
    print(f"正在初始化数据库：{get_db_path()}")
    init_db()
    print(f"服务器启动：http://{server_config.HOST}:{server_config.PORT}")
    print(f"看板地址：http://localhost:{server_config.PORT}")
    app.run(
        host=server_config.HOST,
        port=server_config.PORT,
        debug=server_config.DEBUG,
    )
