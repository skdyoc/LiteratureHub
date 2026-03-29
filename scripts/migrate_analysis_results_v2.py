"""
迁移 Wind-Aero 项目的分析结果到 LiteratureHub
遵循 all/ + categories/ 的分层结构（完全复刻 Page 1 模式）

执行方式：
    python scripts/migrate_analysis_results_v2.py

输出：
    - data/agent_results/all/ - 所有分析结果
    - data/agent_results/all/analysis_index.json - 状态索引
"""

import shutil
import json
from pathlib import Path
from datetime import datetime
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def migrate_to_all_structure():
    """迁移已有分析结果到 agent_results/all/"""

    # 源目录和目标目录
    source_dir = Path("D:/xfs/phd/github项目/Wind-Aero-Literature-Analysis-System/data/agent_results")
    target_all_dir = project_root / "data" / "agent_results" / "all"

    print("=" * 60)
    print("开始迁移分析结果到 LiteratureHub")
    print("=" * 60)
    print(f"源目录: {source_dir}")
    print(f"目标目录: {target_all_dir}")
    print()

    # 检查源目录
    if not source_dir.exists():
        print(f"❌ 源目录不存在: {source_dir}")
        return

    # 创建目标目录
    target_all_dir.mkdir(parents=True, exist_ok=True)

    # 初始化索引
    analysis_index = {
        "metadata": {
            "total_papers": 0,
            "analyzed_papers": 0,
            "pending_papers": 0,
            "partial_papers": 0,
            "last_updated": datetime.now().isoformat(),
            "source": "Wind-Aero-Literature-Analysis-System"
        },
        "papers": {}
    }

    # 统计信息
    total_count = 0
    completed_count = 0
    partial_count = 0
    error_count = 0

    # 遍历所有论文
    paper_dirs = [d for d in source_dir.iterdir() if d.is_dir()]

    print(f"发现 {len(paper_dirs)} 个论文文件夹")
    print()

    for i, paper_dir in enumerate(paper_dirs, 1):
        paper_id = paper_dir.name

        try:
            # 复制到 all/
            target_paper_dir = target_all_dir / paper_id

            # 如果目标已存在，先删除
            if target_paper_dir.exists():
                shutil.rmtree(target_paper_dir)

            shutil.copytree(paper_dir, target_paper_dir)

            # 验证并记录到索引
            analyzers = {}
            for analyzer in ["innovation", "motivation", "roadmap", "mechanism", "impact"]:
                json_file = target_paper_dir / f"{analyzer}.json"
                if json_file.exists():
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        analyzers[analyzer] = {
                            "status": "completed",
                            "file": f"{analyzer}.json",
                            "analyzed_at": datetime.fromtimestamp(json_file.stat().st_mtime).isoformat(),
                            "file_size": json_file.stat().st_size
                        }
                    except Exception as e:
                        print(f"  ⚠️ {analyzer}.json 读取失败: {e}")
                else:
                    # 缺少某个分析器
                    pass

            # 确定整体状态
            if len(analyzers) == 5:
                overall_status = "completed"
                completed_count += 1
            elif len(analyzers) > 0:
                overall_status = "partial"
                partial_count += 1
            else:
                overall_status = "empty"

            # 添加到索引
            analysis_index["papers"][paper_id] = {
                "paper_id": paper_id,
                "analyzers": analyzers,
                "overall_status": overall_status
            }

            total_count += 1

            # 每处理50个显示一次进度
            if i % 50 == 0 or i == len(paper_dirs):
                print(f"  进度: {i}/{len(paper_dirs)}")

        except Exception as e:
            print(f"❌ 迁移失败: {paper_id}, 错误: {e}")
            error_count += 1

    # 更新元数据
    analysis_index["metadata"]["total_papers"] = total_count
    analysis_index["metadata"]["analyzed_papers"] = completed_count
    analysis_index["metadata"]["partial_papers"] = partial_count
    analysis_index["metadata"]["pending_papers"] = 0  # 迁移的都是已有的

    # 保存索引
    index_file = target_all_dir / "analysis_index.json"
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_index, f, indent=2, ensure_ascii=False)

    # 打印统计
    print()
    print("=" * 60)
    print("迁移完成！")
    print("=" * 60)
    print(f"总论文数: {total_count}")
    print(f"完全完成: {completed_count}")
    print(f"部分完成: {partial_count}")
    print(f"错误: {error_count}")
    print()
    print(f"索引文件: {index_file}")
    print(f"数据目录: {target_all_dir}")
    print("=" * 60)


if __name__ == "__main__":
    migrate_to_all_structure()
