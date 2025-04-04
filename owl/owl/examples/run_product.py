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
# ==========================

# 购物场景指令处理脚本 - run_product.py
# 该脚本用于在购物场景下，通过指定的指令处理不同类型的任务。主要功能是：
# - 自动识别指令类型并根据指令中关键词进行任务分类（推荐、比价、查找等）
# - 根据指令内容构建购物场景的智能体社会，并通过模型执行任务
# - 输出任务类型、任务提示和相关结果（如聊天历史、token计数等）
#
# 功能详解：
# 1. classify_instruction：识别输入的指令类型并进行分类（如推荐、比价、查找类等）。
# 2. construct_society：根据任务构建一个"购物"场景的智能体社会，包括设置用户和助手角色、工具包等。
# 3. process_instruction：主要处理输入的购物指令，进行任务类型分类、构建任务提示并调用智能体执行任务，最后返回结果。
# 4. main：脚本的主入口函数，接收输入指令，调用相关函数处理并输出结构化结果。
# ==========================

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
import logging
import time

# 确保使用UTF-8编码处理输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base_dir = pathlib.Path(__file__).parent.parent
env_path = base_dir / "owl" / ".env"
load_dotenv(dotenv_path=str(env_path))

set_log_level(level="DEBUG")

os.environ["PYTHONIOENCODING"] = "utf-8"

log_env = base_dir / "owl" / "product_log"
log_env.mkdir(parents=True, exist_ok=True)
log_file_path = log_env / "shopping_task_log.txt"
logging.basicConfig(filename=str(log_file_path), level=logging.INFO)

# 任务类型优先级：数值越小越优先
TASK_PRIORITIES = {
    "比价类": 1,
    "推荐类": 2,
    "查找类": 3,
    "评价类": 4,
    "图片提示类": 5,
    "通用购物类": 6,
}

def classify_instruction(instruction: str) -> list:
    task_types = set()

    if any(word in instruction for word in ["推荐", "类似", "品牌", "兴趣", "相关", "适合"]):
        task_types.add("推荐类")

    if any(word in instruction for word in ["对比", "哪个更便宜", "性价比", "区别", "比一下"]):
        task_types.add("比价类")

    if any(word in instruction for word in ["找", "寻找", "哪里有", "哪能买", "哪个网站"]):
        task_types.add("查找类")

    if any(word in instruction for word in ["好不好", "质量如何", "怎么样", "值不值", "用户评价"]):
        task_types.add("评价类")

    if any(word in instruction for word in ["图片", "图中", "截图", "视觉", "画面"]):
        task_types.add("图片提示类")

    if not task_types:
        task_types.add("通用购物类")

    # 排序
    sorted_tasks = sorted(task_types, key=lambda t: TASK_PRIORITIES.get(t, 99))
    return sorted_tasks


def construct_society(question: str) -> RolePlaying:
    """
    构建基于给定问题的智能体社会。

    参数:
        question (str): 要由智能体社会处理的任务或问题。

    返回:
        RolePlaying: 一个配置好的智能体社会，准备处理问题。
    """

    # 为不同组件创建模型,temperature设为0.7：	中等创造性，既能推理也有变化，专业推荐：temperature=0.5 更自由探索：temperature=0.9
    models = {
        "user": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_MAX,
            model_config_dict={"temperature": 0.7},
        ),
        "assistant": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_MAX,
            model_config_dict={"temperature": 0.7},
        ),
        "browsing": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_VL_MAX,
            model_config_dict={"temperature": 0.7},
        ),
        "planning": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_MAX,
            model_config_dict={"temperature": 0.7},
        ),
        "video": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_VL_MAX,
            model_config_dict={"temperature": 0.7},
        ),
        "image": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_VL_MAX,
            model_config_dict={"temperature": 0.7},
        ),
        "document": ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_VL_MAX,
            model_config_dict={"temperature": 0.7},
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
    ]

    # 购物专属角色设定
    user_agent_kwargs = {"model": models["user"]}

    assistant_agent_kwargs = {"model": models["assistant"],"tools": tools}

    # 配置任务参数
    enhanced_prompt = f"""
    {question}
    
    在处理购物相关任务时，请遵循以下指南：
    
    1. 信息获取策略：
       - 优先使用extract_document_content工具直接爬取网页内容，而不是模拟浏览行为
       - 对于电商平台，使用search_baidu或search_google获取目标URL
       - 使用DocumentProcessingToolkit处理结构化数据
    
    2. 产品分析要点：
       - 如果涉及产品图片，使用ask_question_about_image工具分析图片中的产品细节
       - 对于产品视频，使用ask_question_about_video工具提取关键信息
       - 提供产品规格、价格、评分等关键数据的结构化比较
    
    3. 回答格式要求：
       - 对于比价类任务，提供清晰的价格对比表格
       - 对于推荐类任务，列出3-5个推荐选项并说明理由
       - 对于每个推荐产品，提供简短的"优缺点速览"
       - 确保所有链接格式正确，便于用户访问
    
    4. 如遇到浏览器工具失败，请改用爬虫工具和搜索工具继续完成任务
    """
    
    task_kwargs = {
        "task_prompt": enhanced_prompt,
        "with_task_specify": False,
    }

    # 创建并返回智能体社会
    society = RolePlaying(
        **task_kwargs,
        user_role_name="product_user",
        user_agent_kwargs=user_agent_kwargs,
        assistant_role_name="product_assistant",
        assistant_agent_kwargs=assistant_agent_kwargs,
        output_language="Chinese",
    )

    return society

def log_task_details(task_types, instruction, answer):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    logging.info(f"时间: {timestamp}, 任务类型: {task_types}, 指令: {instruction}, 结果: {answer}")

def process_instruction(instruction: str):
    """
    处理从截图分析中获取的指令。

    参数:
        instruction (str): 要处理的指令。

    返回:
        dict: 包含处理结果和聊天历史的字典。
    """
    # 原先的指令加上识别的任务类型变成最终的任务prompt
    task_types = classify_instruction(instruction)
    type_string = " > ".join(task_types)
    task_prompt = f"[任务类型: {type_string}]\n{instruction}"

    print(f"\n识别出的任务类型（含优先级）: {type_string}")
    print(f"发送给智能体的任务提示:\n{task_prompt}\n")
    
    society = construct_society(task_prompt) #参数改成task_prompt而不是instruction
    answer, chat_history, token_count = run_society(society, 3)

    # 输出结果
    print(f"\033[94m指令: {instruction}\033[0m")
    print(f"\033[94m回答: {answer}\033[0m")
    
    # 日志记录
    log_task_details(type_string, instruction, answer)

    # 返回结构化数据
    return {
        "instruction": instruction,
        "answer": answer,
        # "task_types": task_types,
        # "task_prompt": task_prompt, 这两天是新加的返回值，不知道会不会影响原先的读取逻辑，暂且先注释掉以保持和原来逻辑一致
        "chat_history": chat_history,
        "token_count": token_count
    }


def main():
    """主函数，用于运行截图指令处理系统。"""
    
    instruction = sys.argv[1]
    print("this is run_product.py")
    
    # 处理指令并获取结构化结果
    result = process_instruction(instruction)
    
    # 将结果写入统一的结果文件
    result_file_path = os.path.join(base_dir, "owl_result.json")
    with open(result_file_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False)
    
    # 通知api_server结果已写入文件
    print(f"OWL_RESULT_FILE:{result_file_path}")


if __name__ == "__main__":
    main() 