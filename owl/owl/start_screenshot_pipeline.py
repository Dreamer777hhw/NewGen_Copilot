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
import time
import pathlib

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

def main():
    """主函数，启动整个系统"""
    print("启动截图指令处理流程...")
    
    # 停止占用端口的进程
    kill_process_on_port(7860)
    kill_process_on_port(7861)
    kill_process_on_port(7862)
    kill_process_on_port(7863)
    
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