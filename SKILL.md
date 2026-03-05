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
- `dependency_graph.html` - **Interactive HTML graph** with D3.js
- `dependency_graph.dot` - Graphviz DOT format
- `dependency_graph.mmd` - Mermaid diagram format
- `dependency_graph.graphml` - Graph data for Gephi/Cytoscape
- **`quality_report.json`** - **Quality evaluation metrics** (NEW!)

## Quality Evaluation

The tool automatically evaluates dependency graph quality across 5 dimensions:

### Metrics

| Metric | Weight | Description | Ideal Range |
|--------|--------|-------------|-------------|
| **Coverage** | 25% | Number of entities detected | 10-50 entities |
| **Connectivity** | 25% | % of nodes with edges | 50-90% |
| **Structure Balance** | 20% | Ratio of definitions to theorems | 1:1 to 1:3 |
| **Completeness** | 20% | Isolated node percentage | <20% |
| **Density** | 10% | Edge density | 0.05-0.3 |

### Quality Grades

- **A (≥0.9)** - Excellent quality
- **B (0.8-0.89)** - Good quality
- **C (0.7-0.79)** - Fair quality
- **D (0.6-0.69)** - Poor quality
- **F (<0.6)** - Critical issues

### Recommendations

The quality report provides actionable recommendations:
- 📄 Use LaTeX source for better entity extraction
- 🔗 Check \label and \ref parsing
- 📐 Verify definitions and theorems are detected
- 🔍 Review for missed dependencies

### Example Quality Output

```
🎯 OVERALL SCORE: 0.85/1.0 (Grade: B)

Coverage          [██████████] 1.00 - 53 entities detected
Connectivity      [██████░░░░] 0.60 - 65% of entities connected
Structure Balance [████████░░] 0.80 - Good theorem/definition ratio
Completeness      [████████░░] 0.85 - 15% isolated nodes
Density           [████████░░] 0.80 - Density in ideal range
```

### Interactive HTML Graph Features

The HTML graph (`dependency_graph.html`) includes:

🎮 **Interactive Features:**
- **Drag nodes** - Adjust layout freely
- **Zoom/Pan** - Mouse wheel zoom, drag canvas
- **Hover tooltips** - Show node details
- **Highlight connections** - Hover to highlight related edges
- **Search filter** - Top-right search box
- **Animation controls** - Pause/play force-directed animation
- **Reset view** - One-click restore

🎨 **Visual Effects:**
- Dark gradient background
- Color-coded nodes by type
- Glowing hover effects
- Smooth animations

Usage: Open `dependency_graph.html` in any browser

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
