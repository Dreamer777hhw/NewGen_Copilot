## Agent赋能电脑助理

### 项目结构

以下是有用的文件

```
owl/owl/
├── api_server.py
├── clean_owl_results.py
├── result_reviewer.py
├── start_screenshot_pipeline.py
├── examples/run_screenshot_instruction.py
└──  owl/utils/enhanced_role_playing.py

AI_platform/
├── content.js
├── content.css
├── manifest.json
├── popup/popup.html
└── popup/popup.js

```

### 安装依赖

可以按照owl官方网站中的要求进行配置。

### 关键文件说明

#### AI_platform 浏览器插件

AI_platform文件夹中的内容是用于在浏览器中运行的插件，主要功能是：

1. **网页截图捕获**：截取当前浏览的网页内容
2. **智能指令生成**：使用qwen多模态模型分析截图并自动生成指令，并且可以添加补充说明
3. **OWL系统集成**：将生成的指令发送到OWL多智能体系统处理
4. **用户交互界面**：提供简洁的操作界面，支持添加补充说明
5. **数据管理**：支持清除和导出收集的数据

插件工作流程：用户点击截屏按钮 → 捕获网页截图 → 模型分析生成指令 → 用户自行选择补充说明 → 发送到OWL系统 → 自动弹出查看处理结果。

#### OWL 多智能体系统

owl文件夹包含OWL多智能体系统的核心组件：

1. **api_server.py**：HTTP API服务器，接收浏览器插件的指令请求并返回处理结果
2. **result_reviewer.py**：结果查看器，通过WebSocket实时显示处理进度和结果
3. **start_screenshot_pipeline.py**：系统启动脚本，初始化整个处理流程（**是主程序**）
4. **examples/run_screenshot_instruction.py**：自定义的处理截图指令的脚本

OWL系统工作流程：接收指令 → 构建多智能体社会(enhanced_role_playing.py中定义了run_society函数，但是应该不用修改) → 智能体协作处理任务 → 生成结果 → 通过WebSocket广播结果会浏览器中。

### 使用方法

1. 安装依赖，可以按照owl官方网站中的要求进行配置。
2. 在chrome浏览器中打开网址'chrome://extensions/'，打开开发者模式，点击“加载已解压的扩展程序”，选择AI_platform文件夹。
3. 直接运行python start_screenshot_pipeline.py
4. 在浏览器中使用插件截屏并发送指令
5. 在浏览器中查看处理结果
