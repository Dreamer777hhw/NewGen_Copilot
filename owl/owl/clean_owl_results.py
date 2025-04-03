import json
import re

def extract_owl_response(owl_result):
    """
    从OWL输出结果中提取有用的回答部分
    
    参数:
        owl_result (str): OWL的原始输出结果
    
    返回:
        str: 提取的有用回答
    """
    # 处理可能的编码问题
    if isinstance(owl_result, bytes):
        owl_result = owl_result.decode('utf-8', errors='ignore')
    
    # 首先检查是否已经是一个干净的回答（没有特定格式的原始输出）
    if not any(pattern in owl_result for pattern in ["'role': 'assistant'", "回答:", "指令:", "2025-", "Traceback"]):
        # 如果看起来已经是干净的文本，直接返回
        return owl_result.strip()
    
    # 查找assistant角色的Solution内容
    assistant_solution_pattern = r"'role': 'assistant', 'content': 'Solution: (.*?)(?:Next request\.|')"
    solutions = re.findall(assistant_solution_pattern, owl_result, re.DOTALL)
    
    if solutions:
        # 清理解决方案内容
        cleaned_solutions = []
        for solution in solutions:
            # 移除转义字符
            solution = solution.replace('\\n', '\n').replace('\\', '')
            # 移除重复内容和模板指令
            if "<YOUR_SOLUTION>" in solution:
                # 尝试提取实际内容，不依赖于特定的内容
                actual_content = re.search(r'(.*?)(?=<YOUR_SOLUTION>|$)', solution, re.DOTALL)
                if actual_content:
                    solution = actual_content.group(1).strip()
            cleaned_solutions.append(solution.strip())
        
        # 合并所有找到的解决方案，去除重复内容
        unique_solutions = []
        for solution in cleaned_solutions:
            if solution and solution not in unique_solutions:
                unique_solutions.append(solution)
        
        return "\n\n".join(unique_solutions)
    
    # 如果没有找到Solution格式的回答，尝试查找其他可能的回答格式
    response_pattern = r'回答: (.*?)(?=\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}|$)'
    responses = re.findall(response_pattern, owl_result, re.DOTALL)
    
    if responses:
        response = responses[0].strip()
        # 如果回答部分包含日志信息，尝试进一步提取
        if "DEBUG" in response or "INFO" in response:
            # 尝试找到最后一个有意义的回答，不依赖于特定内容
            # 查找日志时间戳前的内容
            clean_response = re.search(r'(.*?)(?=\n\d{4}-\d{2}-\d{2}|$)', response, re.DOTALL)
            if clean_response:
                return clean_response.group(1).strip()
        return response
    
    # 检查是否包含错误信息
    if "Traceback" in owl_result or "Error" in owl_result:
        return "处理过程中出现错误，请查看原始输出了解详情。"
    
    # 尝试直接提取可能的回答内容，不依赖于特定内容
    # 查找第一个非空行开始的所有内容
    direct_answer = re.search(r'^\s*(.+(?:\n.+)*)', owl_result, re.MULTILINE)
    if direct_answer:
        return direct_answer.group(1).strip()
    
    # 如果都没找到，返回一个提示信息
    return "无法从输出中提取有用的回答内容"

def save_clean_response(input_file, output_file):
    """
    从JSON文件中读取OWL结果，提取有用部分并保存
    
    参数:
        input_file (str): 输入的JSON文件路径
        output_file (str): 输出的文本文件路径
    """
    try:
        # 读取JSON文件
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 处理每个结果
        clean_results = []
        for item in data:
            timestamp = item.get("timestamp", "未知时间")
            result = item.get("result", "")
            
            # 提取有用的回答
            clean_result = extract_owl_response(result)
            
            # 添加到结果列表
            clean_results.append({
                "timestamp": timestamp,
                "clean_result": clean_result
            })
        
        # 保存处理后的结果
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(clean_results, f, ensure_ascii=False, indent=2)
            
        print(f"已成功处理并保存到 {output_file}")
        
    except Exception as e:
        print(f"处理文件时出错: {e}")

# 使用示例
if __name__ == "__main__":
    input_file = "owl_results_history.json"
    output_file = "clean_results.json"
    save_clean_response(input_file, output_file)