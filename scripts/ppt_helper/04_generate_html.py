"""
HTML 生成器脚本

职责：基于 Phase 3 的 JSON 输出生成符合博士论文汇报风格的 HTML 文件
"""

import sys
import io
import json
from pathlib import Path
from typing import Dict, Any, List

# Windows UTF-8 支持
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class HTMLGenerator:
    """HTML 生成器 - 基于参考模板的配色和样式"""

    # 配色方案（基于参考模板）
    COLORS = {
        "primary": "#0d4c92",        # 主色调（深蓝）
        "secondary": "#174a8b",      # 次要色（中蓝）
        "accent": "#2f80ed",         # 强调色（亮蓝）
        "accent_light": "#56ccf2",   # 浅蓝
        "background_start": "#eef4ff",  # 背景渐变起始
        "background_end": "#f9fbff",    # 背景渐变结束
        "white": "#ffffff",          # 白色
        "tag_bg": "#eaf3ff",          # 标签背景
        "tag_text": "#1a5fb4",       # 标签文字
        "text_main": "#1f2d3d",       # 主要文字
        "text_secondary": "#22324a",  # 次要文字
    }

    def __init__(self, output_dir: str):
        """
        初始化 HTML 生成器

        Args:
            output_dir: HTML 文件输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_css(self) -> str:
        """生成通用 CSS 样式"""
        return f"""
body {{
    margin: 0;
    padding: 24px;
    font-family: "Microsoft YaHei", Arial, sans-serif;
    background: linear-gradient(135deg, {self.COLORS['background_start']}, {self.COLORS['background_end']});
    color: {self.COLORS['text_main']};
}}
.wrap {{
    max-width: 1400px;
    margin: 0 auto;
}}
.title {{
    font-size: 34px;
    font-weight: 800;
    color: {self.COLORS['primary']};
    margin-bottom: 20px;
    text-align: center;
}}
.top-box {{
    background: {self.COLORS['white']};
    border-radius: 18px;
    padding: 18px 24px;
    box-shadow: 0 8px 24px rgba(16, 59, 115, 0.08);
    border-left: 8px solid {self.COLORS['accent']};
    margin-bottom: 22px;
}}
.top-box .main {{
    font-size: 22px;
    font-weight: 700;
    color: {self.COLORS['secondary']};
    text-align: center;
    line-height: 1.8;
}}
.grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 18px;
}}
.card {{
    background: {self.COLORS['white']};
    border-radius: 18px;
    padding: 18px;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.06);
    position: relative;
    min-height: 260px;
}}
.card:before {{
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    height: 6px;
    border-radius: 18px 18px 0 0;
    background: linear-gradient(90deg, {self.COLORS['accent']}, {self.COLORS['accent_light']});
}}
.card h3 {{
    margin: 10px 0 14px;
    font-size: 22px;
    color: {self.COLORS['secondary']};
}}
.tag {{
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    background: {self.COLORS['tag_bg']};
    color: {self.COLORS['tag_text']};
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 10px;
}}
ul {{
    margin: 0;
    padding-left: 18px;
    line-height: 1.9;
    font-size: 16px;
}}
.bottom {{
    margin-top: 22px;
    background: {self.COLORS['primary']};
    color: {self.COLORS['white']};
    padding: 18px 22px;
    border-radius: 18px;
    font-size: 20px;
    font-weight: 700;
    text-align: center;
    box-shadow: 0 8px 24px rgba(16, 59, 115, 0.18);
}}
"""

    def generate_part1_html(self, slides: List[Dict[str, Any]]) -> str:
        """生成 Part 1: 课题研究综述 HTML"""
        html_parts = []

        for i, slide in enumerate(slides, 1):
            title = slide.get('title', f'第{i}页')
            bullets = slide.get('bullets', [])
            notes = slide.get('notes', '')

            html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title}</title>
<style>
{self.generate_css()}
</style>
</head>
<body>
<div class="wrap">
    <div class="title">{title}</div>
"""

            # 添加顶部框（如果有 notes）
            if notes:
                html += f"""
    <div class="top-box">
        <div class="main">
            {notes}
        </div>
    </div>
"""

            # 添加卡片网格
            if bullets:
                html += '    <div class="grid">\n'

                # 每个要点一个卡片
                for bullet in bullets:
                    html += f"""        <div class="card">
            <h3>{bullet}</h3>
        </div>
"""

                # 补齐到4的倍数
                while len(bullets) % 4 != 0:
                    html += f"""        <div class="card">
            <h3>待补充</h3>
        </div>"""
                    bullets.append("")

                html += '    </div>\n'

            # 添加底部总结
            if i == len(slides):
                html += """
    <div class="bottom">
        总结：本部分系统梳理了领域研究的整体发展脉络，明确了研究背景、意义及国内外研究现状
    </div>
"""

            html += """
</div>
</body>
</html>
"""
            html_parts.append(html)

        return html_parts

    def generate_part2_html(self, slides: List[Dict[str, Any]]) -> str:
        """生成 Part 2: 课题创新性 HTML"""
        html_parts = []

        for i, slide in enumerate(slides, 1):
            title = slide.get('title', f'第{i}页')
            bullets = slide.get('bullets', [])

            html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
{self.generate_css()}
.row {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 22px;
    margin-bottom: 22px;
}}
.panel {{
    background: {self.COLORS['white']};
    border-radius: 20px;
    padding: 22px;
    box-shadow: 0 10px 26px rgba(0, 0, 0, 0.06);
}}
.panel h2 {{
    margin: 0 0 16px 0;
    font-size: 24px;
    color: {self.COLORS['primary']};
}}
.sub {{
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 12px;
    background: {self.COLORS['tag_bg']};
    color: {self.COLORS['tag_text']};
}}
</style>
</head>
<body>
<div class="wrap">
    <div class="title">{title}</div>
"""

            # 添加内容
            if bullets:
                # 分成两列显示
                half = (len(bullets) + 1) // 2
                first_col = bullets[:half]
                second_col = bullets[half:]

                html += '    <div class="row">\n'

                # 第一列
                if first_col:
                    html += '        <div class="panel">\n'
                    for bullet in first_col:
                        html += f'            <li>{bullet}</li>\n'
                    html += '        </div>\n'

                # 第二列
                if second_col:
                    html += '        <div class="panel">\n'
                    for bullet in second_col:
                        html += f'            <li>{bullet}</li>\n'
                    html += '        </div>\n'

                html += '    </div>\n'

            # 添加底部总结
            if i == len(slides):
                html += """
    <div class="bottom">
        总结：本部分明确了课题的创新性，包括新现象、新方法、新对象的发现与分析
    </div>
"""

            html += """
</div>
</body>
</html>
"""
            html_parts.append(html)

        return html_parts

    def generate_part3_html(self, slides: List[Dict[str, Any]]) -> str:
        """生成 Part 3: 思路及方法 HTML"""
        # 使用与 Part 2 相似的双列布局
        return self.generate_part2_html(slides)

    def generate_part4_html(self, slides: List[Dict[str, Any]]) -> str:
        """生成 Part 4: 后续工作完成 HTML"""
        # 使用与 Part 1 相似的4列布局
        return self.generate_part1_html(slides)

    def generate_all_html(self, ppt_content: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        生成所有部分的 HTML 文件

        Args:
            ppt_content: Phase 3 的 JSON 输出

        Returns:
            各部分生成的 HTML 文件路径字典
        """
        results = {}

        # Part 1: 课题研究综述
        part1_slides = ppt_content.get('ppt_content', {}).get('part1_research_review', {}).get('slides', [])
        if part1_slides:
            part1_htmls = self.generate_part1_html(part1_slides)
            part1_dir = self.output_dir / "part1_research_review"
            part1_dir.mkdir(parents=True, exist_ok=True)

            for i, html in enumerate(part1_htmls, 1):
                output_file = part1_dir / f"page{i:02d}_research_review.html"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(html)

            results['part1'] = list(part1_dir.glob('*.html'))

        # Part 2: 课题创新性
        part2_slides = ppt_content.get('ppt_content', {}).get('part2_innovation', {}).get('slides', [])
        if part2_slides:
            part2_htmls = self.generate_part2_html(part2_slides)
            part2_dir = self.output_dir / "part2_innovation"
            part2_dir.mkdir(parents=True, exist_ok=True)

            for i, html in enumerate(part2_htmls, 1):
                output_file = part2_dir / f"page{i:02d}_innovation.html"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(html)

            results['part2'] = list(part2_dir.glob('*.html'))

        # Part 3: 思路及方法
        part3_slides = ppt_content.get('ppt_content', {}).get('part3_methodology', {}).get('slides', [])
        if part3_slides:
            part3_htmls = self.generate_part3_html(part3_slides)
            part3_dir = self.output_dir / "part3_methodology"
            part3_dir.mkdir(parents=True, exist_ok=True)

            for i, html in enumerate(part3_htmls, 1):
                output_file = part3_dir / f"page{i:02d}_methodology.html"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(html)

            results['part3'] = list(part3_dir.glob('*.html'))

        # Part 4: 后续工作完成
        part4_slides = ppt_content.get('ppt_content', {}).get('part4_future_work', {}).get('slides', [])
        if part4_slides:
            part4_htmls = self.generate_part4_html(part4_slides)
            part4_dir = self.output_dir / "part4_future_work"
            part4_dir.mkdir(parents=True, exist_ok=True)

            for i, html in enumerate(part4_htmls, 1):
                output_file = part4_dir / f"page{i:02d}_future_work.html"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(html)

            results['part4'] = list(part4_dir.glob('*.html'))

        return results


def main():
    """主函数"""
    import sys
    import yaml

    print("=" * 60)
    print("📊 HTML 生成器".center(60))
    print("=" * 60)
    print()

    try:
        # 加载配置
        config_file = Path("config/ppt_helper_config.yaml")
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 读取 Phase 3 的 JSON 输出
        json_file = Path(config['data_paths']['processed_data']) / "final_ppt_content.json"

        if not json_file.exists():
            print(f"❌ JSON 文件不存在: {json_file}")
            print("💡 请先运行 Phase 3: python scripts/ppt_helper/03_summary.py")
            return

        with open(json_file, 'r', encoding='utf-8') as f:
            ppt_content = json.load(f)

        # 创建 HTML 生成器
        output_dir = Path(config['data_paths']['processed_data']) / "html_output"
        generator = HTMLGenerator(str(output_dir))

        print("🎨 开始生成 HTML 文件...")

        # 生成所有 HTML
        results = generator.generate_all_html(ppt_content)

        # 显示结果
        print()
        print("✅ HTML 文件生成完成！")
        print()
        print("📁 输出位置：")
        for part_name, html_files in results.items():
            print(f"   - {part_name}: {len(html_files)} 个文件")
            for html_file in html_files:
                print(f"     * {html_file.name}")

        print()
        print("💡 提示：可以在浏览器中打开 HTML 文件查看效果")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
