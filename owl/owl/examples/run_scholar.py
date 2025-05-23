"""
    * @FileDescription: 学术论文脚本
    * @Author: 胡皓文
    * @Date: 2025-04-02
    * @LastEditors: 胡皓文
    * @LastEditTime: 2025-04-03
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
    ArxivToolkit,
    # GoogleScholarToolkit,
)
from camel.types import ModelPlatformType, ModelType
from camel.societies import RolePlaying
from owl.utils import run_society, DocumentProcessingToolkit
from camel.logger import set_log_level
import pathlib
import logging

for handler in logging.root.handlers:
    if isinstance(handler, logging.StreamHandler):
        handler.setStream(io.TextIOWrapper(handler.stream.buffer, encoding='utf-8'))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

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
        *FileWriteToolkit(output_dir="./").get_tools(),
        *ArxivToolkit().get_tools(),
        # *GoogleScholarToolkit().get_tools(),
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
    处理从截图分析中获取的指令。

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
    
    # 如果找到URL，修改指令
    if url:
        enhanced_instruction = f"""我正在阅读这篇学术文章：{url}

我的问题是：{instruction}

请先全面分析这篇文章的内容，然后针对我的问题提供详细、准确的解答。如果文章中有相关的数据、方法、结论或图表，请在回答中具体引用。
请提取文章中与我问题相关的关键图表，并在回答中包含这些图表的描述和解释。
如果有重要的数据表格，请将其整理成结构化格式。
如果我的问题需要更多背景知识来理解，请一并提供。
最后，请总结文章的创新点和局限性。"""
        print(f"\033[94m增强后的指令: {enhanced_instruction}\033[0m")
    else:
        enhanced_instruction = instruction
        print(f"\033[94m未找到URL，使用原始指令\033[0m")
    
    society = construct_society(enhanced_instruction)
    answer, chat_history, token_count = run_society(society, 3)
    
    # 提取图像和表格信息
    extracted_images = []
    extracted_tables = []

    # TODO：从chat_history中提取图像和表格信息

    # 输出结果
    print(f"\033[94m原始指令: {instruction}\033[0m")
    print(f"\033[94m回答: {answer}\033[0m")
    print(f"\033[94m提取的图像数量: {len(extracted_images)}\033[0m")
    print(f"\033[94m提取的表格数量: {len(extracted_tables)}\033[0m")
    
    # 返回结构化数据
    return {
        "instruction": instruction,
        "answer": answer,
        "chat_history": chat_history,
        "token_count": token_count,
        "extracted_images": extracted_images,
        "extracted_tables": extracted_tables,
        "article_url": url
    }


def main():
    """主函数，用于运行截图指令处理系统。"""
    
    instruction = sys.argv[1]
    print("this is run_scholar.py")
    
    result = process_instruction(instruction)
    
    # 创建一个更丰富的结果文件
    result_file = os.path.join(base_dir, "owl_result.json")
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False)
    
    # 通知api_server结果已写入文件
    print(f"OWL_RESULT_FILE:{result_file}")

if __name__ == "__main__":
    main() 