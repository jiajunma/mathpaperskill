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
import urllib.error
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


class GraphQualityEvaluator:
    """Evaluate the quality of dependency graphs extracted from math papers"""
    
    def __init__(self, structure: PaperStructure):
        self.structure = structure
        self.graph = nx.DiGraph()
        self._build_graph()
    
    def _build_graph(self):
        """Build NetworkX graph from structure"""
        for entity in self.structure.entities:
            node_id = entity.label if entity.label else f"{entity.type}_{entity.name}"
            self.graph.add_node(
                node_id,
                type=entity.type,
                name=entity.name
            )
        
        for entity in self.structure.entities:
            source = entity.label if entity.label else f"{entity.type}_{entity.name}"
            for dep in entity.dependencies:
                if dep in self.graph:
                    self.graph.add_edge(source, dep)
    
    def evaluate(self) -> Dict:
        """
        Perform comprehensive quality evaluation.
        Returns a dictionary with scores and recommendations.
        """
        metrics = {
            'coverage': self._evaluate_coverage(),
            'connectivity': self._evaluate_connectivity(),
            'structure_balance': self._evaluate_structure_balance(),
            'completeness': self._evaluate_completeness(),
            'density': self._evaluate_density(),
        }
        
        # Calculate overall score (weighted average)
        weights = {
            'coverage': 0.25,
            'connectivity': 0.25,
            'structure_balance': 0.20,
            'completeness': 0.20,
            'density': 0.10,
        }
        
        overall_score = sum(
            metrics[metric]['score'] * weights[metric]
            for metric in metrics
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(metrics)
        
        return {
            'overall_score': round(overall_score, 2),
            'grade': self._score_to_grade(overall_score),
            'metrics': metrics,
            'recommendations': recommendations,
            'statistics': {
                'total_nodes': self.graph.number_of_nodes(),
                'total_edges': self.graph.number_of_edges(),
                'density': round(nx.density(self.graph), 4),
                'is_connected': nx.is_weakly_connected(self.graph) if self.graph.number_of_nodes() > 0 else False,
                'num_components': nx.number_weakly_connected_components(self.graph) if self.graph.number_of_nodes() > 0 else 0,
            }
        }
    
    def _evaluate_coverage(self) -> Dict:
        """
        Evaluate entity coverage - whether we've detected a reasonable number of entities.
        Score based on expected density of math entities in academic papers.
        """
        total_entities = len(self.structure.entities)
        
        # Heuristic: typical math papers have 5-15 major entities per 1000 words
        # We'll be lenient and consider 3-20 as acceptable range
        
        if total_entities == 0:
            return {
                'score': 0.0,
                'status': 'CRITICAL',
                'message': 'No entities detected. Check if input is a valid math paper.',
                'details': {'total_entities': 0}
            }
        
        if total_entities < 3:
            return {
                'score': 0.3,
                'status': 'POOR',
                'message': f'Only {total_entities} entities detected. May have missed content.',
                'details': {'total_entities': total_entities}
            }
        
        if total_entities < 10:
            return {
                'score': 0.6,
                'status': 'FAIR',
                'message': f'{total_entities} entities detected. Consider checking for missed entities.',
                'details': {'total_entities': total_entities}
            }
        
        if total_entities <= 50:
            return {
                'score': 0.9,
                'status': 'GOOD',
                'message': f'{total_entities} entities detected. Good coverage.',
                'details': {'total_entities': total_entities}
            }
        
        return {
            'score': 1.0,
            'status': 'EXCELLENT',
            'message': f'{total_entities} entities detected. Comprehensive coverage.',
            'details': {'total_entities': total_entities}
        }
    
    def _evaluate_connectivity(self) -> Dict:
        """
        Evaluate the connectivity of the dependency graph.
        Good graphs should have meaningful connections between entities.
        """
        if self.graph.number_of_nodes() == 0:
            return {
                'score': 0.0,
                'status': 'CRITICAL',
                'message': 'Empty graph - no connectivity to evaluate.',
                'details': {}
            }
        
        # Calculate percentage of nodes with at least one connection
        nodes_with_edges = sum(
            1 for node in self.graph.nodes()
            if self.graph.degree(node) > 0
        )
        
        connected_ratio = nodes_with_edges / self.graph.number_of_nodes()
        
        # Ideal: 70-90% of nodes should have connections
        # Too few connections = isolated entities
        # Too many connections = may indicate over-linking or false positives
        
        if connected_ratio < 0.3:
            return {
                'score': 0.3,
                'status': 'POOR',
                'message': f'Only {connected_ratio:.1%} of entities have dependencies. Many isolated nodes.',
                'details': {
                    'connected_nodes': nodes_with_edges,
                    'total_nodes': self.graph.number_of_nodes(),
                    'connected_ratio': connected_ratio
                }
            }
        
        if connected_ratio < 0.5:
            return {
                'score': 0.6,
                'status': 'FAIR',
                'message': f'{connected_ratio:.1%} of entities connected. Consider adding more cross-references.',
                'details': {
                    'connected_nodes': nodes_with_edges,
                    'total_nodes': self.graph.number_of_nodes(),
                    'connected_ratio': connected_ratio
                }
            }
        
        if connected_ratio <= 0.9:
            return {
                'score': 0.9,
                'status': 'GOOD',
                'message': f'{connected_ratio:.1%} of entities have connections. Well-connected graph.',
                'details': {
                    'connected_nodes': nodes_with_edges,
                    'total_nodes': self.graph.number_of_nodes(),
                    'connected_ratio': connected_ratio
                }
            }
        
        # If almost all nodes are connected, might be over-connected
        return {
            'score': 0.85,
            'status': 'GOOD',
            'message': f'{connected_ratio:.1%} connected. Very dense - verify connections are meaningful.',
            'details': {
                'connected_nodes': nodes_with_edges,
                'total_nodes': self.graph.number_of_nodes(),
                'connected_ratio': connected_ratio
            }
        }
    
    def _evaluate_structure_balance(self) -> Dict:
        """
        Evaluate the balance of different entity types.
        Math papers should have a reasonable ratio of definitions to theorems to lemmas.
        """
        stats = {
            'definitions': len(self.structure.definitions),
            'theorems': len(self.structure.theorems),
            'lemmas': len(self.structure.lemmas),
            'propositions': len(self.structure.propositions),
            'corollaries': len(self.structure.corollaries),
            'assumptions': len(self.structure.assumptions),
            'remarks': len(self.structure.remarks),
        }
        
        total = sum(stats.values())
        
        if total == 0:
            return {
                'score': 0.0,
                'status': 'CRITICAL',
                'message': 'No entities of any type detected.',
                'details': stats
            }
        
        # Check for severe imbalances
        has_definitions = stats['definitions'] > 0
        has_theorems = stats['theorems'] > 0
        
        # Ideal math paper should have both definitions and theorems
        if not has_definitions and not has_theorems:
            # Only lemmas, remarks, etc. - might be a fragment
            return {
                'score': 0.4,
                'status': 'FAIR',
                'message': 'No definitions or theorems found. May be a partial extraction.',
                'details': stats
            }
        
        if not has_definitions:
            return {
                'score': 0.6,
                'status': 'FAIR',
                'message': 'No definitions found. Theorems may lack proper foundations.',
                'details': stats
            }
        
        if not has_theorems and stats['lemmas'] == 0:
            return {
                'score': 0.5,
                'status': 'POOR',
                'message': 'Only definitions found. No main results detected.',
                'details': stats
            }
        
        # Check ratio of theorems to definitions
        if stats['definitions'] > 0:
            theorem_def_ratio = (stats['theorems'] + stats['lemmas']) / stats['definitions']
            
            # Ideal ratio: 1-3 theorems/lemmas per definition
            if 0.5 <= theorem_def_ratio <= 5:
                return {
                    'score': 0.95,
                    'status': 'EXCELLENT',
                    'message': f'Good balance: {stats["definitions"]} definitions, {stats["theorems"]} theorems, {stats["lemmas"]} lemmas.',
                    'details': {**stats, 'theorem_def_ratio': round(theorem_def_ratio, 2)}
                }
            elif theorem_def_ratio < 0.5:
                return {
                    'score': 0.7,
                    'status': 'FAIR',
                    'message': f'More definitions than results. Consider if some definitions are unnecessary.',
                    'details': {**stats, 'theorem_def_ratio': round(theorem_def_ratio, 2)}
                }
            else:
                return {
                    'score': 0.8,
                    'status': 'GOOD',
                    'message': f'Many results relative to definitions. May need intermediate lemmas.',
                    'details': {**stats, 'theorem_def_ratio': round(theorem_def_ratio, 2)}
                }
        
        return {
            'score': 0.8,
            'status': 'GOOD',
            'message': f'Found {stats["theorems"]} theorems and {stats["lemmas"]} lemmas.',
            'details': stats
        }
    
    def _evaluate_completeness(self) -> Dict:
        """
        Evaluate completeness by checking for orphaned nodes and detecting gaps.
        """
        if self.graph.number_of_nodes() == 0:
            return {
                'score': 0.0,
                'status': 'CRITICAL',
                'message': 'Empty graph.',
                'details': {}
            }
        
        # Find truly isolated nodes (no in-edges, no out-edges)
        isolated_nodes = [
            node for node in self.graph.nodes()
            if self.graph.in_degree(node) == 0 and self.graph.out_degree(node) == 0
        ]
        
        isolated_ratio = len(isolated_nodes) / self.graph.number_of_nodes()
        
        # Find source nodes (only out-edges, no in-edges) - should be definitions/assumptions
        source_nodes = [
            node for node in self.graph.nodes()
            if self.graph.in_degree(node) == 0 and self.graph.out_degree(node) > 0
        ]
        
        # Find sink nodes (only in-edges, no out-edges) - should be theorems/corollaries
        sink_nodes = [
            node for node in self.graph.nodes()
            if self.graph.in_degree(node) > 0 and self.graph.out_degree(node) == 0
        ]
        
        if isolated_ratio > 0.5:
            return {
                'score': 0.3,
                'status': 'POOR',
                'message': f'{isolated_ratio:.1%} of nodes are isolated. Dependency extraction may have failed.',
                'details': {
                    'isolated_nodes': len(isolated_nodes),
                    'isolated_ratio': isolated_ratio,
                    'source_nodes': len(source_nodes),
                    'sink_nodes': len(sink_nodes)
                }
            }
        
        if isolated_ratio > 0.2:
            return {
                'score': 0.6,
                'status': 'FAIR',
                'message': f'{isolated_ratio:.1%} isolated nodes. Some dependencies may be missing.',
                'details': {
                    'isolated_nodes': len(isolated_nodes),
                    'isolated_ratio': isolated_ratio,
                    'source_nodes': len(source_nodes),
                    'sink_nodes': len(sink_nodes)
                }
            }
        
        if isolated_ratio <= 0.1:
            return {
                'score': 0.95,
                'status': 'EXCELLENT',
                'message': f'Only {isolated_ratio:.1%} isolated nodes. Good dependency coverage.',
                'details': {
                    'isolated_nodes': len(isolated_nodes),
                    'isolated_ratio': isolated_ratio,
                    'source_nodes': len(source_nodes),
                    'sink_nodes': len(sink_nodes)
                }
            }
        
        return {
            'score': 0.8,
            'status': 'GOOD',
            'message': f'{isolated_ratio:.1%} isolated nodes. Reasonable completeness.',
            'details': {
                'isolated_nodes': len(isolated_nodes),
                'isolated_ratio': isolated_ratio,
                'source_nodes': len(source_nodes),
                'sink_nodes': len(sink_nodes)
            }
        }
    
    def _evaluate_density(self) -> Dict:
        """
        Evaluate graph density - not too sparse, not too dense.
        """
        n = self.graph.number_of_nodes()
        
        if n <= 1:
            return {
                'score': 0.0,
                'status': 'CRITICAL',
                'message': 'Insufficient nodes to evaluate density.',
                'details': {'density': 0}
            }
        
        density = nx.density(self.graph)
        
        # For directed graphs: 0 = no edges, 1 = complete graph
        # Mathematical dependency graphs typically have density 0.05-0.3
        
        if density < 0.01:
            return {
                'score': 0.2,
                'status': 'POOR',
                'message': f'Density {density:.4f} is very low. Graph is too sparse.',
                'details': {'density': density}
            }
        
        if density < 0.05:
            return {
                'score': 0.6,
                'status': 'FAIR',
                'message': f'Density {density:.4f} is low. May have missed some dependencies.',
                'details': {'density': density}
            }
        
        if density <= 0.3:
            return {
                'score': 1.0,
                'status': 'EXCELLENT',
                'message': f'Density {density:.4f} is in ideal range.',
                'details': {'density': density}
            }
        
        if density <= 0.5:
            return {
                'score': 0.8,
                'status': 'GOOD',
                'message': f'Density {density:.4f} is slightly high. Verify connections are meaningful.',
                'details': {'density': density}
            }
        
        return {
            'score': 0.5,
            'status': 'FAIR',
            'message': f'Density {density:.4f} is very high. May have false positive connections.',
            'details': {'density': density}
        }
    
    def _generate_recommendations(self, metrics: Dict) -> List[str]:
        """Generate actionable recommendations based on metrics."""
        recommendations = []
        
        # Coverage recommendations
        if metrics['coverage']['score'] < 0.5:
            recommendations.append("📄 **Entity Detection**: Consider using LaTeX source instead of PDF for better entity extraction.")
        
        # Connectivity recommendations
        if metrics['connectivity']['score'] < 0.5:
            recommendations.append("🔗 **Dependencies**: Many entities are isolated. Check if \\label and \\ref commands are properly parsed.")
        
        # Structure recommendations
        if metrics['structure_balance']['score'] < 0.6:
            rec = metrics['structure_balance'].get('details', {})
            if rec.get('definitions', 0) == 0:
                recommendations.append("📐 **Definitions**: No definitions found. Ensure \\begin{{definition}} environments are detected.")
            if rec.get('theorems', 0) == 0 and rec.get('lemmas', 0) == 0:
                recommendations.append("🎯 **Main Results**: No theorems or lemmas detected. Verify \\begin{{theorem}} parsing.")
        
        # Completeness recommendations
        if metrics['completeness']['score'] < 0.5:
            recommendations.append("🔍 **Completeness**: High number of isolated nodes. Some \\ref citations may not be resolving to \\label targets.")
        
        # Density recommendations
        if metrics['density']['score'] < 0.5:
            recommendations.append("📊 **Graph Density**: Graph is too sparse. Consider manual review for missed dependencies.")
        elif metrics['density']['score'] > 0.8:
            recommendations.append("⚠️ **Graph Density**: Graph is very dense. Verify that all connections are meaningful and not false positives.")
        
        if not recommendations:
            recommendations.append("✅ **Overall**: Dependency graph quality is good. No major issues detected.")
        
        return recommendations
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 0.9:
            return 'A'
        if score >= 0.8:
            return 'B'
        if score >= 0.7:
            return 'C'
        if score >= 0.6:
            return 'D'
        return 'F'
    
    def export_quality_report(self, output_path: str = "quality_report.json"):
        """Export quality evaluation to JSON file."""
        evaluation = self.evaluate()
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(evaluation, f, indent=2, ensure_ascii=False)
        print(f"Quality report saved to: {output_path}")
    
    def print_quality_summary(self):
        """Print a formatted quality summary to console."""
        result = self.evaluate()
        
        print("\n" + "="*60)
        print("📊 DEPENDENCY GRAPH QUALITY EVALUATION")
        print("="*60)
        
        print(f"\n🎯 OVERALL SCORE: {result['overall_score']}/1.0 (Grade: {result['grade']})")
        
        print("\n📈 DETAILED METRICS:")
        print("-"*40)
        for metric_name, metric_data in result['metrics'].items():
            score_bar = "█" * int(metric_data['score'] * 10) + "░" * (10 - int(metric_data['score'] * 10))
            print(f"  {metric_name.replace('_', ' ').title():20} [{score_bar}] {metric_data['score']:.2f}")
            print(f"    Status: {metric_data['status']} - {metric_data['message']}")
        
        print("\n📋 STATISTICS:")
        print("-"*40)
        stats = result['statistics']
        print(f"  Total Nodes: {stats['total_nodes']}")
        print(f"  Total Edges: {stats['total_edges']}")
        print(f"  Density: {stats['density']}")
        print(f"  Connected: {'Yes' if stats['is_connected'] else 'No'} ({stats['num_components']} components)")
        
        print("\n💡 RECOMMENDATIONS:")
        print("-"*40)
        for rec in result['recommendations']:
            print(f"  • {rec}")
        
        print("\n" + "="*60)


class LLMReviewer:
    """Use LLM (Kimi/Gemini) to generate peer review comments for math papers"""
    
    def __init__(self, kimi_key: Optional[str] = None, gemini_key: Optional[str] = None):
        self.kimi_key = kimi_key
        self.gemini_key = gemini_key
        self.preferred_model = "kimi"  # Default to cheaper model
    
    def _call_kimi(self, prompt: str, max_tokens: int = 4000) -> str:
        """Call Kimi API (Moonshot AI)"""
        if not self.kimi_key:
            raise ValueError("Kimi API key not provided")
        
        url = "https://api.moonshot.cn/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.kimi_key}"
        }
        data = {
            "model": "kimi-latest",
            "messages": [
                {"role": "system", "content": "You are an expert mathematician and peer reviewer. Provide detailed, constructive feedback on mathematical papers."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": max_tokens
        }
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"Kimi API error: {e}")
            raise
    
    def _call_gemini(self, prompt: str, max_tokens: int = 4000) -> str:
        """Call Gemini API (Google)"""
        if not self.gemini_key:
            raise ValueError("Gemini API key not provided")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_key}"
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": max_tokens
            }
        }
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            print(f"Gemini API error: {e}")
            raise
    
    def _call_llm(self, prompt: str, max_tokens: int = 4000, model: Optional[str] = None) -> str:
        """Call LLM with fallback strategy"""
        use_model = model or self.preferred_model
        
        if use_model == "kimi" and self.kimi_key:
            try:
                return self._call_kimi(prompt, max_tokens)
            except Exception as e:
                print(f"Kimi failed, trying Gemini: {e}")
                if self.gemini_key:
                    return self._call_gemini(prompt, max_tokens)
                raise
        elif use_model == "gemini" and self.gemini_key:
            try:
                return self._call_gemini(prompt, max_tokens)
            except Exception as e:
                print(f"Gemini failed, trying Kimi: {e}")
                if self.kimi_key:
                    return self._call_kimi(prompt, max_tokens)
                raise
        else:
            raise ValueError(f"No API key available for model: {use_model}")
    
    def generate_review(self, structure: PaperStructure, full_text: str = "") -> Dict:
        """
        Generate comprehensive peer review in Chinese.
        Returns structured review data.
        """
        print("\n🤖 Generating AI peer review (this may take a minute)...")
        
        # Prepare paper summary for the prompt - limit entities
        entities_summary = []
        for e in structure.entities[:10]:  # Limit to first 10 entities
            entities_summary.append(f"{e.type.upper()}: {e.name}")
        
        prompt = f"""你是一位资深的数学论文审稿人。请对以下数学论文进行详细的同行评议。审稿意见必须用中文撰写。

论文信息：
- 标题：{structure.title or '未提取到标题'}
- 作者：{', '.join(structure.authors) if structure.authors else '未知'}
- 摘要：{structure.abstract[:300] if structure.abstract else '未提取到摘要'}...

提取到的主要数学实体：
{chr(10).join(entities_summary)}

论文统计：
- 定义数量：{len(structure.definitions)}
- 定理数量：{len(structure.theorems)}
- 引理数量：{len(structure.lemmas)}
- 命题数量：{len(structure.propositions)}
- 推论数量：{len(structure.corollaries)}

请按照以下结构提供详细的审稿意见：

## 1. 论文概述与主要贡献
简述文章的主要研究内容和核心定理，评价论文的创新点和学术价值。

## 2. 主要证明方法分析
分析论文使用的主要数学技巧和方法，评价证明思路的清晰度和巧妙性。

## 3. 具体错误与问题
### 3.1 语法和表述错误
数学符号使用不当、语言表达不清晰之处。

### 3.2 逻辑错误与漏洞
论证过程中的逻辑断层、隐含假设未明确说明的地方。

### 3.3 证明中的跳步
需要补充详细论证的步骤、过于简略的证明片段。

## 4. 引用与文献问题
引用他人结论时表述含糊之处、重要参考文献的缺失。

## 5. 改进建议
结构组织、内容补充、写作风格方面的建议。

请确保审稿意见具体且有针对性，避免空泛的评价。语气专业、客观、建设性。
"""
        
        # First call with cheaper model (Kimi)
        try:
            review_text = self._call_llm(prompt, max_tokens=4000, model="kimi")
        except Exception as e:
            print(f"Kimi review failed: {e}")
            review_text = "审稿生成失败。请检查API密钥配置。"
        
        # Parse the review into structured format
        return self._parse_review(review_text)
    
    def _parse_review(self, review_text: str) -> Dict:
        """Parse LLM output into structured review format"""
        review = {
            'raw_text': review_text,
            'sections': {}
        }
        
        # Try to extract sections
        sections_patterns = [
            ("overview", r"## 1[.\s]+论文概述与主要贡献(.*?)## 2"),
            ("methods", r"## 2[.\s]+主要证明方法分析(.*?)## 3"),
            ("errors", r"## 3[.\s]+具体错误与问题(.*?)## 4"),
            ("citations", r"## 4[.\s]+引用与文献问题(.*?)## 5"),
            ("suggestions", r"## 5[.\s]+改进建议(.*?)$"),
        ]
        
        for section_name, pattern in sections_patterns:
            match = re.search(pattern, review_text, re.DOTALL)
            if match:
                review['sections'][section_name] = match.group(1).strip()
        
        return review
    
    def export_review(self, review: Dict, output_path: str = "peer_review.md"):
        """Export peer review to Markdown file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 数学论文同行评议报告\n\n")
            f.write(review['raw_text'])
        print(f"Peer review saved to: {output_path}")
    
    def print_review_summary(self, review: Dict):
        """Print review summary to console"""
        print("\n" + "="*60)
        print("📝 AI PEER REVIEW (中文)")
        print("="*60)
        
        # Print first 1000 chars as preview
        preview = review['raw_text'][:1000]
        print(preview)
        if len(review['raw_text']) > 1000:
            print(f"\n... (完整报告已保存，共 {len(review['raw_text'])} 字符)")
        
        print("\n" + "="*60)


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
        
        # Quality evaluation
        evaluator = GraphQualityEvaluator(structure)
        quality_path = os.path.join(output_dir, "quality_report.json")
        evaluator.export_quality_report(quality_path)
        evaluator.print_quality_summary()
        
        # AI Peer Review (if API keys available)
        try:
            # Try to load API keys from common locations
            kimi_key = None
            gemini_key = None
            
            # Check common key file locations
            key_paths = [
                os.path.expanduser("~/.openclaw/workspace/mycode/kimi_key"),
                os.path.expanduser("~/mycode/kimi_key"),
                "./kimi_key",
            ]
            for path in key_paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        kimi_key = f.read().strip()
                    break
            
            gemini_paths = [
                os.path.expanduser("~/.openclaw/workspace/mycode/gemini_key"),
                os.path.expanduser("~/mycode/gemini_key"),
                "./gemini_key",
            ]
            for path in gemini_paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        gemini_key = f.read().strip()
                    break
            
            if kimi_key or gemini_key:
                reviewer = LLMReviewer(kimi_key=kimi_key, gemini_key=gemini_key)
                review = reviewer.generate_review(structure)
                review_path = os.path.join(output_dir, "peer_review.md")
                reviewer.export_review(review, review_path)
                reviewer.print_review_summary(review)
            else:
                print("\n⚠️  No API keys found. Skipping AI peer review.")
                print("   Set KIMI_KEY or GEMINI_KEY environment variables, or create key files.")
        except Exception as e:
            print(f"\n⚠️  AI peer review failed: {e}")


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
