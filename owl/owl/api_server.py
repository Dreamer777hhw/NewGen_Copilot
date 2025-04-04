# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.def do_POST(self):
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import os
import sys
import json
import http.server
import socketserver
import subprocess
import threading
import pathlib
import queue
import time
import socket
from clean_owl_results import extract_owl_response
from result_viewer import update_result, start_result_viewer

# 获取项目根目录
base_dir = pathlib.Path(__file__).parent.parent
examples_dir = base_dir / "examples"

# 保存指令的文件路径
instruction_file = str(base_dir / "owl" / "screenshot_instruction.txt")

# print(instruction_file, "api_server.py")

# 使用队列存储处理结果
result_queue = queue.Queue()
# 全局变量，用于存储处理状态
processing_status = {"status": "idle", "result": None}

class OWLRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        # 处理CORS预检请求
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        # 处理POST请求
        if self.path == '/api/process_instruction':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                # 解析JSON数据
                data = json.loads(post_data.decode('utf-8'))
                instruction = data.get('instruction')
                scene = data.get('scene')
                
                if not instruction:
                    self._send_error_response('未提供指令')
                    return

                # 重置处理状态
                global processing_status
                processing_status = {"status": "processing", "result": None}
                
                # 设置环境变量
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                
                # 在后台线程中运行OWL处理脚本
                thread = threading.Thread(target=run_owl_script, args=(instruction, scene))
                thread.daemon = True
                thread.start()
                
                # 发送成功响应
                self._send_success_response('指令已接收，正在处理中')
            
            except Exception as e:
                self._send_error_response(f'处理指令时出错: {str(e)}')
        elif self.path == '/api/save_url':
            # 新增API端点，用于保存当前URL
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                # 解析JSON数据
                data = json.loads(post_data.decode('utf-8'))
                url = data.get('url')
                
                if not url:
                    self._send_error_response('未提供URL')
                    return
                
                # 保存URL到JSON文件
                url_file_path = base_dir / "owl" / "current_url.json"
                with open(url_file_path, 'w', encoding='utf-8') as f:
                    json.dump({"url": url, "timestamp": time.time()}, f)
                
                # 发送成功响应
                self._send_success_response(f'URL已保存: {url}')
            
            except Exception as e:
                self._send_error_response(f'保存URL时出错: {str(e)}')
        elif self.path == '/api/get_result':
            try:
                # 直接从内存中获取结果
                
                if processing_status["status"] == "completed" and processing_status["result"]:
                    # 发送结果
                    self._send_json_response({
                        'status': 'success',
                        'result': processing_status["result"]
                    })
                else:
                    self._send_json_response({
                        'status': 'waiting',
                        'result': '处理中，请稍候...'
                    })
            
            except Exception as e:
                self._send_error_response(str(e))
        elif self.path == '/api/clear_instruction':
            # 清除当前指令和结果
            try:
                # 清空指令文件
                with open(instruction_file, 'w', encoding='utf-8') as f:
                    f.write('')
                
                # 重置处理状态
                
                processing_status = {"status": "idle", "result": None}
                
                # 返回成功响应
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response = {"success": True, "message": "指令已清除"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response = {"success": False, "error": str(e)}
                self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self._send_error_response('未知的API端点')
    
    def do_GET(self):
        # 处理GET请求
        if self.path == '/api/get_result':
            try:
                # 直接从内存中获取结果
                
                
                if processing_status["status"] == "completed" and processing_status["result"]:
                    # 发送结果
                    self._send_json_response({
                        'status': 'success',
                        'result': processing_status["result"]
                    })
                else:
                    self._send_json_response({
                        'status': 'waiting',
                        'result': '处理中，请稍候...'
                    })
            
            except Exception as e:
                self._send_error_response(str(e))
        else:
            self._send_error_response('未知的API端点')
    
    def _send_success_response(self, message):
        """发送成功响应"""
        response = json.dumps({'status': 'success', 'message': message})
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
    
    def _send_error_response(self, error_message, status_code=400):
        """发送错误响应"""
        response = json.dumps({'error': error_message})
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))

    def _send_json_response(self, data):
        """发送JSON响应"""
        response = json.dumps(data)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))

def read_stream(stream, output_list, prefix=""):
    """
    读取流并将输出添加到列表中。
    
    参数:
        stream: 要读取的流。
        output_list: 存储输出的列表。
        prefix: 输出前缀。
    """
    for line in iter(stream.readline, ''):
        try:
            print(f"{prefix}: {line.strip()}")
            output_list.append(line)
        except UnicodeEncodeError:
            print(f"{prefix}: [遇到解码错误]")
            # 尝试使用不同的编码处理
            try:
                safe_line = line.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                output_list.append(safe_line)
            except:
                # 如果仍然失败，添加一个占位符
                output_list.append("[内容包含无法显示的字符]")

def run_owl_script(instruction, scene):
    """
    运行OWL处理脚本来处理指令。
    
    参数:
        instruction (str): 要处理的指令。
        scene (str): 场景名称。
    """
    # 在函数开始处声明全局变量
    global processing_status
    
    try:
        # 重置处理状态，确保清除旧结果
        processing_status = {"status": "processing", "result": None}
        
        # 清空结果查看器中的旧结果 - 使用空的占位符消息
        try:
            update_result({
                "instruction": instruction,
                "content": "正在处理中，请稍候...",
            })
        except Exception as e:
            print(f"更新处理状态时出错: {str(e)}")
        
        # 清理主目录下的结果文件
        main_result_file = os.path.join(base_dir, "owl", "owl_result.json")
        if os.path.exists(main_result_file):
            try:
                os.remove(main_result_file)
                print(f"已清除旧的结果文件: {main_result_file}")
            except Exception as e:
                print(f"清除旧结果文件时出错: {str(e)}")
        
        # 根据场景选择不同的脚本
        if scene == "编程问题":
            script_name = "run_programming.py"
        elif scene == "学术论文":
            script_name = "run_scholar.py"
        elif scene == "聚焦事件":
            script_name = "run_news.py"
        elif scene == "产品页面":
            script_name = "run_product.py"
        else:
            script_name = "run_default.py"
        
        # 构建脚本路径
        script_path = os.path.join(base_dir, "owl", "examples", script_name)
        
        # 如果指定的脚本不存在，回退到默认脚本
        if not os.path.exists(script_path):
            print(f"警告: 脚本 {script_name} 不存在，使用默认脚本")
            script_path = os.path.join(base_dir, "owl", "examples", "run_default.py")
        
        print(f"执行脚本: {script_path}")
        print(f"当前工作目录: {os.getcwd()}")
        print(f"基础目录: {base_dir}")
        
        # 检查文件是否存在
        if not os.path.exists(script_path):
            error_msg = f"脚本文件不存在: {script_path}"
            print(error_msg)
            processing_status = {"status": "error", "result": error_msg}
            return
        
        # 设置编码环境变量
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # 运行脚本并实时捕获输出
        process = subprocess.Popen(
            [sys.executable, script_path, instruction],
            cwd=str(base_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            encoding='utf-8',
            env=env
        )
        
        # 实时读取输出
        stdout_output = []
        stderr_output = []
        
        # 创建线程读取输出
        stdout_thread = threading.Thread(
            target=read_stream, 
            args=(process.stdout, stdout_output, "脚本输出")
        )
        stderr_thread = threading.Thread(
            target=read_stream, 
            args=(process.stderr, stderr_output, "脚本错误")
        )
        
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()
        
        # 等待进程完成
        process.wait()
        stdout_thread.join()
        stderr_thread.join()
        
        stdout = "".join(stdout_output)
        stderr = "".join(stderr_output)
        
        # 检查进程返回码
        if process.returncode != 0:
            error_msg = f"脚本执行失败，返回码: {process.returncode}\n错误输出: {stderr}"
            print(error_msg)
            processing_status = {"status": "error", "result": error_msg}
            
            # 更新错误信息到结果查看器
            try:
                update_result(error_msg)
            except Exception as e:
                print(f"更新结果查看器时出错: {str(e)}")
            
            return
        
        # 从输出中提取结果文件
        result_data = None
        result_file = None
        
        for line in stdout.splitlines():
            if line.startswith("OWL_RESULT_FILE:"):
                result_file = line.replace("OWL_RESULT_FILE:", "", 1).strip()
                print(f"发现结果文件: {result_file}")
                if os.path.exists(result_file):
                    try:
                        with open(result_file, 'r', encoding='utf-8') as f:
                            result_data = json.load(f)
                        print(f"从文件读取JSON结果成功")
                        break
                    except Exception as e:
                        print(f"从文件读取JSON结果失败: {str(e)}")
        
        try:
            def clean_text(text):
                if isinstance(text, str):
                    return text.encode('utf-8', errors='ignore').decode('utf-8')
                return text
            
            # 处理结果数据
            if result_data:
                # 如果是结构化数据
                if isinstance(result_data, dict):
                    # 提取回答
                    answer = clean_text(result_data.get("answer", ""))
                    
                    # 提取聊天历史中的solution
                    chat_history = result_data.get("chat_history", [])
                    solutions = []
                    
                    for message in chat_history:
                        if message.get("assistant"):
                            solutions.append(message.get("assistant"))
                            # 移除"Next request."等结束语
                            if "Next request." in solutions[-1]:
                                solutions[-1] = solutions[-1].split("Next request.", 1)[0]

                    # 合并所有solution
                    combined_solution = "\n\n".join(solutions)
                    
                    # 如果answer为空或不完整，使用combined_solution
                    if not answer or len(answer) < len(combined_solution):
                        answer = combined_solution
                    
                    article_url = result_data.get("article_url", "")
                    all_rounds = result_data.get("all_rounds", [])
                    
                    # 创建结构化结果
                    structured_result = {
                        "instruction": instruction,
                        "answer": answer,
                        "article_url": article_url,
                        "all_rounds": all_rounds,
                        "chat_history": chat_history
                    }
                    
                    # 更新结果查看器
                    update_result(structured_result)
                    
                    # 更新处理状态
                    processing_status = {
                        "status": "completed", 
                        "result": answer,
                        "structured_result": structured_result
                    }
                else:
                    # 如果是简单数据
                    result = f"指令: {instruction}\n\n回答: {clean_text(result_data)}"
                    clean_result = extract_owl_response(result)
                    
                    processing_status = {"status": "completed", "result": clean_result, "raw_result": result}
                    update_result(clean_result)
            else:
                # 如果没有结构化数据，从stdout中提取
                result = clean_text(f"指令: {instruction}\n\n回答: ")
                
                # 从输出中提取回答部分
                if stdout:
                    answer_found = False
                    answer_content = []
                    
                    for line in stdout.splitlines():
                        if "Answer:" in line and not answer_found:
                            answer_found = True
                            answer_part = line.split("Answer:", 1)[1].strip()
                            if answer_part:
                                answer_content.append(answer_part)
                        elif answer_found:
                            answer_content.append(line.strip())
                    
                    if answer_content:
                        result += "\n".join(answer_content)
                    else:
                        # 如果没有找到Answer标记，则使用整个stdout
                        result += stdout
                
                if "回答:" in result and len(result.split("回答:", 1)[1].strip()) == 0:
                    result += f"\n\n{stdout}"
                    if stderr:
                        result += f"\n\n错误输出:\n{stderr}"
                
                clean_result = extract_owl_response(result)
                
                # 创建结构化结果
                structured_result = {
                    "instruction": instruction,
                    "answer": clean_result,
                    "extracted_images": [],  # 添加空的图像列表
                    "extracted_tables": [],  # 添加空的表格列表
                    "stdout": stdout,
                    "stderr": stderr
                }
                
                processing_status = {
                    "status": "completed", 
                    "result": clean_result, 
                    "raw_result": result,
                    "structured_result": structured_result
                }
                
                # 更新结果查看器 - 传递完整的结构化对象
                update_result(structured_result)
            
            print(f"已更新结果到查看器")
                
        except Exception as e:
            error_msg = f"处理结果时出错: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            
            processing_status = {"status": "error", "result": error_msg}
            
            # 更新错误信息到结果查看器
            try:
                update_result(error_msg)
            except Exception as e:
                print(f"更新结果查看器时出错: {str(e)}")

    except Exception as e:
        error_msg = f"运行OWL脚本时出错: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        
        # 更新处理状态为错误
        processing_status = {"status": "error", "result": error_msg}
        
        # 同样更新错误信息到结果查看器
        try:
            update_result(error_msg)
        except Exception as e:
            print(f"更新结果查看器时出错: {str(e)}")

    return processing_status

def is_port_in_use(port):
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_process_on_port(port):
    """终止占用指定端口的进程"""
    try:
        if sys.platform.startswith('win'):
            # Windows平台
            output = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True).decode()
            if output:
                # 提取PID
                for line in output.splitlines():
                    if f":{port}" in line and "LISTENING" in line:
                        pid = line.strip().split()[-1]
                        try:
                            subprocess.check_output(f'taskkill /F /PID {pid}', shell=True)
                            print(f"已终止占用端口 {port} 的进程 (PID: {pid})")
                            return True
                        except:
                            print(f"无法终止进程 {pid}")
        else:
            # Linux/Mac平台
            output = subprocess.check_output(f'lsof -i :{port} -t', shell=True).decode()
            if output:
                pid = output.strip()
                try:
                    subprocess.check_output(f'kill -9 {pid}', shell=True)
                    print(f"已终止占用端口 {port} 的进程 (PID: {pid})")
                    return True
                except:
                    print(f"无法终止进程 {pid}")
        return False
    except:
        return False

def main():
    """启动API服务器"""
    port = 7861
    handler = OWLRequestHandler
    global processing_status
    
    # 检查并释放需要的端口
    ports_to_check = [7861, 7865, 7866]
    
    for check_port in ports_to_check:
        if is_port_in_use(check_port):
            print(f"端口 {check_port} 已被占用，尝试释放...")
            if kill_process_on_port(check_port):
                print(f"端口 {check_port} 已释放")
                # 等待端口完全释放
                time.sleep(1)
            else:
                print(f"警告: 无法释放端口 {check_port}，可能会导致服务启动失败")
    
    # 启动结果查看器服务器
    try:
        viewer_thread = threading.Thread(target=start_result_viewer)
        viewer_thread.daemon = True
        viewer_thread.start()
        # 给结果查看器一些时间来启动
        time.sleep(2)
    except Exception as e:
        print(f"启动结果查看器服务器时出错: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 启动API服务器
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"API服务器已启动，监听端口{port}...")
            httpd.serve_forever()
    except OSError as e:
        if "地址已经被使用" in str(e) or "Address already in use" in str(e):
            print(f"错误: 端口 {port} 已被占用，无法启动API服务器")
            print("请尝试手动终止占用该端口的进程，或者使用不同的端口")
        else:
            print(f"启动API服务器时出错: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 