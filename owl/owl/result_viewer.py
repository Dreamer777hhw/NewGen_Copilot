"""
    * @FileDescription: 结果查看器 
    * @Author: 胡皓文
    * @Date: 2025-04-02
    * @LastEditors: 胡皓文
    * @LastEditTime: 2025-04-06
    * @Contributors: 胡皓文，范起豪
"""

import os
import http.server
import socketserver
import threading
from pathlib import Path
import queue
import json
from datetime import datetime
import shutil
import re
import sqlite3  # 添加sqlite3导入

# 创建一个全局队列用于存储最新结果
result_queue = queue.Queue()
current_result = "等待处理结果..."

# 结果历史记录
results_history = []
# 结果历史文件路径 - 使用pathlib获取相对路径
base_dir = Path(__file__).parent
HISTORY_FILE = str(base_dir / "owl_results_history.json")
# HTML报告目录
REPORTS_DIR = str(base_dir / "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# 数据库文件路径
DB_FILE = str(base_dir / "owl_results.db")

# 初始化数据库
def init_db():
    """初始化数据库，创建必要的表"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 创建结果历史表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS results_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        result TEXT NOT NULL,
        instruction TEXT,
        article_url TEXT,
        scene TEXT,
        images TEXT,
        tables TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    print(f"数据库初始化完成: {DB_FILE}")

# 加载历史记录
def load_history():
    """加载历史记录"""
    global results_history
    
    # 首先尝试从数据库加载
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row  # 启用行工厂，以便通过名称访问列
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT timestamp, result, instruction, article_url, scene, images, tables
        FROM results_history
        ORDER BY timestamp DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        if rows:
            results_history = []
            for row in rows:
                item = {
                    "timestamp": row["timestamp"],
                    "result": row["result"],
                    "instruction": row["instruction"],
                    "article_url": row["article_url"],
                    "scene": row["scene"]
                }
                
                # 处理JSON格式的字段
                if row["images"]:
                    try:
                        item["images"] = json.loads(row["images"])
                    except:
                        item["images"] = []
                
                if row["tables"]:
                    try:
                        item["tables"] = json.loads(row["tables"])
                    except:
                        item["tables"] = []
                
                results_history.append(item)
            
            print(f"从数据库加载了 {len(results_history)} 条历史记录")
            return
    except Exception as e:
        print(f"从数据库加载历史记录时出错: {str(e)}")
    
    # 如果数据库加载失败，则尝试从JSON文件加载
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                file_content = f.read().strip()
                if file_content:  # 检查文件是否为空
                    results_history = json.loads(file_content)
                else:
                    results_history = []  # 如果文件为空，初始化为空列表
                
            # 确保历史记录按时间戳倒序排列
            results_history = sorted(results_history, 
                                    key=lambda x: x.get('timestamp', ''), 
                                    reverse=True)
            
            # 数据库和JSON文件同步
            if results_history:
                sync_history_to_db()
        else:
            results_history = []
    except Exception as e:
        print(f"从JSON文件加载历史记录时出错: {str(e)}")
        results_history = []

# 将JSON文件中的历史记录同步到数据库
def sync_history_to_db():
    """将JSON文件中的历史记录同步到数据库中"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 清空数据库中的历史记录
        cursor.execute('DELETE FROM results_history')
        
        # 将JSON中的历史记录插入数据库
        for item in results_history:
            timestamp = item.get('timestamp', '')
            result = item.get('result', '')
            instruction = item.get('instruction', '')
            article_url = item.get('article_url', '')
            scene = item.get('scene', '默认场景')
            
            # 处理复杂字段
            images = json.dumps(item.get('images', [])) if item.get('images') else None
            tables = json.dumps(item.get('tables', [])) if item.get('tables') else None
            
            cursor.execute('''
            INSERT INTO results_history 
            (timestamp, result, instruction, article_url, scene, images, tables)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, result, instruction, article_url, scene, images, tables))
        
        conn.commit()
        conn.close()
        print(f"已同步 {len(results_history)} 条历史记录到数据库")
    except Exception as e:
        print(f"同步历史记录到数据库时出错: {str(e)}")

# 保存历史记录
def save_history():
    """保存历史记录到JSON文件和数据库"""
    # 保存到JSON文件
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(results_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存历史记录到JSON文件出错: {str(e)}")
    
    # 保存到数据库
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 清空当前记录
        cursor.execute('DELETE FROM results_history')
        
        # 插入最新的记录
        for item in results_history:
            timestamp = item.get('timestamp', '')
            result = item.get('result', '')
            instruction = item.get('instruction', '')
            article_url = item.get('article_url', '')
            scene = item.get('scene', '默认场景')
            
            # 处理复杂字段
            images = json.dumps(item.get('images', [])) if item.get('images') else None
            tables = json.dumps(item.get('tables', [])) if item.get('tables') else None
            
            cursor.execute('''
            INSERT INTO results_history 
            (timestamp, result, instruction, article_url, scene, images, tables)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, result, instruction, article_url, scene, images, tables))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"保存历史记录到数据库出错: {str(e)}")

# HTML模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>OWL结果查看器</title>
    <meta charset="utf-8">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/dompurify/dist/purify.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.4;
            margin: 0;
            padding: 15px;
            background-color: #f5f5f5;
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1, h2, h3 {{
            color: #333;
            margin-top: 10px;
            margin-bottom: 12px;
            line-height: 1.3;
        }}
        h1 {{
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 8px;
        }}
        .button-container {{
            margin: 10px 0;
            display: flex;
            gap: 10px;
        }}
        button {{
            background-color: #4CAF50;
            color: white;
            padding: 8px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 15px;
            transition: background-color 0.3s;
        }}
        button:hover {{
            background-color: #45a049;
        }}
        button.secondary {{
            background-color: #2196F3;
        }}
        button.secondary:hover {{
            background-color: #0b7dda;
        }}
        button.danger {{
            background-color: #f44336;
        }}
        button.danger:hover {{
            background-color: #d32f2f;
        }}
        .result-container {{
            background-color: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 12px;
            white-space: pre-wrap;
        }}
        .history-container {{
            margin-top: 15px;
        }}
        .history-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        .history-item {{
            background-color: white;
            padding: 12px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 12px;
        }}
        .timestamp {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 6px;
        }}
        .instruction {{
            background-color: #e6f7ff;
            padding: 8px;
            border-left: 4px solid #1890ff;
            margin-bottom: 10px;
            font-style: italic;
            display: block;
            line-height: 1.3;
        }}
        .content {{
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 4px;
            white-space: pre-wrap;
            line-height: 1.4;
        }}
        .content p {{
            margin-top: 0.5em;
            margin-bottom: 0.5em;
        }}
        .content ul, .content ol {{
            margin-top: 0.3em;
            margin-bottom: 0.3em;
            padding-left: 1.5em;
        }}
        .content li {{
            margin-bottom: 0.2em;
            line-height: 1.3;
        }}
        .content li p {{
            margin-top: 0.2em;
            margin-bottom: 0.2em;
        }}
        .content ul ul, .content ol ol, .content ul ol, .content ol ul {{
            margin-top: 0.2em;
            margin-bottom: 0.2em;
        }}
        .result-box {{
            border: 1px solid #ddd;
            border-radius: 5px;
            overflow: hidden;
            margin-bottom: 12px;
        }}
        .instruction-section {{
            background-color: #e6f7ff;
            padding: 8px 10px;
            border-bottom: 1px solid #ddd;
            font-style: italic;
            line-height: 1.3;
        }}
        .answer-section {{
            padding: 10px;
        }}
        .answer-section .content {{
            margin-top: 6px;
        }}
        .image-section {{
            margin-top: 12px;
            border-top: 1px solid #eee;
            padding-top: 10px;
        }}
        .image-container {{
            margin-bottom: 10px;
        }}
        .image-container img {{
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .image-description {{
            font-style: italic;
            color: #666;
            margin-top: 4px;
            line-height: 1.3;
        }}
        .table-section {{
            margin-top: 12px;
            border-top: 1px solid #eee;
            padding-top: 10px;
            overflow-x: auto;
        }}
        .scene-tag {{
            margin-bottom: 8px;
        }}
        .scene-tag span {{
            background-color: #e6f7ff;
            color: #0066cc;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.85em;
            display: inline-block;
        }}
        .tabs {{
            display: flex;
            margin-bottom: 12px;
            border-bottom: 1px solid #ddd;
        }}
        .tab {{
            padding: 8px 16px;
            cursor: pointer;
            border: 1px solid transparent;
            border-bottom: none;
            border-radius: 4px 4px 0 0;
            background-color: #f1f1f1;
            margin-right: 4px;
        }}
        .tab.active {{
            background-color: white;
            border-color: #ddd;
            position: relative;
        }}
        .tab.active::after {{
            content: '';
            position: absolute;
            bottom: -1px;
            left: 0;
            width: 100%;
            height: 1px;
            background-color: white;
        }}
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}
        .search-container {{
            margin: 10px 0;
            display: flex;
            gap: 10px;
        }}
        .search-input {{
            flex-grow: 1;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .db-stats {{
            background-color: #e8f5e9;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 15px;
        }}
        .db-stats p {{
            margin: 5px 0;
        }}
        .pagination {{
            display: flex;
            justify-content: center;
            margin-top: 15px;
            gap: 5px;
        }}
        .pagination button {{
            padding: 5px 10px;
        }}
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }}
        .modal-content {{
            background-color: white;
            margin: 10% auto;
            padding: 20px;
            border-radius: 5px;
            width: 80%;
            max-width: 700px;
            max-height: 80vh; /* 限制最大高度为视口高度的80% */
            overflow-y: auto; /* 添加垂直滚动条 */
        }}
        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .close-btn {{
            font-size: 24px;
            cursor: pointer;
        }}
        /* 添加响应式设计 */
        @media (max-width: 768px) {{
            body {{
                padding: 8px;
            }}
            .result-container, .history-item {{
                padding: 10px;
            }}
            .history-header {{
                flex-direction: column;
                align-items: flex-start;
            }}
            .history-header button {{
                margin-top: 8px;
            }}
            .button-container {{
                flex-wrap: wrap;
            }}
            .modal-content {{
                width: 95%;
                margin: 5% auto;
            }}
        }}
    </style>
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const resultArea = document.getElementById('result-area');

            const parseMarkdownElements = () => {{
                document.querySelectorAll('.content').forEach(element => {{
                    const raw = element.textContent;
                    const clean = DOMPurify.sanitize(raw);
                    element.innerHTML = marked.parse(clean);
                }});
            }};

            parseMarkdownElements();
            
            // 建立WebSocket连接
            const ws = new WebSocket('ws://localhost:{ws_port}');
            
            ws.onopen = function(event) {{
                console.log('WebSocket连接已建立');
            }};
            
            ws.onmessage = function(event) {{
                
                resultArea.innerHTML = event.data;
    
                // 仅对.content元素进行Markdown解析
                resultArea.querySelectorAll('.content').forEach(contentDiv => {{
                    const raw = contentDiv.textContent; // 获取原始文本内容
                    const clean = DOMPurify.sanitize(raw);
                    contentDiv.innerHTML = marked.parse(clean);
                }});
                // 如果消息包含"历史记录已清除"，则刷新页面以更新历史记录显示
                if(event.data.includes("历史记录已清除")) {{
                    setTimeout(function() {{
                        window.location.reload();
                    }}, 1000);
                }}
            }};
            
            ws.onerror = function(error) {{
                console.error('WebSocket错误:', error);
            }};
            
            ws.onclose = function(event) {{
                console.log('WebSocket连接已关闭');
            }};
            
            // 新任务按钮点击事件
            document.getElementById('new-task-button').addEventListener('click', function() {{
                // 发送清除消息给服务器
                ws.send('clear');
                // 清空当前结果显示
                resultArea.innerHTML = "准备好接收新任务...";
            }});
            
            // 清除历史记录按钮点击事件
            document.getElementById('clear-history-button').addEventListener('click', function() {{
                if(confirm('确定要清除所有历史记录吗？此操作不可撤销。')) {{
                    // 发送清除历史记录消息给服务器
                    ws.send('clear_history');
                }}
            }});

            // 选项卡功能
            const tabs = document.querySelectorAll('.tab');
            const tabContents = document.querySelectorAll('.tab-content');
            
            tabs.forEach(tab => {{
                tab.addEventListener('click', () => {{
                    // 移除所有活动类
                    tabs.forEach(t => t.classList.remove('active'));
                    tabContents.forEach(c => c.classList.remove('active'));
                    
                    // 添加活动类到当前选项卡
                    tab.classList.add('active');
                    document.getElementById(tab.dataset.target).classList.add('active');
                }});
            }});
            
            // 数据库统计信息获取
            const fetchDbStats = () => {{
                fetch('/api/db-stats')
                    .then(response => response.json())
                    .then(data => {{
                        if (data.status === 'success') {{
                            document.getElementById('total-records').textContent = data.totalRecords;
                            document.getElementById('latest-record').textContent = data.latestRecord;
                            document.getElementById('db-size').textContent = data.dbSize;
                        }}
                    }})
                    .catch(error => console.error('获取数据库统计信息出错:', error));
            }};
            
            // 加载数据库历史记录
            const loadDbHistory = (page = 1, search = '') => {{
                let url = `/api/history?page=${{page}}`;
                if (search) {{
                    url += `&search=${{encodeURIComponent(search)}}`;
                }}
                
                fetch(url)
                    .then(response => response.json())
                    .then(data => {{
                        if (data.status === 'success') {{
                            const historyList = document.getElementById('db-history-list');
                            historyList.innerHTML = '';
                            
                            data.history.forEach(item => {{
                                const historyItem = document.createElement('div');
                                historyItem.className = 'history-item';
                                historyItem.innerHTML = `
                                    <h3>任务 #${{item.id}}</h3>
                                    <div class="timestamp">${{item.timestamp}}</div>
                                    <div class="scene-tag"><span>场景: ${{item.scene || '默认场景'}}</span></div>
                                    <div class="instruction"><strong>指令:</strong> <em>${{item.instruction || '无指令'}}</em></div>
                                    <button class="secondary view-detail-btn" data-id="${{item.id}}">查看详情</button>
                                `;
                                historyList.appendChild(historyItem);
                            }});
                            
                            // 添加查看详情事件
                            document.querySelectorAll('.view-detail-btn').forEach(btn => {{
                                btn.addEventListener('click', () => {{
                                    const recordId = btn.dataset.id;
                                    loadRecordDetail(recordId);
                                }});
                            }});
                            
                            // 更新分页
                            const pagination = document.getElementById('pagination');
                            pagination.innerHTML = '';
                            
                            if (data.totalPages > 1) {{
                                // 上一页按钮
                                if (page > 1) {{
                                    const prevBtn = document.createElement('button');
                                    prevBtn.textContent = '上一页';
                                    prevBtn.addEventListener('click', () => loadDbHistory(page - 1, search));
                                    pagination.appendChild(prevBtn);
                                }}
                                
                                // 页码
                                for (let i = 1; i <= data.totalPages; i++) {{
                                    const pageBtn = document.createElement('button');
                                    pageBtn.textContent = i;
                                    if (i === page) {{
                                        pageBtn.disabled = true;
                                    }}
                                    pageBtn.addEventListener('click', () => loadDbHistory(i, search));
                                    pagination.appendChild(pageBtn);
                                }}
                                
                                // 下一页按钮
                                if (page < data.totalPages) {{
                                    const nextBtn = document.createElement('button');
                                    nextBtn.textContent = '下一页';
                                    nextBtn.addEventListener('click', () => loadDbHistory(page + 1, search));
                                    pagination.appendChild(nextBtn);
                                }}
                            }}
                        }}
                    }})
                    .catch(error => console.error('加载历史记录出错:', error));
            }};
            
            // 加载记录详情
            const loadRecordDetail = (recordId) => {{
                fetch(`/api/history/${{recordId}}`)
                    .then(response => response.json())
                    .then(data => {{
                        if (data.status === 'success') {{
                            const modal = document.getElementById('detail-modal');
                            const record = data.record;
                            
                            // 填充模态框内容
                            document.getElementById('modal-title').textContent = `任务 #${{record.id}} 详情`;
                            document.getElementById('modal-timestamp').textContent = record.timestamp;
                            document.getElementById('modal-scene').textContent = record.scene || '默认场景';
                            document.getElementById('modal-instruction').textContent = record.instruction || '无指令';
                            
                            // 处理结果内容
                            const contentDiv = document.getElementById('modal-content');
                            contentDiv.textContent = record.result;
                            contentDiv.innerHTML = marked.parse(DOMPurify.sanitize(record.result));
                            
                            // 处理图片
                            const imagesContainer = document.getElementById('modal-images');
                            imagesContainer.innerHTML = '';
                            
                            if (record.images && record.images.length > 0) {{
                                const imagesSection = document.createElement('div');
                                imagesSection.className = 'image-section';
                                imagesSection.innerHTML = '<h3>提取的图像</h3>';
                                
                                record.images.forEach((img, i) => {{
                                    if (img.path) {{
                                        const imgContainer = document.createElement('div');
                                        imgContainer.className = 'image-container';
                                        imgContainer.innerHTML = `
                                            <img src="/images/${{img.path}}" alt="图像 ${{i+1}}">
                                            <p class="image-description">${{img.description || '图像描述'}}</p>
                                        `;
                                        imagesSection.appendChild(imgContainer);
                                    }}
                                }});
                                
                                imagesContainer.appendChild(imagesSection);
                            }}
                            
                            // 处理表格
                            const tablesContainer = document.getElementById('modal-tables');
                            tablesContainer.innerHTML = '';
                            
                            if (record.tables && record.tables.length > 0) {{
                                const tablesSection = document.createElement('div');
                                tablesSection.className = 'table-section';
                                tablesSection.innerHTML = '<h3>提取的表格</h3>';
                                
                                record.tables.forEach((table, i) => {{
                                    const tableContainer = document.createElement('div');
                                    tableContainer.className = 'table-container';
                                    tableContainer.innerHTML = `
                                        <p class="table-description">${{table.description || '表格描述'}}</p>
                                        ${{table.data || ''}}
                                    `;
                                    tablesSection.appendChild(tableContainer);
                                }});
                                
                                tablesContainer.appendChild(tablesSection);
                            }}
                            
                            // 显示模态框
                            modal.style.display = 'block';
                        }}
                    }})
                    .catch(error => console.error('加载记录详情出错:', error));
            }};
            
            // 搜索功能
            const searchForm = document.getElementById('search-form');
            searchForm.addEventListener('submit', (e) => {{
                e.preventDefault();
                const searchTerm = document.getElementById('search-input').value.trim();
                loadDbHistory(1, searchTerm);
            }});
            
            // 关闭模态框
            document.querySelector('.close-btn').addEventListener('click', () => {{
                document.getElementById('detail-modal').style.display = 'none';
            }});
            
            // 点击模态框外部关闭
            window.addEventListener('click', (e) => {{
                const modal = document.getElementById('detail-modal');
                if (e.target === modal) {{
                    modal.style.display = 'none';
                }}
            }});
            
            // 初始化加载数据库统计和历史记录
            fetchDbStats();
            loadDbHistory();
            
            // 设置刷新定时器
            setInterval(fetchDbStats, 60000); // 每分钟刷新一次
            
            // 修改历史记录刷新后的解析
            const observer = new MutationObserver(parseMarkdownElements);
            observer.observe(document.querySelector('.history-container'), {{
                childList: true,
                subtree: true
            }});
        }});
    </script>
</head>
<body>
    <h1>OWL处理结果</h1>
    
    <div class="button-container">
        <button id="new-task-button">开始新任务</button>
        <button class="secondary" id="refresh-btn">刷新数据</button>
    </div>
    
    <div class="result-container">
        <div id="result-area">{result}</div>
    </div>
    
    <div class="tabs">
        <div class="tab active" data-target="file-history-tab">文件历史记录</div>
        <div class="tab" data-target="db-history-tab">数据库记录</div>
    </div>
    
    <div id="file-history-tab" class="tab-content active">
        <div class="history-container">
            <div class="history-header">
                <h2>历史记录 (文件存储)</h2>
                <button id="clear-history-button" class="danger">清除历史记录</button>
            </div>
            {history}
        </div>
    </div>
    
    <div id="db-history-tab" class="tab-content">
        <div class="history-container">
            <div class="history-header">
                <h2>数据库历史记录</h2>
                <div>
                    <button id="export-db-button" class="secondary">导出数据</button>
                    <button id="clear-db-button" class="danger">清除数据库</button>
                </div>
            </div>
            
            <div class="db-stats">
                <h3>数据库统计</h3>
                <p>总记录数: <span id="total-records">加载中...</span></p>
                <p>最新记录: <span id="latest-record">加载中...</span></p>
                <p>数据库大小: <span id="db-size">加载中...</span></p>
            </div>
            
            <div class="search-container">
                <form id="search-form">
                    <input type="text" id="search-input" class="search-input" placeholder="搜索指令或场景...">
                    <button type="submit" class="secondary">搜索</button>
                </form>
            </div>
            
            <div id="db-history-list">
                <!-- 数据库记录将在这里动态加载 -->
                <div class="history-item">
                    <p>加载中...</p>
                </div>
            </div>
            
            <div id="pagination" class="pagination">
                <!-- 分页控件将在这里动态加载 -->
            </div>
        </div>
    </div>
    
    <!-- 详情模态框 -->
    <div id="detail-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modal-title">任务详情</h2>
                <span class="close-btn">&times;</span>
            </div>
            <div class="timestamp">时间: <span id="modal-timestamp"></span></div>
            <div class="scene-tag"><span>场景: <span id="modal-scene"></span></span></div>
            <div class="instruction"><strong>指令:</strong> <em id="modal-instruction"></em></div>
            <h3>解答:</h3>
            <div class="content" id="modal-content"></div>
            <div id="modal-images"></div>
            <div id="modal-tables"></div>
        </div>
    </div>
</body>
</html>
"""

# 自定义HTTP请求处理器
class ResultViewerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 添加调试日志
        print(f"收到GET请求: {self.path}")
        
        # 处理图像请求
        if self.path.startswith('/images/'):
            try:
                image_path = self.path[8:]
                self.send_response(200)
                if image_path.endswith('.png'):
                    self.send_header('Content-type', 'image/png')
                elif image_path.endswith('.jpg') or image_path.endswith('.jpeg'):
                    self.send_header('Content-type', 'image/jpeg')
                else:
                    self.send_header('Content-type', 'application/octet-stream')
                self.end_headers()
                with open(image_path, 'rb') as f:
                    self.wfile.write(f.read())
                return
            except Exception as e:
                print(f"提供图像时出错: {str(e)}")
                self.send_error(404, "File not found")
                return
        # 处理数据库统计API
        elif self.path == '/api/db-stats':
            print("处理数据库统计请求")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')  # 添加CORS头
            self.end_headers()
            
            stats = self._get_db_stats()
            response = json.dumps({
                'status': 'success',
                **stats
            })
            print(f"数据库统计响应: {response}")
            self.wfile.write(response.encode('utf-8'))
            return
        # 处理历史记录API
        elif self.path.startswith('/api/history'):
            print(f"处理历史记录请求: {self.path}")
            # 检查是否是单条记录详情请求
            if self.path.startswith('/api/history/'):
                record_id = self.path.split('/')[-1]
                if not record_id.isdigit():
                    self.send_error(400, "无效的记录ID")
                    return
                
                record = self._get_history_detail_from_db(int(record_id))
                if record:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')  # 添加CORS头
                    self.end_headers()
                    response = json.dumps({
                        'status': 'success',
                        'record': record
                    })
                    print(f"记录详情响应: {record['id']}")
                    self.wfile.write(response.encode('utf-8'))
                else:
                    self.send_error(404, "Record not found")
                return
            else:
                # 处理历史记录列表请求
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')  # 添加CORS头
                self.end_headers()
                
                history = self._get_history_from_db()
                response = json.dumps({
                    'status': 'success',
                    'history': history,
                    'totalPages': 1
                })
                print(f"历史记录响应: 找到{len(history)}条记录")
                self.wfile.write(response.encode('utf-8'))
                return
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # 初始化当前结果为空
            global current_result
            current_result = "准备好接收新任务..."
            
            history_html = ""
            sorted_history = sorted(results_history, 
                                   key=lambda x: x.get('timestamp', ''), 
                                   reverse=True)
            
            for item in sorted_history:
                timestamp = item.get('timestamp', '')
                result = item.get('result', '')
                instruction = item.get('instruction', '')
                images = item.get('images', [])
                tables = item.get('tables', [])
                scene = item.get('scene', '默认场景')
                
                # 添加指令显示区域
                instruction_html = ""
                if instruction and instruction.strip():
                    # 对指令进行HTML转义，防止XSS攻击
                    instruction = instruction.replace('<', '&lt;').replace('>', '&gt;')
                    instruction_html = f'<div class="instruction"><strong>指令:</strong> <em>{instruction}</em></div>'
                
                # 添加场景显示
                scene_html = f'<div class="scene-tag"><span>场景: {scene}</span></div>'
                
                # 添加图像显示区域
                images_html = ""
                if images:
                    images_html = '<div class="image-section"><h3>提取的图像</h3>'
                    for i, img in enumerate(images):
                        img_path = img.get('path', '')
                        img_desc = img.get('description', '图像描述')
                        if img_path:
                            images_html += f'''
                            <div class="image-container">
                                <img src="/images/{img_path}" alt="图像 {i+1}">
                                <p class="image-description">{img_desc}</p>
                            </div>
                            '''
                    images_html += '</div>'
                
                # 添加表格显示区域
                tables_html = ""
                if tables:
                    tables_html = '<div class="table-section"><h3>提取的表格</h3>'
                    for i, table in enumerate(tables):
                        table_data = table.get('data', '')
                        table_desc = table.get('description', '表格描述')
                        tables_html += f'''
                        <div class="table-container">
                            <p class="table-description">{table_desc}</p>
                            {table_data}
                        </div>
                        '''
                    tables_html += '</div>'
                
                history_html += f"""
                <div class="history-item">
                    <h3>任务结果</h3>
                    <div class="timestamp">{timestamp}</div>
                    {scene_html}
                    {instruction_html}
                    <div class="content">{result}</div>
                    {images_html}
                    {tables_html}
                </div>
                """
            
            html = HTML_TEMPLATE.format(result=current_result, history=history_html, ws_port=7866)
            self.wfile.write(html.encode('utf-8'))
        else:
            super().do_GET()

    def _get_db_stats(self):
        """获取数据库统计信息"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 获取总记录数
        cursor.execute('SELECT COUNT(*) FROM results_history')
        total_records = cursor.fetchone()[0]
        
        # 获取最新记录时间
        cursor.execute('SELECT timestamp FROM results_history ORDER BY timestamp DESC LIMIT 1')
        latest_record_row = cursor.fetchone()
        latest_record = latest_record_row[0] if latest_record_row else "无记录"
        
        # 获取数据库文件大小
        try:
            db_size_bytes = os.path.getsize(DB_FILE)
            if db_size_bytes < 1024:
                db_size = f"{db_size_bytes} B"
            elif db_size_bytes < 1024 * 1024:
                db_size = f"{db_size_bytes / 1024:.2f} KB"
            else:
                db_size = f"{db_size_bytes / (1024 * 1024):.2f} MB"
        except:
            db_size = "未知"
        
        conn.close()
        
        return {
            'totalRecords': total_records,
            'latestRecord': latest_record,
            'dbSize': db_size
        }

    def _get_history_from_db(self):
        """从数据库获取历史记录"""
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询历史记录，只返回基本信息
        cursor.execute('''
        SELECT id, timestamp, instruction, scene
        FROM results_history
        ORDER BY timestamp DESC
        LIMIT 100
        ''')
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'timestamp': row['timestamp'],
                'instruction': row['instruction'],
                'scene': row['scene']
            })
        
        conn.close()
        return results
    
    def _get_history_detail_from_db(self, record_id):
        """从数据库获取单条历史记录的详细信息"""
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询指定ID的历史记录详情
        cursor.execute('''
        SELECT id, timestamp, result, instruction, article_url, scene, images, tables
        FROM results_history
        WHERE id = ?
        ''', (record_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # 构建详情对象
        detail = {
            'id': row['id'],
            'timestamp': row['timestamp'],
            'result': row['result'],
            'instruction': row['instruction'],
            'article_url': row['article_url'],
            'scene': row['scene']
        }
        
        # 解析JSON字段
        if row['images']:
            try:
                detail['images'] = json.loads(row['images'])
            except:
                detail['images'] = []
        
        if row['tables']:
            try:
                detail['tables'] = json.loads(row['tables'])
            except:
                detail['tables'] = []
        
        return detail

# 添加一个函数用于更新结果
def update_result(data):
    """更新当前结果并广播给所有连接的客户端"""
    global current_result, results_history
    instruction = data.get("instruction", "")
    # 处理数据
    content = data["answer"]
    article_url = data.get("article_url", "")
            
    # 处理换行符
    clean_content = content.strip()
    clean_content = re.sub(r'\n{2,}', '\n\n', clean_content)
            
    # 创建一个包含指令和内容的结构化显示框架 - 减少空白区域
    current_result = f"""<div class="result-box">
        <div class="instruction-section">
            <strong>指令:</strong> <em>{instruction if instruction else "无指令"}</em>
        </div>
        <div class="answer-section">
            <strong>解答:</strong>
            <div class="content">{clean_content}</div>
        </div>
    </div>"""
            
    # 只有当消息不是"正在处理中"时才添加到历史记录
    if not content.startswith("正在处理中"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scene = data.get("scene", "默认场景")
        # 提取图像和表格数据（如果有）
        images = data.get("images", [])
        tables = data.get("tables", [])
        
        # 创建新的历史记录条目
        new_entry = {
            "timestamp": timestamp, 
            "result": clean_content,
            "instruction": instruction,
            "article_url": article_url,
            "scene": scene
        }
        
        # 如果有图像或表格数据，添加到条目中
        if images:
            new_entry["images"] = images
        if tables:
            new_entry["tables"] = tables
        
        # 添加到历史记录中
        results_history.insert(0, new_entry)
 
    # 保存历史记录到文件和数据库
    save_history()
    
    # 将更新后的结果放入队列，供WebSocket发送
    result_queue.put(current_result)

def start_result_viewer():
    """启动结果查看器服务器"""
    # 初始化数据库
    init_db()
    
    # 加载历史记录
    load_history()
    
    # 使用不同的端口
    http_port = 7865
    ws_port = 7866
    
    # 启动HTTP服务器
    handler = ResultViewerHandler
    httpd = socketserver.TCPServer(("", http_port), handler)
    print(f"结果查看器已启动，访问 http://localhost:{http_port} 查看结果")
    
    # 启动WebSocket服务器线程
    ws_thread = threading.Thread(target=start_websocket_server, args=(ws_port,))
    ws_thread.daemon = True
    ws_thread.start()
    
    # 启动HTTP服务器
    httpd.serve_forever()

def start_websocket_server(port=7866):
    """启动WebSocket服务器"""
    import asyncio
    import websockets
    
    # 存储活动连接
    active_connections = set()
    
    async def register(websocket):
        """注册新的WebSocket连接"""
        global current_result
        active_connections.add(websocket)
        try:
            # 发送当前结果
            await websocket.send(current_result)
            
            # 处理来自客户端的消息
            async for message in websocket:
                if message == 'clear':
                    current_result = "准备好接收新任务..."
                    # 通知所有客户端
                    if active_connections:
                        websockets_tasks = [
                            conn.send(current_result) for conn in active_connections
                        ]
                        await asyncio.gather(*websockets_tasks)
                elif message == 'clear_history':
                    clear_history()
                    current_result = "历史记录已清除，准备好接收新任务..."
                    if active_connections:
                        websockets_tasks = [
                            conn.send(current_result) for conn in active_connections
                        ]
                        await asyncio.gather(*websockets_tasks)
        finally:
            active_connections.remove(websocket)
    
    async def broadcast_results():
        """广播结果更新到所有连接的客户端"""
        while True:
            try:
                # 非阻塞方式检查队列
                if not result_queue.empty():
                    result = result_queue.get_nowait()
                    if active_connections:  # 只有在有连接时才广播
                        websockets_tasks = [
                            websocket.send(result) for websocket in active_connections
                        ]
                        await asyncio.gather(*websockets_tasks)
                
                # 短暂休眠以避免CPU占用过高
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"广播结果时出错: {str(e)}")
    
    async def main():
        """主WebSocket服务器函数"""
        # 启动WebSocket服务器
        async with websockets.serve(register, "localhost", port):
            print(f"WebSocket服务器已启动，监听端口 {port}")
            # 启动广播任务
            broadcast_task = asyncio.create_task(broadcast_results())
            # 保持服务器运行
            await asyncio.Future()
    
    # 运行WebSocket服务器
    asyncio.run(main())

# 添加一个清除历史记录的函数
def clear_history():
    """清除历史记录"""
    global results_history
    results_history = []
    
    # 清除JSON文件
    save_history()
    
    # 清除数据库记录
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM results_history')
        
        # 重置自增ID计数器
        cursor.execute('DELETE FROM sqlite_sequence WHERE name="results_history"')
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"清除数据库历史记录时出错: {str(e)}")
    
    print("历史记录已清除")
