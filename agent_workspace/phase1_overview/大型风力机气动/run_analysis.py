#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1 Overview Analysis
风能气动领域整体概览分析
"""

import json
import re
from pathlib import Path
from zhipuai import ZhipuAI

# 配置
CONFIG = {
    "api_key": "3e5827ff22f5410bba5fb50930b8b023.lXqIbs9TN1iGi6Kb",
    "base_url": "https://open.bigmodel.cn/api/coding/paas/v4",
    "model": "glm-4-plus",
    "temperature": 0.7,
    "min_domains": 5,
    "max_domains": 10,
    "total_papers": 350
}

def load_data():
    """加载输入数据"""
    work_dir = Path(r"D:\xfs\phd\github项目\LiteratureHub\agent_workspace\phase1_overview\大型风力机气动")

    # 读取摘要文本
    with open(work_dir / "02_summaries_text.txt", "r", encoding="utf-8") as f:
        summaries = f.read()

    # 读取参数
    with open(work_dir / "03_params.json", "r", encoding="utf-8") as f:
        params = json.load(f)

    # 读取提示模板
    with open(work_dir / "04_prompt_template.txt", "r", encoding="utf-8") as f:
        prompt_template = f.read()

    return summaries, params, prompt_template, work_dir

def create_prompt(summaries, params, prompt_template):
    """创建完整的提示"""
    prompt = prompt_template.format(
        agent_results_summaries=summaries,
        min_domains=params["min_domains"],
        max_domains=params["max_domains"]
    )
    return prompt

def call_glm_api(prompt):
    """调用 GLM API"""
    client = ZhipuAI(
        api_key=CONFIG["api_key"],
    )

    print("正在调用 GLM-4 Plus API...")
    print(f"模型: {CONFIG['model']}")
    print(f"温度: {CONFIG['temperature']}")

    response = client.chat.completions.create(
        model=CONFIG["model"],
        messages=[
            {
                "role": "system",
                "content": "你是一位经验丰富的风能气动领域专家,擅长从大量文献中提取领域整体认知。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=CONFIG["temperature"],
        max_tokens=8000,
        top_p=0.9,
    )

    return response.choices[0].message.content

def extract_json_from_response(response_text):
    """从 API 响应中提取 JSON 内容"""
    # 尝试直接解析
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # 尝试提取代码块中的 JSON (优先级最高)
    json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
    if json_match:
        try:
            json_str = json_match.group(1).strip()
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON代码块解析失败: {e}")
            pass

    # 尝试提取 { } 之间的内容 (整个响应)
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError("无法从 API 响应中提取有效的 JSON 内容")

def validate_output(output):
    """验证输出格式"""
    required_fields = ["phase", "domains", "research_hotspots", "time_trends", "top_papers", "summary"]

    for field in required_fields:
        if field not in output:
            raise ValueError(f"缺少必需字段: {field}")

    # 验证 domains
    if not isinstance(output["domains"], list):
        raise ValueError("domains 必须是列表")

    if len(output["domains"]) < CONFIG["min_domains"] or len(output["domains"]) > CONFIG["max_domains"]:
        raise ValueError(f"领域数量必须在 {CONFIG['min_domains']} 到 {CONFIG['max_domains']} 之间")

    for domain in output["domains"]:
        if "all_papers" not in domain or "key_papers" not in domain:
            raise ValueError("每个领域必须包含 all_papers 和 key_papers")
        if len(domain["key_papers"]) < 10:
            raise ValueError(f"领域 {domain.get('name', 'Unknown')} 的 key_papers 数量不足 10 篇")

    # 验证 top_papers
    if len(output["top_papers"]) != 20:
        raise ValueError(f"top_papers 必须包含 20 篇文献，当前只有 {len(output['top_papers'])} 篇")

    # 统计 2023-2026 年的文献数量
    recent_papers = sum(1 for paper in output["top_papers"] if paper["year"] >= 2023)
    if recent_papers < 10:
        raise ValueError(f"Top 20 中至少需要 10 篇 2023-2026 年的文献，当前只有 {recent_papers} 篇")

    print("[OK] 输出验证通过！")
    return True

def save_output(output, work_dir):
    """保存输出结果"""
    output_file = work_dir / "05_agent_output.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ 输出已保存到: {output_file}")
    return output_file

def main():
    """主函数"""
    print("=" * 80)
    print("Phase 1 Overview Analysis - 风能气动领域整体概览分析")
    print("=" * 80)

    # 1. 加载数据
    print("\n[1/5] 加载输入数据...")
    summaries, params, prompt_template, work_dir = load_data()
    print(f"[OK] 文献数量: {CONFIG['total_papers']}")
    print(f"[OK] 领域数量范围: {params['min_domains']} - {params['max_domains']}")

    # 2. 创建提示
    print("\n[2/5] 创建分析提示...")
    prompt = create_prompt(summaries, params, prompt_template)
    print(f"[OK] 提示长度: {len(prompt)} 字符")

    # 3. 调用 API
    print("\n[3/5] 调用 GLM-4 Plus API 进行分析...")
    response_text = call_glm_api(prompt)
    print(f"[OK] 响应长度: {len(response_text)} 字符")

    # 保存原始响应
    raw_response_file = work_dir / "05_agent_output_raw.txt"
    with open(raw_response_file, "w", encoding="utf-8") as f:
        f.write(response_text)
    print(f"[OK] 原始响应已保存到: {raw_response_file}")

    # 4. 提取 JSON
    print("\n[4/5] 提取 JSON 结果...")
    try:
        output = extract_json_from_response(response_text)
        print(f"[OK] 成功提取 JSON")
    except ValueError as e:
        print(f"❌ JSON 提取失败: {e}")
        print("尝试保存原始响应...")
        raise

    # 5. 验证输出
    print("\n[5/5] 验证输出格式...")
    try:
        validate_output(output)
    except ValueError as e:
        print(f"❌ 输出验证失败: {e}")
        print("\n当前输出统计:")
        print(f"  - 领域数量: {len(output.get('domains', []))}")
        print(f"  - Top 文献数量: {len(output.get('top_papers', []))}")
        if 'domains' in output:
            for i, domain in enumerate(output['domains']):
                print(f"  - 领域 {i+1}: {len(domain.get('key_papers', []))} 篇关键文献")
        raise

    # 6. 保存输出
    output_file = save_output(output, work_dir)
    print(f"[OK] 输出已保存到: {output_file}")

    # 打印统计信息
    print("\n" + "=" * 80)
    print("分析完成！统计信息:")
    print("=" * 80)
    print(f"研究领域数量: {len(output['domains'])}")
    print(f"研究热点数量: {len(output['research_hotspots'])}")
    print(f"Top 文献数量: {len(output['top_papers'])}")

    recent_papers = sum(1 for paper in output['top_papers'] if paper['year'] >= 2023)
    print(f"  - 2023-2026 年文献: {recent_papers} 篇")

    print("\n领域分布:")
    for i, domain in enumerate(output['domains'], 1):
        print(f"  {i}. {domain['name']}: {domain['paper_count']} 篇文献")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
