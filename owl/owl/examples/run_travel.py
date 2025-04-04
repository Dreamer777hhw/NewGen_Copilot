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
    GoogleMapsToolkit,
    WeatherToolkit,
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
        *FileWriteToolkit(output_dir="./").get_tools(),
        *GoogleMapsToolkit().get_tools(),
        *WeatherToolkit().get_tools(),
    ]

    # 旅行助手提示词
    travel_prompt = """
在回答中，请注意以下要点：
1. 为用户提供[旅行目的地]的全面旅行攻略，针对[日期]出发的行程安排
2. 推荐景点，并提供详细介绍
3. 提供最佳路线规划和交通建议
4. 推荐符合用户需求的住宿选择，包括位置、价格范围和设施

处理流程指南：
1. 首先使用搜索工具search_google获取目的地的最新旅游信息
2. 使用google_maps工具规划最佳路线和交通方案
3. 使用weather_toolkit查询目的地所属地级市在指定日期的天气预报
4. 对于推荐的景点，使用extract_document_content获取详细信息，并用ImageAnalysisToolkit分析相关图片
5. 为用户提供住宿建议，包括酒店、民宿或其他住宿选择
6. 整合所有信息，提供一份结构化的旅行攻略，包括：
   - 行程概览（天数安排）
   - 必游景点详情（开放时间、门票、特色）
   - 交通方案（如何到达及当地交通）
   - 住宿推荐（位置、价格、设施）
   - 美食推荐（当地特色）
   - 旅行贴士（天气、穿着、文化习俗）
   - 预算估算

7. 如有相关图片，使用ask_question_about_image工具分析并提供描述
8. 为每个部分提供"省流版"概述，帮助用户快速了解信息
"""

    # 将旅行提示词添加到用户问题中
    enhanced_question = f"{question}\n\n{travel_prompt}"

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