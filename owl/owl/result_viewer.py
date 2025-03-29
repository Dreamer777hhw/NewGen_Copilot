import os
import http.server
import socketserver
import threading
import time
from pathlib import Path
import queue
import json
import asyncio
from datetime import datetime
from clean_owl_results import extract_owl_response

# 创建一个全局队列用于存储最新结果
result_queue = queue.Queue()
current_result = "等待处理结果..."

# 结果历史记录
results_history = []
# 结果历史文件路径 - 使用pathlib获取相对路径
base_dir = Path(__file__).parent
HISTORY_FILE = str(base_dir / "owl_results_history.json")
# print(HISTORY_FILE,"result_viewer.py")
# 加载历史记录
def load_history():
    """加载历史记录"""
    global results_history
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                results_history = json.load(f)
                
            # 确保历史记录按时间戳倒序排列
            results_history = sorted(results_history, 
                                    key=lambda x: x.get('timestamp', ''), 
                                    reverse=True)
        else:
            results_history = []
    except Exception as e:
        print(f"加载历史记录时出错: {str(e)}")
        results_history = []

# 保存历史记录
def save_history():
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(results_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存历史记录出错: {str(e)}")

# HTML模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>OWL结果查看器</title>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1, h2, h3 {{
            color: #333;
        }}
        .button-container {{
            margin: 20px 0;
        }}
        button {{
            background-color: #4CAF50;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }}
        button:hover {{
            background-color: #45a049;
        }}
        .result-container {{
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            white-space: pre-wrap;
        }}
        .history-container {{
            margin-top: 30px;
        }}
        .history-item {{
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 15px;
        }}
        .timestamp {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
        }}
        .tab-buttons {{
            margin-bottom: 10px;
        }}
        .tab-button {{
            background-color: #f1f1f1;
            color: #333;
            padding: 8px 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 5px;
        }}
        .tab-button.active {{
            background-color: #4CAF50;
            color: white;
        }}
        .content {{
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 4px;
            white-space: pre-wrap;
        }}
        .hidden {{
            display: none;
        }}
    </style>
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const resultArea = document.getElementById('result-area');
            
            // 建立WebSocket连接
            const ws = new WebSocket('ws://localhost:{ws_port}');
            
            ws.onopen = function(event) {{
                console.log('WebSocket连接已建立');
            }};
            
            ws.onmessage = function(event) {{
                // 更新结果区域
                resultArea.innerHTML = event.data;
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
            
            // 添加切换原始/清理结果的功能
            const historyItems = document.querySelectorAll('.history-item');
            historyItems.forEach(item => {{
                const cleanButton = item.querySelector('.clean-tab');
                const rawButton = item.querySelector('.raw-tab');
                const cleanContent = item.querySelector('.clean-content');
                const rawContent = item.querySelector('.raw-content');
                
                if (cleanButton && rawButton) {{
                    cleanButton.addEventListener('click', function() {{
                        cleanButton.classList.add('active');
                        rawButton.classList.remove('active');
                        cleanContent.classList.remove('hidden');
                        rawContent.classList.add('hidden');
                    }});
                    
                    rawButton.addEventListener('click', function() {{
                        rawButton.classList.add('active');
                        cleanButton.classList.remove('active');
                        rawContent.classList.remove('hidden');
                        cleanContent.classList.add('hidden');
                    }});
                }}
            }});
        }});
    </script>
</head>
<body>
    <h1>OWL处理结果</h1>
    
    <div class="button-container">
        <button id="new-task-button">开始新任务</button>
    </div>
    
    <div class="result-container">
        <div id="result-area">{result}</div>
    </div>
    
    <div class="history-container">
        <h2>历史记录</h2>
        {history}
    </div>
</body>
</html>
"""

# 自定义HTTP请求处理器
class ResultViewerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            # 返回HTML页面
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # 初始化当前结果为空
            global current_result
            current_result = "准备好接收新任务..."
            
            # 生成历史记录HTML，按时间倒序排列（最新的在最前面）
            history_html = ""
            # 对历史记录按时间戳倒序排序
            sorted_history = sorted(results_history, 
                                   key=lambda x: x.get('timestamp', ''), 
                                   reverse=True)
            
            for item in sorted_history:
                timestamp = item.get('timestamp', '')
                clean_result = item.get('result', '')
                raw_result = item.get('raw_result', clean_result)  # 如果没有原始结果，使用清理后的结果
                
                history_html += f"""
                <div class="history-item">
                    <h3>任务结果</h3>
                    <div class="timestamp">{timestamp}</div>
                    <div class="tab-buttons">
                        <button class="tab-button clean-tab active">清理后结果</button>
                        <button class="tab-button raw-tab">原始结果</button>
                    </div>
                    <div class="content clean-content">{clean_result}</div>
                    <div class="content raw-content hidden">{raw_result}</div>
                </div>
                """
            
            html = HTML_TEMPLATE.format(result=current_result, history=history_html, ws_port=7866)
            self.wfile.write(html.encode('utf-8'))
        else:
            super().do_GET()

# 添加一个函数用于更新结果
def update_result(data):
    """更新当前结果并广播给所有连接的客户端"""
    global current_result, results_history
    
    # 确保数据是字符串格式
    if isinstance(data, dict):
        if "content" in data:
            content = data["content"]
        else:
            # 将字典转换为字符串
            content = json.dumps(data, ensure_ascii=False)
    else:
        content = str(data)
    
    # 使用extract_owl_response清理结果
    clean_content = extract_owl_response(content)
    
    # 更新当前结果为清理后的内容
    current_result = clean_content
    
    # 添加到历史记录的开头，同时保存原始内容和清理后的内容
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results_history.insert(0, {
        "timestamp": timestamp, 
        "result": clean_content,
        "raw_result": content  # 保存原始结果
    })
    
    # 保存历史记录
    save_history()
    
    # 将清理后的结果放入队列，供WebSocket发送
    result_queue.put(clean_content)

def start_result_viewer():
    """启动结果查看器服务器"""
    # 加载历史记录
    load_history()
    
    # 使用不同的端口
    http_port = 7865  # 原来是7862
    ws_port = 7866    # 原来是7863
    
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

def start_websocket_server(port=7866):  # 原来是7863
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
