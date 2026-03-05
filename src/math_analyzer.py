#!/usr/bin/env python3
"""
Math Paper Analyzer - Extract and analyze mathematical structures from papers.
Supports PDF, LaTeX files, and arXiv links.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import networkx as nx
import matplotlib.pyplot as plt


@dataclass
class MathEntity:
    """Represents a mathematical entity (definition, theorem, lemma, etc.)"""
    type: str  # definition, theorem, lemma, proposition, corollary, assumption, remark
    name: str
    label: Optional[str] = None
    content: str = ""
    section: str = ""
    dependencies: List[str] = field(default_factory=list)
    line_number: int = 0
    cited_by: List[str] = field(default_factory=list)


@dataclass
class PaperStructure:
    """Structure of a mathematical paper"""
    title: str = ""
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    sections: List[str] = field(default_factory=list)
    entities: List[MathEntity] = field(default_factory=list)
    definitions: Dict[str, MathEntity] = field(default_factory=dict)
    theorems: Dict[str, MathEntity] = field(default_factory=dict)
    lemmas: Dict[str, MathEntity] = field(default_factory=dict)
    propositions: Dict[str, MathEntity] = field(default_factory=dict)
    corollaries: Dict[str, MathEntity] = field(default_factory=dict)
    assumptions: Dict[str, MathEntity] = field(default_factory=dict)
    remarks: Dict[str, MathEntity] = field(default_factory=dict)


class ArxivFetcher:
    """Fetch papers from arXiv"""
    
    ARXIV_PDF_URL = "https://arxiv.org/pdf/{}.pdf"
    ARXIV_SOURCE_URL = "https://arxiv.org/e-print/{}"
    
    @staticmethod
    def extract_arxiv_id(url_or_id: str) -> str:
        """Extract arXiv ID from URL or return as-is if already an ID"""
        # Match patterns like 2512.19344v1 or arxiv.org/abs/2512.19344
        patterns = [
            r'arxiv\.org/abs/(\d+\.\d+(?:v\d+)?)',
            r'arxiv\.org/pdf/(\d+\.\d+(?:v\d+)?)',
            r'^(\d{4}\.\d+(?:v\d+)?)$',
        ]
        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)
        return url_or_id
    
    @classmethod
    def fetch_pdf(cls, arxiv_id: str, output_dir: str = ".") -> str:
        """Download PDF from arXiv"""
        arxiv_id = cls.extract_arxiv_id(arxiv_id)
        pdf_url = cls.ARXIV_PDF_URL.format(arxiv_id)
        output_path = os.path.join(output_dir, f"{arxiv_id}.pdf")
        
        print(f"Downloading from {pdf_url}...")
        urllib.request.urlretrieve(pdf_url, output_path)
        print(f"Saved to {output_path}")
        return output_path
    
    @classmethod
    def fetch_source(cls, arxiv_id: str, output_dir: str = ".") -> str:
        """Download source tarball from arXiv"""
        arxiv_id = cls.extract_arxiv_id(arxiv_id)
        source_url = cls.ARXIV_SOURCE_URL.format(arxiv_id)
        output_path = os.path.join(output_dir, f"{arxiv_id}_source.tar.gz")
        
        print(f"Downloading source from {source_url}...")
        urllib.request.urlretrieve(source_url, output_path)
        print(f"Saved to {output_path}")
        return output_path


class PDFExtractor:
    """Extract text from PDF files"""
    
    @staticmethod
    def extract_text(pdf_path: str) -> str:
        """Extract text using pdftotext"""
        result = subprocess.run(
            ["pdftotext", "-layout", pdf_path, "-"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"pdftotext failed: {result.stderr}")
        return result.stdout
    
    @staticmethod
    def extract_with_ocr(pdf_path: str) -> str:
        """Extract text using OCR (for scanned PDFs)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract images from PDF
            subprocess.run(
                ["pdfimages", "-png", pdf_path, os.path.join(tmpdir, "page")],
                check=True
            )
            
            # OCR each image
            texts = []
            images = sorted([f for f in os.listdir(tmpdir) if f.endswith('.png')])
            for img in images:
                img_path = os.path.join(tmpdir, img)
                txt_path = os.path.join(tmpdir, img.replace('.png', ''))
                subprocess.run(
                    ["tesseract", img_path, txt_path, "-l", "eng"],
                    check=True
                )
                with open(f"{txt_path}.txt", 'r') as f:
                    texts.append(f.read())
            
            return "\n\n".join(texts)


class LatexParser:
    """Parse LaTeX files to extract mathematical structure"""
    
    # Environment patterns
    ENV_PATTERNS = {
        'definition': r'\\begin\{definition\}(?:\[(.*?)\])?(.*?)\\end\{definition\}',
        'theorem': r'\\begin\{theorem\}(?:\[(.*?)\])?(.*?)\\end\{theorem\}',
        'lemma': r'\\begin\{lemma\}(?:\[(.*?)\])?(.*?)\\end\{lemma\}',
        'proposition': r'\\begin\{proposition\}(?:\[(.*?)\])?(.*?)\\end\{proposition\}',
        'corollary': r'\\begin\{corollary\}(?:\[(.*?)\])?(.*?)\\end\{corollary\}',
        'assumption': r'\\begin\{assumption\}(?:\[(.*?)\])?(.*?)\\end\{assumption\}',
        'remark': r'\\begin\{remark\}(?:\[(.*?)\])?(.*?)\\end\{remark\}',
    }
    
    LABEL_PATTERN = r'\\label\{(.*?)\}'
    REF_PATTERN = r'\\(?:ref|eqref|cref)\{(.*?)\}'
    
    def __init__(self):
        self.structure = PaperStructure()
        self.entity_counter = defaultdict(int)
    
    def parse_file(self, tex_path: str) -> PaperStructure:
        """Parse a LaTeX file"""
        with open(tex_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return self.parse_content(content)
    
    def parse_content(self, content: str) -> PaperStructure:
        """Parse LaTeX content"""
        # Extract basic info
        self._extract_metadata(content)
        self._extract_sections(content)
        
        # Extract entities
        for entity_type, pattern in self.ENV_PATTERNS.items():
            self._extract_entities(content, entity_type, pattern)
        
        # Build dependency graph
        self._build_dependencies()
        
        return self.structure
    
    def _extract_metadata(self, content: str):
        """Extract title, authors, abstract"""
        # Title
        title_match = re.search(r'\\title\{(.*?)\}', content, re.DOTALL)
        if title_match:
            self.structure.title = self._clean_latex(title_match.group(1))
        
        # Authors
        author_matches = re.findall(r'\\author\{(.*?)\}', content, re.DOTALL)
        self.structure.authors = [self._clean_latex(a) for a in author_matches]
        
        # Abstract
        abstract_match = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', content, re.DOTALL)
        if abstract_match:
            self.structure.abstract = self._clean_latex(abstract_match.group(1))
    
    def _extract_sections(self, content: str):
        """Extract section titles"""
        sections = re.findall(r'\\section\{(.*?)\}', content)
        self.structure.sections = sections
    
    def _extract_entities(self, content: str, entity_type: str, pattern: str):
        """Extract mathematical entities"""
        matches = list(re.finditer(pattern, content, re.DOTALL))
        
        for i, match in enumerate(matches):
            self.entity_counter[entity_type] += 1
            
            name = match.group(1) if match.group(1) else f"{entity_type.capitalize()} {self.entity_counter[entity_type]}"
            entity_content = match.group(2) if len(match.groups()) > 1 else match.group(1)
            
            # Extract label
            label_match = re.search(self.LABEL_PATTERN, match.group(0))
            label = label_match.group(1) if label_match else None
            
            entity = MathEntity(
                type=entity_type,
                name=name,
                label=label,
                content=self._clean_latex(entity_content) if entity_content else "",
                line_number=match.start()
            )
            
            self.structure.entities.append(entity)
            
            # Store in appropriate category
            category_map = {
                'definition': self.structure.definitions,
                'theorem': self.structure.theorems,
                'lemma': self.structure.lemmas,
                'proposition': self.structure.propositions,
                'corollary': self.structure.corollaries,
                'assumption': self.structure.assumptions,
                'remark': self.structure.remarks,
            }
            
            key = label if label else f"{entity_type}_{self.entity_counter[entity_type]}"
            category_map[entity_type][key] = entity
    
    def _build_dependencies(self):
        """Build dependency graph based on \ref citations"""
        for entity in self.structure.entities:
            # Find all \ref commands in the entity content
            refs = re.findall(self.REF_PATTERN, entity.content)
            entity.dependencies = refs
            
            # Update cited_by for referenced entities
            for ref in refs:
                for other in self.structure.entities:
                    if other.label == ref:
                        if entity.label not in other.cited_by:
                            other.cited_by.append(entity.label)
                        break
    
    def _clean_latex(self, text: str) -> str:
        """Clean LaTeX formatting from text"""
        # Remove comments
        text = re.sub(r'(?<!\\)%.*$', '', text, flags=re.MULTILINE)
        # Remove some common commands
        text = re.sub(r'\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?', ' ', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text.strip()


class TextAnalyzer:
    """Analyze plain text to identify mathematical structure"""
    
    # Keywords for identifying entities
    KEYWORDS = {
        'definition': [r'Definition\s+\d+', r'Definition\.'],
        'theorem': [r'Theorem\s+\d+', r'Theorem\.'],
        'lemma': [r'Lemma\s+\d+', r'Lemma\.'],
        'proposition': [r'Proposition\s+\d+', r'Proposition\.'],
        'corollary': [r'Corollary\s+\d+', r'Corollary\.'],
        'assumption': [r'Assumption\s+\d+', r'Assumption\.', r'Assume\s+that'],
        'remark': [r'Remark\s+\d+', r'Remark\.'],
    }
    
    def __init__(self):
        self.structure = PaperStructure()
        self.entity_counter = defaultdict(int)
    
    def analyze(self, text: str) -> PaperStructure:
        """Analyze text to extract mathematical structure"""
        # Extract title (first line or sentence)
        lines = text.split('\n')
        self.structure.title = lines[0].strip() if lines else "Unknown"
        
        # Find entities
        for entity_type, patterns in self.KEYWORDS.items():
            self._find_entities(text, entity_type, patterns)
        
        # Build dependencies
        self._build_dependencies()
        
        return self.structure
    
    def _find_entities(self, text: str, entity_type: str, patterns: List[str]):
        """Find entities of a specific type"""
        for pattern in patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            
            for match in matches:
                self.entity_counter[entity_type] += 1
                start = match.end()
                
                # Extract content (next sentence or paragraph)
                end_match = re.search(r'\n\s*\n|\.\s+[A-Z]', text[start:])
                end = start + end_match.start() if end_match else min(start + 500, len(text))
                content = text[start:end].strip()
                
                entity = MathEntity(
                    type=entity_type,
                    name=f"{entity_type.capitalize()} {self.entity_counter[entity_type]}",
                    content=content,
                    line_number=match.start()
                )
                
                self.structure.entities.append(entity)
                
                category_map = {
                    'definition': self.structure.definitions,
                    'theorem': self.structure.theorems,
                    'lemma': self.structure.lemmas,
                    'proposition': self.structure.propositions,
                    'corollary': self.structure.corollaries,
                    'assumption': self.structure.assumptions,
                    'remark': self.structure.remarks,
                }
                
                key = f"{entity_type}_{self.entity_counter[entity_type]}"
                category_map[entity_type][key] = entity
    
    def _build_dependencies(self):
        """Build simple dependency graph based on text references"""
        for entity in self.structure.entities:
            # Look for references to other entities
            for other in self.structure.entities:
                if other == entity:
                    continue
                # Check if entity references other by name
                if other.name.lower() in entity.content.lower():
                    if other.label:
                        entity.dependencies.append(other.label)


class DependencyGraphVisualizer:
    """Visualize dependency graph of mathematical entities"""
    
    def __init__(self, structure: PaperStructure):
        self.structure = structure
        self.graph = nx.DiGraph()
    
    def build_graph(self):
        """Build NetworkX graph from structure"""
        # Add nodes
        for entity in self.structure.entities:
            node_id = entity.label if entity.label else f"{entity.type}_{entity.name}"
            self.graph.add_node(
                node_id,
                type=entity.type,
                name=entity.name,
                content=entity.content[:100] + "..." if len(entity.content) > 100 else entity.content
            )
        
        # Add edges (dependencies)
        for entity in self.structure.entities:
            source = entity.label if entity.label else f"{entity.type}_{entity.name}"
            for dep in entity.dependencies:
                if dep in self.graph:
                    self.graph.add_edge(source, dep)
        
        return self.graph
    
    def visualize(self, output_path: str = "dependency_graph.png"):
        """Create visualization of dependency graph"""
        if len(self.graph.nodes()) == 0:
            self.build_graph()
        
        if len(self.graph.nodes()) == 0:
            print("No entities to visualize")
            return
        
        plt.figure(figsize=(14, 10))
        
        # Color nodes by type
        type_colors = {
            'definition': '#4CAF50',
            'theorem': '#2196F3',
            'lemma': '#FF9800',
            'proposition': '#9C27B0',
            'corollary': '#E91E63',
            'assumption': '#F44336',
            'remark': '#607D8B',
        }
        
        node_colors = [
            type_colors.get(self.graph.nodes[n].get('type', ''), '#999999')
            for n in self.graph.nodes()
        ]
        
        # Layout
        pos = nx.spring_layout(self.graph, k=2, iterations=50)
        
        # Draw
        nx.draw_networkx_nodes(self.graph, pos, node_color=node_colors, node_size=1500, alpha=0.9)
        nx.draw_networkx_edges(self.graph, pos, edge_color='#666666', arrows=True, 
                               arrowsize=20, arrowstyle='->', width=1.5, alpha=0.6)
        
        # Labels
        labels = {n: self._truncate_label(self.graph.nodes[n].get('name', n))
                  for n in self.graph.nodes()}
        nx.draw_networkx_labels(self.graph, pos, labels, font_size=8, font_weight='bold')
        
        plt.title("Mathematical Dependencies", fontsize=16, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Dependency graph saved to: {output_path}")
    
    def _truncate_label(self, label: str, max_len: int = 20) -> str:
        """Truncate label for display"""
        if len(label) <= max_len:
            return label
        return label[:max_len-3] + "..."
    
    def export_graphml(self, output_path: str = "dependency_graph.graphml"):
        """Export graph to GraphML format"""
        if len(self.graph.nodes()) == 0:
            self.build_graph()
        # Clean node attributes for XML compatibility
        for node in self.graph.nodes():
            for key, value in list(self.graph.nodes[node].items()):
                if isinstance(value, str):
                    # Remove control characters and NULL bytes
                    cleaned = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')
                    self.graph.nodes[node][key] = cleaned[:500]  # Limit length
        nx.write_graphml(self.graph, output_path)
        print(f"Graph exported to: {output_path}")
    
    def export_dot(self, output_path: str = "dependency_graph.dot"):
        """Export graph to DOT format (Graphviz)"""
        if len(self.graph.nodes()) == 0:
            self.build_graph()
        
        type_colors = {
            'definition': '#4CAF50',
            'theorem': '#2196F3',
            'lemma': '#FF9800',
            'proposition': '#9C27B0',
            'corollary': '#E91E63',
            'assumption': '#F44336',
            'remark': '#607D8B',
        }
        
        lines = ['digraph MathDependencies {', '  rankdir=TB;']
        lines.append('  node [shape=box, style=rounded, fontname="Arial"];')
        
        # Add nodes
        for node in self.graph.nodes():
            node_type = self.graph.nodes[node].get('type', 'unknown')
            name = self.graph.nodes[node].get('name', node)
            color = type_colors.get(node_type, '#999999')
            # Escape special characters
            safe_name = name.replace('"', '\\"').replace('\n', ' ')
            safe_id = node.replace('"', '\\"')
            lines.append(f'  "{safe_id}" [label="{safe_name}", fillcolor="{color}", style="filled,rounded"];')
        
        # Add edges
        for edge in self.graph.edges():
            source = edge[0].replace('"', '\\"')
            target = edge[1].replace('"', '\\"')
            lines.append(f'  "{source}" -> "{target}";')
        
        lines.append('}')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"DOT graph saved to: {output_path}")
    
    def export_mermaid(self, output_path: str = "dependency_graph.mmd"):
        """Export graph to Mermaid format (for Markdown)"""
        if len(self.graph.nodes()) == 0:
            self.build_graph()
        
        type_colors = {
            'definition': '#4CAF50',
            'theorem': '#2196F3',
            'lemma': '#FF9800',
            'proposition': '#9C27B0',
            'corollary': '#E91E63',
            'assumption': '#F44336',
            'remark': '#607D8B',
        }
        
        lines = ['```mermaid', 'flowchart TD']
        
        # Add class definitions for colors
        for entity_type, color in type_colors.items():
            lines.append(f'    classDef {entity_type} fill:{color},stroke:#333,stroke-width:2px,color:#fff;')
        
        # Add nodes
        for node in self.graph.nodes():
            node_type = self.graph.nodes[node].get('type', 'unknown')
            name = self.graph.nodes[node].get('name', node)
            # Escape special characters for Mermaid
            safe_name = name.replace('[', '&#91;').replace(']', '&#93;').replace('(', '&#40;').replace(')', '&#41;')
            safe_id = node.replace('[', '_').replace(']', '_').replace('(', '_').replace(')', '_').replace(' ', '_')
            safe_id = re.sub(r'[^a-zA-Z0-9_]', '_', safe_id)
            lines.append(f'    {safe_id}["{safe_name}"]')
            if node_type in type_colors:
                lines.append(f'    class {safe_id} {node_type};')
        
        # Add edges
        for edge in self.graph.edges():
            source = edge[0].replace('[', '_').replace(']', '_').replace('(', '_').replace(')', '_').replace(' ', '_')
            source = re.sub(r'[^a-zA-Z0-9_]', '_', source)
            target = edge[1].replace('[', '_').replace(']', '_').replace('(', '_').replace(')', '_').replace(' ', '_')
            target = re.sub(r'[^a-zA-Z0-9_]', '_', target)
            lines.append(f'    {source} --> {target}')
        
        lines.append('```')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"Mermaid graph saved to: {output_path}")
    
    def export_html(self, output_path: str = "dependency_graph.html"):
        """Export interactive HTML graph using D3.js"""
        if len(self.graph.nodes()) == 0:
            self.build_graph()
        
        type_colors = {
            'definition': '#4CAF50',
            'theorem': '#2196F3',
            'lemma': '#FF9800',
            'proposition': '#9C27B0',
            'corollary': '#E91E63',
            'assumption': '#F44336',
            'remark': '#607D8B',
        }
        
        # Build nodes and links for D3
        nodes = []
        for node in self.graph.nodes():
            node_type = self.graph.nodes[node].get('type', 'unknown')
            name = self.graph.nodes[node].get('name', node)
            content = self.graph.nodes[node].get('content', '')
            nodes.append({
                'id': node,
                'name': name,
                'type': node_type,
                'color': type_colors.get(node_type, '#999999'),
                'content': content.replace('"', '\\"').replace('\n', ' ')
            })
        
        links = []
        for edge in self.graph.edges():
            links.append({'source': edge[0], 'target': edge[1]})
        
        # HTML template with D3.js
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mathematical Dependencies - Interactive Graph</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
        }}
        .header {{
            padding: 20px;
            text-align: center;
            background: rgba(0,0,0,0.3);
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        .legend {{
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
            padding: 15px;
            background: rgba(0,0,0,0.2);
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            border: 2px solid rgba(255,255,255,0.3);
        }}
        #graph {{
            width: 100%;
            height: calc(100vh - 180px);
            position: relative;
        }}
        .tooltip {{
            position: absolute;
            padding: 12px;
            background: rgba(0,0,0,0.9);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            max-width: 300px;
            font-size: 13px;
            line-height: 1.5;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }}
        .tooltip h4 {{
            margin-bottom: 8px;
            color: #4CAF50;
            font-size: 14px;
        }}
        .controls {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            display: flex;
            gap: 10px;
        }}
        .btn {{
            padding: 10px 20px;
            background: rgba(76, 175, 80, 0.8);
            border: none;
            border-radius: 25px;
            color: white;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }}
        .btn:hover {{
            background: rgba(76, 175, 80, 1);
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(76, 175, 80, 0.4);
        }}
        svg {{
            width: 100%;
            height: 100%;
        }}
        .node circle {{
            cursor: pointer;
            stroke: #fff;
            stroke-width: 2px;
            transition: all 0.3s;
        }}
        .node circle:hover {{
            stroke-width: 4px;
            filter: drop-shadow(0 0 10px currentColor);
        }}
        .node text {{
            font-size: 12px;
            fill: #fff;
            text-anchor: middle;
            pointer-events: none;
            text-shadow: 0 1px 3px rgba(0,0,0,0.8);
        }}
        .link {{
            stroke: rgba(255,255,255,0.4);
            stroke-width: 1.5px;
            marker-end: url(#arrowhead);
        }}
        .link.highlight {{
            stroke: #4CAF50;
            stroke-width: 2.5px;
        }}
        .node.highlight circle {{
            stroke: #FFD700;
            stroke-width: 4px;
        }}
        .search-box {{
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 15px;
            border-radius: 25px;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(0,0,0,0.5);
            color: white;
            width: 250px;
            font-size: 14px;
        }}
        .search-box::placeholder {{
            color: rgba(255,255,255,0.5);
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔬 Mathematical Dependencies</h1>
        <p>Interactive Force-Directed Graph</p>
    </div>
    
    <div class="legend">
        <div class="legend-item"><div class="legend-color" style="background: #4CAF50;"></div>Definition</div>
        <div class="legend-item"><div class="legend-color" style="background: #2196F3;"></div>Theorem</div>
        <div class="legend-item"><div class="legend-color" style="background: #FF9800;"></div>Lemma</div>
        <div class="legend-item"><div class="legend-color" style="background: #9C27B0;"></div>Proposition</div>
        <div class="legend-item"><div class="legend-color" style="background: #E91E63;"></div>Corollary</div>
        <div class="legend-item"><div class="legend-color" style="background: #F44336;"></div>Assumption</div>
        <div class="legend-item"><div class="legend-color" style="background: #607D8B;"></div>Remark</div>
    </div>
    
    <input type="text" class="search-box" placeholder="🔍 Search nodes..." id="searchBox">
    
    <div id="graph"></div>
    <div class="tooltip" id="tooltip"></div>
    
    <div class="controls">
        <button class="btn" onclick="resetZoom()">🔄 Reset View</button>
        <button class="btn" onclick="toggleAnimation()">⏯️ Pause/Play</button>
    </div>

    <script>
        const nodes = {json.dumps(nodes, ensure_ascii=False)};
        const links = {json.dumps(links, ensure_ascii=False)};
        
        const width = document.getElementById('graph').clientWidth;
        const height = document.getElementById('graph').clientHeight;
        
        const svg = d3.select("#graph")
            .append("svg")
            .attr("viewBox", [0, 0, width, height]);
        
        // Arrow marker
        svg.append("defs").append("marker")
            .attr("id", "arrowhead")
            .attr("viewBox", "0 -5 10 10")
            .attr("refX", 25)
            .attr("refY", 0)
            .attr("markerWidth", 8)
            .attr("markerHeight", 8)
            .attr("orient", "auto")
            .append("path")
            .attr("d", "M0,-5L10,0L0,5")
            .attr("fill", "rgba(255,255,255,0.4)");
        
        // Zoom behavior
        const g = svg.append("g");
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => g.attr("transform", event.transform));
        svg.call(zoom);
        
        // Force simulation
        let animationRunning = true;
        const simulation = d3.forceSimulation(nodes)
            .force("link", d3.forceLink(links).id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-400))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(40));
        
        // Draw links
        const link = g.append("g")
            .selectAll("line")
            .data(links)
            .join("line")
            .attr("class", "link");
        
        // Draw nodes
        const node = g.append("g")
            .selectAll("g")
            .data(nodes)
            .join("g")
            .attr("class", "node")
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));
        
        // Node circles
        node.append("circle")
            .attr("r", 20)
            .attr("fill", d => d.color);
        
        // Node labels
        node.append("text")
            .attr("dy", 35)
            .text(d => d.name.length > 15 ? d.name.substring(0, 15) + "..." : d.name);
        
        // Tooltip
        const tooltip = d3.select("#tooltip");
        
        node.on("mouseover", function(event, d) {{
            tooltip.style("opacity", 1)
                .html(`<h4>${{d.name}}</h4><p><strong>Type:</strong> ${{d.type}}</p><p>${{d.content}}</p>`)
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 10) + "px");
            
            // Highlight connected links
            link.classed("highlight", l => l.source.id === d.id || l.target.id === d.id);
            node.classed("highlight", n => n.id === d.id || 
                links.some(l => (l.source.id === d.id && l.target.id === n.id) || 
                                (l.target.id === d.id && l.source.id === n.id)));
        }})
        .on("mouseout", function() {{
            tooltip.style("opacity", 0);
            link.classed("highlight", false);
            node.classed("highlight", false);
        }});
        
        // Update positions
        simulation.on("tick", () => {{
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            node
                .attr("transform", d => `translate(${{d.x}},${{d.y}})`);
        }});
        
        // Drag functions
        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}
        
        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}
        
        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}
        
        // Controls
        function resetZoom() {{
            svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity);
            simulation.alpha(1).restart();
        }}
        
        function toggleAnimation() {{
            if (animationRunning) {{
                simulation.stop();
            }} else {{
                simulation.restart();
            }}
            animationRunning = !animationRunning;
        }}
        
        // Search functionality
        document.getElementById('searchBox').addEventListener('input', function(e) {{
            const term = e.target.value.toLowerCase();
            if (term === '') {{
                node.style('opacity', 1);
                link.style('opacity', 1);
                return;
            }}
            
            const matched = nodes.filter(n => n.name.toLowerCase().includes(term));
            const matchedIds = new Set(matched.map(n => n.id));
            
            node.style('opacity', d => matchedIds.has(d.id) ? 1 : 0.2);
            link.style('opacity', d => 
                matchedIds.has(d.source.id) && matchedIds.has(d.target.id) ? 1 : 0.1);
        }});
        
        // Window resize
        window.addEventListener('resize', () => {{
            const newWidth = document.getElementById('graph').clientWidth;
            const newHeight = document.getElementById('graph').clientHeight;
            simulation.force("center", d3.forceCenter(newWidth / 2, newHeight / 2));
            simulation.alpha(0.3).restart();
        }});
    </script>
</body>
</html>'''
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Interactive HTML graph saved to: {output_path}")


class MathPaperAnalyzer:
    """Main class for analyzing math papers"""
    
    def __init__(self):
        self.latex_parser = LatexParser()
        self.text_analyzer = TextAnalyzer()
        self.pdf_extractor = PDFExtractor()
    
    def analyze(self, input_path: str, output_dir: str = ".") -> PaperStructure:
        """
        Analyze a math paper from various input formats.
        
        Args:
            input_path: Path to PDF, .tex file, or arXiv ID/URL
            output_dir: Directory for output files
        """
        input_path = input_path.strip()
        
        # Check if arXiv link/ID
        if 'arxiv' in input_path.lower() or re.match(r'^\d{4}\.\d+', input_path):
            print(f"Fetching from arXiv: {input_path}")
            pdf_path = ArxivFetcher.fetch_pdf(input_path, output_dir)
            return self.analyze_pdf(pdf_path, output_dir)
        
        # Check file extension
        ext = Path(input_path).suffix.lower()
        
        if ext == '.tex':
            return self.analyze_latex(input_path, output_dir)
        elif ext == '.pdf':
            return self.analyze_pdf(input_path, output_dir)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    def analyze_pdf(self, pdf_path: str, output_dir: str = ".") -> PaperStructure:
        """Analyze PDF file"""
        print(f"Extracting text from PDF: {pdf_path}")
        
        try:
            text = self.pdf_extractor.extract_text(pdf_path)
        except Exception as e:
            print(f"Native extraction failed, trying OCR: {e}")
            text = self.pdf_extractor.extract_with_ocr(pdf_path)
        
        # Check if text looks like LaTeX source
        if '\\begin{document}' in text or '\\section{' in text:
            print("Detected LaTeX source in PDF, parsing as LaTeX...")
            structure = self.latex_parser.parse_content(text)
        else:
            print("Analyzing as plain text...")
            structure = self.text_analyzer.analyze(text)
        
        return structure
    
    def analyze_latex(self, tex_path: str, output_dir: str = ".") -> PaperStructure:
        """Analyze LaTeX file"""
        print(f"Parsing LaTeX file: {tex_path}")
        structure = self.latex_parser.parse_file(tex_path)
        return structure
    
    def generate_report(self, structure: PaperStructure, output_dir: str = "."):
        """Generate analysis report"""
        os.makedirs(output_dir, exist_ok=True)
        
        # JSON report
        report_path = os.path.join(output_dir, "analysis_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                'title': structure.title,
                'authors': structure.authors,
                'abstract': structure.abstract,
                'sections': structure.sections,
                'statistics': {
                    'definitions': len(structure.definitions),
                    'theorems': len(structure.theorems),
                    'lemmas': len(structure.lemmas),
                    'propositions': len(structure.propositions),
                    'corollaries': len(structure.corollaries),
                    'assumptions': len(structure.assumptions),
                    'remarks': len(structure.remarks),
                    'total': len(structure.entities),
                },
                'entities': [
                    {
                        'type': e.type,
                        'name': e.name,
                        'label': e.label,
                        'content': e.content[:500] + "..." if len(e.content) > 500 else e.content,
                        'dependencies': e.dependencies,
                        'cited_by': e.cited_by,
                    }
                    for e in structure.entities
                ]
            }, f, indent=2, ensure_ascii=False)
        print(f"Report saved to: {report_path}")
        
        # Markdown report
        md_path = os.path.join(output_dir, "analysis_report.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# {structure.title}\n\n")
            
            if structure.authors:
                f.write(f"**Authors:** {', '.join(structure.authors)}\n\n")
            
            if structure.abstract:
                f.write(f"## Abstract\n\n{structure.abstract}\n\n")
            
            f.write("## Statistics\n\n")
            stats = {
                'Definitions': len(structure.definitions),
                'Theorems': len(structure.theorems),
                'Lemmas': len(structure.lemmas),
                'Propositions': len(structure.propositions),
                'Corollaries': len(structure.corollaries),
                'Assumptions': len(structure.assumptions),
                'Remarks': len(structure.remarks),
            }
            for name, count in stats.items():
                f.write(f"- **{name}:** {count}\n")
            f.write(f"\n**Total entities:** {len(structure.entities)}\n\n")
            
            # Entity details
            for entity_type in ['definition', 'theorem', 'lemma', 'proposition', 'corollary', 'assumption', 'remark']:
                entities = [e for e in structure.entities if e.type == entity_type]
                if entities:
                    f.write(f"## {entity_type.capitalize()}s\n\n")
                    for e in entities:
                        f.write(f"### {e.name}\n")
                        if e.label:
                            f.write(f"*Label: `{e.label}`*\n")
                        if e.dependencies:
                            f.write(f"*Depends on: {', '.join(e.dependencies)}*\n")
                        f.write(f"\n{e.content[:300]}...\n\n")
        print(f"Markdown report saved to: {md_path}")
        
        # Dependency graph
        visualizer = DependencyGraphVisualizer(structure)
        graph_path = os.path.join(output_dir, "dependency_graph.png")
        visualizer.visualize(graph_path)
        
        # Export graph data
        graphml_path = os.path.join(output_dir, "dependency_graph.graphml")
        visualizer.export_graphml(graphml_path)
        
        # Export DOT format (Graphviz)
        dot_path = os.path.join(output_dir, "dependency_graph.dot")
        visualizer.export_dot(dot_path)
        
        # Export Mermaid format (for Markdown)
        mermaid_path = os.path.join(output_dir, "dependency_graph.mmd")
        visualizer.export_mermaid(mermaid_path)
        
        # Export interactive HTML (D3.js)
        html_path = os.path.join(output_dir, "dependency_graph.html")
        visualizer.export_html(html_path)


def main():
    parser = argparse.ArgumentParser(description="Analyze mathematical papers")
    parser.add_argument("input", help="PDF file, LaTeX file, or arXiv ID/URL")
    parser.add_argument("-o", "--output", default="./output", help="Output directory")
    parser.add_argument("--no-graph", action="store_true", help="Skip dependency graph generation")
    
    args = parser.parse_args()
    
    analyzer = MathPaperAnalyzer()
    
    try:
        structure = analyzer.analyze(args.input, args.output)
        analyzer.generate_report(structure, args.output)
        print("\nAnalysis complete!")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
