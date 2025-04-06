## NewGEN Copilot

本项目中，我们的核心理念是应用最新的多智能协作体技术，进行一个其在浏览器端的部署实践。我们使用OWL多智能体系统，并将其部署在本地后台服务器，通过浏览器插件进行交互。因此使用到了开源的OWL系统，以及一种可被调用的API，包括大模型API，以及Google搜索API，FireCrawl爬虫API等。整体的系统结构都是我们自己设计并规定输入输出，并进行一定的修改。核心在于多智能体系统的构建，以及浏览器插件的构建。在理解OWL系统的运行逻辑后，我们对其进行了一定的修改，使其能够更好地适应我们的需求，并且将其作为我们的脚本的一部分，实行最为关键的指令处理操作。

注意在自己使用的时候，需要按照OWL的官网中的步骤配置好.env中的api_key，以及popup.js中的api_key。

### 项目结构

以下是原创或者修改的文件

```
owl/owl/
├── api_server.py
├── clean_owl_results.py
├── result_reviewer.py
├── start_screenshot_pipeline.py
├── examples/run_default.py
├── examples/run_file.py
├── examples/run_news.py
├── examples/run_product.py
├── examples/run_scholar.py
├── examples/run_travel.py
└── owl/utils/enhanced_role_playing.py

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
4. **examples/run_default.py**：默认的指令处理脚本
5. **examples/run_file.py**：文档处理脚本
6. **examples/run_news.py**：新闻处理脚本
7. **examples/run_product.py**：购物处理脚本
8. **examples/run_scholar.py**：学术论文处理脚本
9. **examples/run_travel.py**：旅行处理脚本

OWL系统工作流程：接收指令 → 构建多智能体社会(enhanced_role_playing.py中定义了run_society函数，但是应该不用修改) → 智能体协作处理任务 → 生成结果 → 通过WebSocket广播结果会浏览器中。

### 使用方法

1. 安装依赖，可以按照owl官方网站中的要求进行配置。
2. 在chrome浏览器中打开网址'chrome://extensions/'，打开开发者模式，点击“加载已解压的扩展程序”，选择AI_platform文件夹。
3. 直接运行python start_screenshot_pipeline.py
4. 在浏览器中使用插件截屏并发送指令
5. 在浏览器中查看处理结果
