---
name: math-paper-analyzer
description: Analyze mathematical papers to extract and visualize mathematical structures (definitions, theorems, lemmas, propositions, corollaries, assumptions, remarks) and generate dependency graphs. Use when working with mathematical papers in PDF, LaTeX format, or from arXiv. Supports extracting mathematical entities, analyzing their relationships, and creating visual dependency graphs.
---

# Math Paper Analyzer

Analyze mathematical papers to extract definitions, theorems, lemmas, and other mathematical structures, then generate dependency relationship graphs.

## Supported Input Formats

- **PDF files** - Extracts text using `pdftotext`, falls back to OCR if needed
- **LaTeX files (.tex)** - Parses LaTeX environments directly
- **arXiv links/IDs** - Automatically downloads and analyzes

## Output

- **JSON report** - Structured data of all entities and relationships
- **Markdown report** - Human-readable summary
- **Dependency graph** - PNG visualization and GraphML export

## Usage

### Basic Usage

```python
# Import and use in Python
from scripts.math_analyzer import MathPaperAnalyzer

analyzer = MathPaperAnalyzer()
structure = analyzer.analyze("path/to/paper.pdf", output_dir="./output")
analyzer.generate_report(structure, output_dir="./output")
```

### Command Line

```bash
# Analyze PDF
python3 scripts/math_analyzer.py paper.pdf -o output/

# Analyze LaTeX
python3 scripts/math_analyzer.py paper.tex -o output/

# Analyze arXiv paper
python3 scripts/math_analyzer.py 2512.19344v1 -o output/
python3 scripts/math_analyzer.py https://arxiv.org/abs/2603.03027 -o output/
```

### With OCR for Scanned PDFs

For image-based or scanned PDFs, the tool automatically uses OCR via Tesseract.

## Extracted Entity Types

| Type | Color in Graph | Description |
|------|---------------|-------------|
| Definition | 🟢 Green | Mathematical definitions |
| Theorem | 🔵 Blue | Main theorems |
| Lemma | 🟠 Orange | Supporting lemmas |
| Proposition | 🟣 Purple | Propositions |
| Corollary | 🔴 Pink | Corollaries |
| Assumption | 🔴 Red | Assumptions |
| Remark | ⚫ Gray | Remarks |

## Output Files

After analysis, the following files are generated in the output directory:

- `analysis_report.json` - Complete structured data
- `analysis_report.md` - Human-readable report
- `dependency_graph.png` - Visual dependency graph (PNG image)
- `dependency_graph.html` - **Interactive HTML graph** with D3.js (NEW!)
- `dependency_graph.dot` - Graphviz DOT format (text-based graph description)
- `dependency_graph.mmd` - Mermaid diagram format (for Markdown/GitHub)
- `dependency_graph.graphml` - Graph data for Gephi/Cytoscape

### Interactive HTML Graph Features

The HTML graph (`dependency_graph.html`) includes:

🎮 **交互功能：**
- **拖拽节点** - 自由调整布局
- **缩放/平移** - 鼠标滚轮缩放，拖拽画布平移
- **悬停提示** - 显示节点详细信息
- **高亮连接** - 鼠标悬停时高亮相关边
- **搜索过滤** - 右上角搜索框快速定位节点
- **动画控制** - 暂停/播放力导向动画
- **重置视图** - 一键恢复初始状态

🎨 **视觉效果：**
- 深色渐变背景
- 彩色节点（按类型区分）
- 发光悬停效果
- 流畅的动画过渡

使用方法：直接在浏览器中打开 `dependency_graph.html`

### Using DOT Format

The DOT file can be converted to various formats using Graphviz:

```bash
# Convert to PDF
dot -Tpdf dependency_graph.dot -o graph.pdf

# Convert to SVG
dot -Tsvg dependency_graph.dot -o graph.svg

# Convert to PNG
dot -Tpng dependency_graph.dot -o graph.png
```

### Using Mermaid Format

The Mermaid file (`.mmd`) can be:
- Embedded directly in Markdown documents (GitHub/GitLab render it)
- Viewed with the Mermaid Live Editor: https://mermaid.live
- Used in documentation tools like Notion, Obsidian, etc.

Example:
```markdown
![Dependency Graph](dependency_graph.mmd)
```

Or inline in Markdown:
````markdown
```mermaid
[copy content from .mmd file]
```
````

## Dependencies

System packages:
- `poppler-utils` (for pdftotext)
- `tesseract-ocr` (for OCR)

Python packages:
- `networkx` - Graph processing
- `matplotlib` - Visualization
- `numpy` - Numerical operations

## Implementation Details

The analyzer works in these stages:

1. **Text Extraction**: 
   - PDFs: `pdftotext` for searchable PDFs, OCR fallback for scanned
   - LaTeX: Direct file parsing
   - arXiv: Downloads PDF automatically

2. **Entity Recognition**:
   - LaTeX: Parses `\begin{theorem}`, `\begin{definition}`, etc.
   - PDF: Pattern matching for "Theorem X", "Definition Y", etc.

3. **Dependency Analysis**:
   - Extracts `\label` and `\ref` commands
   - Builds citation graph between entities

4. **Visualization**:
   - Uses NetworkX and Matplotlib
   - Spring layout for node positioning
   - Color-coded by entity type

## Example Output

Statistics for a typical paper:
```
- Definitions: 17
- Theorems: 32
- Lemmas: 12
- Propositions: 16
- Corollaries: 4
- Assumptions: 4
- Remarks: 16
Total entities: 101
```
