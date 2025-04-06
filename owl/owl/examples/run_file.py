"""
    * @FileDescription: 文档助手脚本
    * @Author: 胡皓文
    * @Date: 2025-04-06
    * @LastEditors: 胡皓文
    * @LastEditTime: 2025-04-06
    * @Contributors: 胡皓文
"""

import sys
import os
import json
import io
from dotenv import load_dotenv
from camel.models import ModelFactory
from camel.toolkits import (
    CodeExecutionToolkit,
    ExcelToolkit,
    ImageAnalysisToolkit,
    SearchToolkit,
    VideoAnalysisToolkit,
    BrowserToolkit,
    FileWriteToolkit,
)
from camel.types import ModelPlatformType, ModelType
from camel.societies import RolePlaying

from owl.utils import run_society, DocumentProcessingToolkit

from camel.logger import set_log_level

import pathlib

# 确保使用UTF-8编码处理输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base_dir = pathlib.Path(__file__).parent.parent
env_path = base_dir / "owl" / ".env"
load_dotenv(dotenv_path=str(env_path))

set_log_level(level="DEBUG")

os.environ["PYTHONIOENCODING"] = "utf-8"


def construct_society(question: str) -> RolePlaying:
    """
    构建基于给定问题的智能体社会。

    参数:
        question (str): 要由智能体社会处理的任务或问题。

    返回:
        RolePlaying: 一个配置好的智能体社会，准备处理问题。
    """

    # 为不同组件创建模型
    models = {
        "user": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_MAX,
            model_config_dict={"temperature": 0},
        ),
        "assistant": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_MAX,
            model_config_dict={"temperature": 0},
        ),
        "browsing": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_VL_MAX,
            model_config_dict={"temperature": 0},
        ),
        "planning": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_MAX,
            model_config_dict={"temperature": 0},
        ),
        "video": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_VL_MAX,
            model_config_dict={"temperature": 0},
        ),
        "image": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_VL_MAX,
            model_config_dict={"temperature": 0},
        ),
        "document": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_VL_MAX,
            model_config_dict={"temperature": 0},
        ),
    }

    # 配置工具包
    tools = [
        *BrowserToolkit(
            headless=False,
            web_agent_model=models["browsing"],
            planning_agent_model=models["planning"],
            output_language="Chinese",
        ).get_tools(),
        *VideoAnalysisToolkit(model=models["video"]).get_tools(),
        *CodeExecutionToolkit(sandbox="subprocess", verbose=True).get_tools(),
        *ImageAnalysisToolkit(model=models["image"]).get_tools(),
        SearchToolkit().search_duckduckgo,
        SearchToolkit().search_google,
        SearchToolkit().search_wiki,
        SearchToolkit().search_baidu,
        *ExcelToolkit().get_tools(),
        *DocumentProcessingToolkit(model=models["document"]).get_tools(),
        *FileWriteToolkit(output_dir=os.getenv("FILE_PATH")).get_tools(),
    ]

    # 配置智能体角色和参数
    user_agent_kwargs = {"model": models["user"]}
    assistant_agent_kwargs = {"model": models["assistant"], "tools": tools}

    # 配置任务参数
    task_kwargs = {
        "task_prompt": question,
        "with_task_specify": False,
    }

    # 创建并返回智能体社会
    society = RolePlaying(
        **task_kwargs,
        user_role_name="user",
        user_agent_kwargs=user_agent_kwargs,
        assistant_role_name="assistant",
        assistant_agent_kwargs=assistant_agent_kwargs,
        output_language="Chinese",
    )

    return society


def process_instruction(instruction: str):
    """
    处理从截图分析中获取的指令。根据网页类型自动执行不同操作：
    - 股票/基金网页：爬取历史价格数据并生成Excel图表
    - 技术博客/文档：生成摘要并保存为MD或PDF
    - 新闻网页：生成新闻概要PDF
    - 其他类型网页：根据内容特征执行相应操作

    参数:
        instruction (str): 要处理的指令。

    返回:
        dict: 包含处理结果和聊天历史的字典。
    """
    url = None
    url_file_path = os.path.join(base_dir, "current_url.json")
    
    try:
        if os.path.exists(url_file_path):
            with open(url_file_path, 'r', encoding='utf-8') as f:
                url_data = json.load(f)
                url = url_data.get('url')
    except Exception as e:
        print(f"读取URL文件时出错: {str(e)}")

    if url:
        # 增强指令，根据URL类型提供更具体的处理建议，并限制爬虫调用
        enhanced_instruction = f"""我正在浏览这个网页：{url}
        
请先分析这个网页的类型和内容，然后根据以下规则处理。注意：为避免触发爬虫频率限制(429错误)，请遵循以下原则：
- 仅在绝对必要时调用一次extract_document_content工具
- 尽量从单次爬取的内容中提取所有需要的信息
- 如果遇到429错误，不要立即重试，而是尝试使用已获取的部分数据完成任务

根据网页类型执行以下操作：

1. 如果是股票/基金网页显示历史价格数据：
   - 仅调用一次extract_document_content工具爬取页面数据
   - 从爬取的内容中提取关键数据点(如最近10-20个交易日的数据)而非完整历史
   - 使用CodeExecutionToolkit处理数据并生成简洁的价格走势图，注意：
     * 在处理CSV文件时，先检查日期列的实际格式
     * 使用pd.read_csv()时避免直接指定date_parser，而是先读取为字符串
     * 读取后再使用pd.to_datetime()转换日期，设置format='mixed'或推断格式
   - 将精简数据保存为Excel文件，并创建基本可视化图表
   - 提供简要数据分析和趋势解读

2. 如果是技术博客或技术文档：
   - 仅调用一次extract_document_content工具爬取页面主要内容
   - 生成一份简洁的结构化摘要，包括核心观点和技术要点
   - 将摘要保存为Markdown文件(优先选择，因为生成更快)
   - 提供对技术内容的简要评价

3. 如果是新闻网页：
   - 仅调用一次extract_document_content工具爬取新闻主要内容
   - 生成新闻概要，包括关键5W1H要素
   - 将概要保存为简短的文本文件
   - 提供对新闻事件的简要分析

4. 如果是学术论文或研究报告：
   - 提取关键研究方法、结果和结论
   - 生成研究摘要并保存为PDF
   - 评估研究的创新点和局限性

5. 如果是产品介绍或电商页面：
   - 提取产品规格、价格和评价信息
   - 生成产品比较表格并保存为Excel
   - 提供购买建议

6. 如果是视频网站：
   - 提取视频标题、时长和评论
   - 生成视频内容概要
   - 推荐相关视频

7. 对于其他类型网页：
   - 仅调用一次extract_document_content工具爬取页面主要内容
   - 根据内容特征执行最简化的必要操作
   - 优先使用文本格式输出结果

请根据我的问题：{instruction}，结合网页类型执行最合适的操作，并提供分析结果。记住，宁可少做一些功能，也要确保不触发爬虫频率限制。
"""
        instruction = enhanced_instruction
    else:
        instruction = instruction

    society = construct_society(instruction)
    answer, chat_history, token_count = run_society(society, 3)

    # 输出结果
    print(f"\033[94m指令: {instruction}\033[0m")
    print(f"\033[94m回答: {answer}\033[0m")
    
    # 返回结构化数据
    return {
        "instruction": instruction,
        "answer": answer,
        "chat_history": chat_history,
        "token_count": token_count
    }


def main():
    """主函数，用于运行截图指令处理系统。"""
    
    instruction = sys.argv[1]
    print("this is run_screenshot_instruction.py")
    
    # 处理指令并获取结构化结果
    result = process_instruction(instruction)
    
    # 将结果写入临时文件
    result_file = "owl_result.json"
    result_file_path = os.path.join(base_dir, result_file)
    with open(result_file_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False)
    
    # 通知api_server结果已写入文件
    print(f"OWL_RESULT_FILE:{result_file}")


if __name__ == "__main__":
    main() 