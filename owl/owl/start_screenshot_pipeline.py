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
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import os
import sys
import subprocess
import threading
import time
import pathlib
from result_viewer import start_result_viewer, update_result, current_result
import json
from datetime import datetime
from clean_owl_results import extract_owl_response

# 获取项目根目录
base_dir = pathlib.Path(__file__).parent.parent

def start_api_server():
    """启动API服务器"""
    api_script = os.path.join(base_dir, "owl", "api_server.py")
    subprocess.Popen([sys.executable, api_script])

def kill_process_on_port(port):
    """杀死占用指定端口的进程"""
    try:
        if sys.platform.startswith('win'):
            # Windows系统
            output = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True).decode()
            if output:
                # 提取PID
                for line in output.splitlines():
                    if f':{port}' in line and ('LISTENING' in line or 'ESTABLISHED' in line):
                        parts = line.strip().split()
                        pid = parts[-1]
                        try:
                            # 杀死进程
                            subprocess.call(f'taskkill /F /PID {pid}', shell=True)
                            print(f"已终止占用端口 {port} 的进程 (PID: {pid})")
                        except:
                            print(f"无法终止进程 (PID: {pid})")
        else:
            # Linux/Mac系统
            output = subprocess.check_output(f'lsof -i :{port} -t', shell=True).decode()
            if output:
                for pid in output.splitlines():
                    try:
                        # 杀死进程
                        subprocess.call(f'kill -9 {pid}', shell=True)
                        print(f"已终止占用端口 {port} 的进程 (PID: {pid})")
                    except:
                        print(f"无法终止进程 (PID: {pid})")
    except subprocess.CalledProcessError:
        # 没有找到占用该端口的进程
        pass
    except Exception as e:
        print(f"检查端口占用时出错: {str(e)}")

def process_and_save_results(result, results_dir="owl_results"):
    """
    处理OWL结果并保存到文件
    
    参数:
        result (str): OWL处理的原始结果
        results_dir (str): 结果保存目录
    """
    # 确保结果目录存在
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    
    # 清理结果
    clean_result = extract_owl_response(result)
    
    # 获取当前时间作为时间戳
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 创建结果对象
    result_obj = {
        "timestamp": timestamp,
        "result": result,
        "clean_result": clean_result
    }
    
    # 保存到历史记录文件
    history_file = os.path.join(results_dir, "owl_results_history.json")
    
    # 读取现有历史记录
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            history = []
    else:
        history = []
    
    # 添加新结果
    history.append(result_obj)
    
    # 保存更新后的历史记录
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    # 同时保存清理后的结果到单独的文件
    clean_results_file = os.path.join(results_dir, "clean_results.json")
    
    # 读取现有清理结果
    if os.path.exists(clean_results_file):
        try:
            with open(clean_results_file, 'r', encoding='utf-8') as f:
                clean_history = json.load(f)
        except:
            clean_history = []
    else:
        clean_history = []
    
    # 添加新的清理结果
    clean_history.append({
        "timestamp": timestamp,
        "clean_result": clean_result
    })
    
    # 保存更新后的清理结果
    with open(clean_results_file, 'w', encoding='utf-8') as f:
        json.dump(clean_history, f, ensure_ascii=False, indent=2)
    
    return clean_result

def main():
    """主函数，启动整个系统"""
    print("启动截图指令处理流程...")
    
    # 停止占用端口的进程
    kill_process_on_port(7860)  # 旧的API服务器端口
    kill_process_on_port(7861)  # 新的API服务器端口
    kill_process_on_port(7862)  # 结果查看器端口
    kill_process_on_port(7863)  # WebSocket端口
    
    # 等待端口完全释放
    time.sleep(2)
    
    # 启动API服务器
    start_api_server()
    
    # 等待API服务器完全启动
    time.sleep(1)

    print("系统已启动，等待处理截图指令...")
    print("请使用Chrome扩展捕获截图并生成指令")
    
    try:
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("系统已停止")

if __name__ == "__main__":
    main() 