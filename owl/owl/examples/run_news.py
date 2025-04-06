"""
    * @FileDescription: 聚焦事件脚本
    * @Author: 胡皓文
    * @Date: 2025-04-03
    * @LastEditors: 胡皓文
    * @LastEditTime: 2025-04-04
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
            model_type=ModelType.QWEN_PLUS,
            model_config_dict={"temperature": 0},
        ),
        "assistant": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_PLUS,
            model_config_dict={"temperature": 0},
        ),
        "browsing": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_VL_PLUS,
            model_config_dict={"temperature": 0},
        ),
        "planning": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_PLUS,
            model_config_dict={"temperature": 0},
        ),
        "video": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_VL_PLUS,
            model_config_dict={"temperature": 0},
        ),
        "image": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_VL_PLUS,
            model_config_dict={"temperature": 0},
        ),
        "document": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_VL_PLUS,
            model_config_dict={"temperature": 0},
        ),
    }

    # 增强指令，要求包含综合新闻分析和"省流"简报
    enhanced_question = f"""{question}

在回答中，请执行以下任务：
1. 搜集多个权威新闻来源对该事件的报道，确保至少包含3个不同来源
2. 对各个新闻报道进行客观评判，识别事实与观点的区别
3. 提供一份综合"省流"简报，包含：
   - 事件的客观发展过程和时间线
   - 相关背景信息和必要的上下文
   - 不同媒体对事件的报道角度对比
   - 网友/公众对该事件的主要观点和讨论热点
4. 对于重要的媒体内容：
   - 提供关键图片链接并简要描述内容
   - 提供重要视频链接并概述主要内容
5. 最后给出对信息可信度的评估和建议关注的要点

处理流程指南：
1. 使用search_google和search_baidu获取多个不同来源的相关报道
2. 对于每个获取到的URL，使用extract_document_content爬取内容
3. 分析各来源的内容，对比不同视角和报道侧重点
4. 通过搜索引擎或社交媒体相关功能，获取公众对事件的讨论
5. 整合所有信息，提供全面、客观且结构化的分析简报
"""

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
    ]

    # 配置智能体角色和参数
    user_agent_kwargs = {"model": models["user"]}
    assistant_agent_kwargs = {"model": models["assistant"], "tools": tools}

    # 配置任务参数
    task_kwargs = {
        "task_prompt": enhanced_question,
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
    society = construct_society(instruction)
    answer, chat_history, token_count = run_society(society, 5)

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


def read_instruction_from_file(file_path: str):
    """
    从文件中读取指令。

    参数:
        file_path (str): 指令文件的路径。

    返回:
        str: 读取的指令。
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"读取指令文件时出错: {str(e)}")
        return None


def main():
    """主函数，用于运行截图指令处理系统。"""
    
    instruction = sys.argv[1]
    print("this is run_news.py")
    
    # 处理指令并获取结构化结果
    result = process_instruction(instruction)
    
    # 将结果写入临时文件
    result_file = os.path.join(base_dir, "owl_result.json")
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False)
    
    # 通知api_server结果已写入文件
    print(f"OWL_RESULT_FILE:{result_file}")


if __name__ == "__main__":
    main() 