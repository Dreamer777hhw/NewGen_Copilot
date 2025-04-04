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

# 加载历史记录
def load_history():
    """加载历史记录"""
    global results_history
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
    </div>
    
    <div class="result-container">
        <div id="result-area">{result}</div>
    </div>
    
    <div class="history-container">
        <div class="history-header">
            <h2>历史记录</h2>
            <button id="clear-history-button" style="background-color: #f44336;">清除历史记录</button>
        </div>
        {history}
    </div>
</body>
</html>
"""

# 自定义HTTP请求处理器
class ResultViewerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
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
                
                # 添加指令显示区域
                instruction_html = ""
                if instruction and instruction.strip():
                    # 对指令进行HTML转义，防止XSS攻击
                    instruction = instruction.replace('<', '&lt;').replace('>', '&gt;')
                    instruction_html = f'<div class="instruction"><strong>指令:</strong> <em>{instruction}</em></div>'
                
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
        results_history.insert(0, {
            "timestamp": timestamp, 
            "result": clean_content,
            "instruction": instruction,
            "article_url": article_url
        })
 
    # 保存历史记录
    save_history()
    
    # 将更新后的结果放入队列，供WebSocket发送
    result_queue.put(current_result)

def start_result_viewer():
    """启动结果查看器服务器"""
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
    save_history()
    print("历史记录已清除")
