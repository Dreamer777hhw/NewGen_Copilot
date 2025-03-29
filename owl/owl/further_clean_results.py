import json
import re

def further_clean_results(input_file, output_file):
    """
    进一步处理已经清理过的OWL结果
    
    参数:
        input_file (str): 输入的JSON文件路径
        output_file (str): 输出的JSON文件路径
    """
    try:
        # 读取JSON文件
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 进一步处理每个结果
        refined_results = []
        for item in data:
            timestamp = item.get("timestamp", "")
            content = item.get("clean_result", "")
            
            # 移除重复的内容和模板指令
            if "<YOUR_SOLUTION>" in content:
                # 提取实际内容，去除模板指令
                actual_content = re.search(r'嵊泗县位于.*?(?=<YOUR_SOLUTION>|$)', content, re.DOTALL)
                if actual_content:
                    content = actual_content.group(0).strip()
            
            # 移除多余的转义字符和重复内容
            content = content.replace("\\n", "\n")
            
            # 如果内容中有重复段落，只保留一次
            paragraphs = content.split("\n\n")
            unique_paragraphs = []
            for p in paragraphs:
                if p and p not in unique_paragraphs:
                    unique_paragraphs.append(p)
            
            content = "\n\n".join(unique_paragraphs)
            
            refined_results.append({
                "timestamp": timestamp,
                "clean_result": content
            })
        
        # 保存处理后的结果
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(refined_results, f, ensure_ascii=False, indent=2)
            
        print(f"已成功进一步处理并保存到 {output_file}")
        
    except Exception as e:
        print(f"处理文件时出错: {e}")

# 使用示例
if __name__ == "__main__":
    input_file = "clean_results.json"
    output_file = "refined_results.json"
    further_clean_results(input_file, output_file)