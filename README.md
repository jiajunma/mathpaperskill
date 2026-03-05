# Math Paper Analyzer

数学论文分析工具 - 自动提取定义、定理、引理等数学结构，并生成依赖关系图。

## 功能

- **多格式输入支持**：PDF、LaTeX (.tex)、arXiv 链接
- **实体提取**：自动识别并提取
  - 定义 (Definition)
  - 定理 (Theorem)
  - 引理 (Lemma)
  - 命题 (Proposition)
  - 推论 (Corollary)
  - 假设 (Assumption)
  - 备注 (Remark)
- **依赖关系分析**：分析实体间的引用关系
- **可视化输出**：生成依赖关系图（PNG 和 GraphML 格式）
- **结构化报告**：JSON 和 Markdown 格式

## 安装

### 系统依赖

```bash
# Ubuntu/Debian
sudo apt-get install -y poppler-utils tesseract-ocr tesseract-ocr-eng

# macOS
brew install poppler tesseract
```

### Python 依赖

```bash
pip3 install -r requirements.txt
```

## 使用方法

### 分析 PDF 文件

```bash
python3 src/math_analyzer.py path/to/paper.pdf -o output/
```

### 分析 LaTeX 文件

```bash
python3 src/math_analyzer.py path/to/paper.tex -o output/
```

### 分析 arXiv 论文

```bash
# 使用 arXiv ID
python3 src/math_analyzer.py 2512.19344v1 -o output/

# 使用完整 URL
python3 src/math_analyzer.py https://arxiv.org/abs/2603.03027 -o output/
```

### 命令行选项

```bash
python3 src/math_analyzer.py --help

# 跳过图形生成
python3 src/math_analyzer.py paper.pdf -o output/ --no-graph
```

## 输出文件

分析完成后，会在输出目录生成：

- `analysis_report.json` - 完整的结构化数据（JSON）
- `analysis_report.md` - 可读的分析报告（Markdown）
- `dependency_graph.png` - 依赖关系可视化图
- `dependency_graph.graphml` - 依赖关系图（可在 Gephi 等工具中打开）

## 测试示例

已测试的两篇论文：

1. **arXiv:2512.19344v1** - "PARAMETERS AND THETA LIFTS"
   - 17 个定义
   - 32 个定理
   - 12 个引理
   - 101 个实体总计

2. **arXiv:2603.03027** - "A TWISTED HECKE ALGEBRA, THEN AND NOW, AND A KLEIN BOTTLE"
   - 1 个定义
   - 19 个定理
   - 20 个引理
   - 53 个实体总计

## 依赖关系图颜色说明

- 🟢 绿色 - Definition（定义）
- 🔵 蓝色 - Theorem（定理）
- 🟠 橙色 - Lemma（引理）
- 🟣 紫色 - Proposition（命题）
- 🔴 红色 - Assumption（假设）
- ⚫ 灰色 - Remark（备注）

## 项目结构

```
mathpaperskill/
├── src/
│   └── math_analyzer.py      # 主程序
├── test_papers/              # 测试论文
│   ├── 2512.19344v1.pdf
│   └── 2603.03027.pdf
├── output/                   # 分析结果
│   ├── paper1/
│   └── paper2/
├── requirements.txt          # Python 依赖
└── README.md
```

## 技术细节

- **PDF 处理**：使用 `pdftotext` 提取文本，OCR 作为备用
- **LaTeX 解析**：正则表达式匹配数学环境
- **图可视化**：NetworkX + Matplotlib
- **依赖检测**：通过 `\ref` 和 `\label` 命令分析

## 注意事项

- 对于扫描版 PDF，会自动启用 OCR（需要 tesseract）
- 实体提取基于文本模式匹配，可能不完美的识别所有数学结构
- 依赖关系图基于显式引用，隐式依赖可能无法检测

## 许可证

MIT
