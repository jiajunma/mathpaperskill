#!/usr/bin/env python3
"""
Structured Math Paper Parser - Creates a complete tree representation of mathematical papers.
Can theoretically reconstruct the entire article from the structured data.
"""

import json
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Union
from pathlib import Path
from collections import defaultdict
import copy


@dataclass
class TextSpan:
    """A span of text with type information"""
    type: str  # "text", "math_inline", "math_display", "cite", "ref", "label", "command", "environment"
    content: str
    raw_latex: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List['TextSpan'] = field(default_factory=list)
    
    def to_latex(self) -> str:
        """Reconstruct LaTeX from this span"""
        if self.raw_latex:
            return self.raw_latex
        
        if self.type == "math_inline":
            return f"${self.content}$"
        elif self.type == "math_display":
            return f"\\[{self.content}\\]"
        elif self.type == "cite":
            keys = self.metadata.get("keys", [self.content])
            return f"\\cite{{{','.join(keys)}}}"
        elif self.type == "ref":
            return f"\\ref{{{self.content}}}"
        elif self.type == "eqref":
            return f"\\eqref{{{self.content}}}"
        elif self.type == "label":
            return f"\\label{{{self.content}}}"
        elif self.type == "command":
            cmd = self.metadata.get("command", self.content)
            args = self.metadata.get("args", "")
            return f"\\{cmd}{args}"
        elif self.children:
            return "".join(child.to_latex() for child in self.children)
        else:
            # Escape special LaTeX characters
            content = self.content
            content = content.replace('\\', '\\textbackslash{}')
            content = content.replace('{', '\\{')
            content = content.replace('}', '\\}')
            content = content.replace('$', '\\$')
            content = content.replace('&', '\\&')
            content = content.replace('%', '\\%')
            content = content.replace('#', '\\#')
            content = content.replace('_', '\\_')
            content = content.replace('^', '\\^')
            content = content.replace('~', '\\~{}')
            return content


@dataclass
class Proof:
    """A proof block"""
    content: List[TextSpan] = field(default_factory=list)
    raw_latex: str = ""
    
    def to_latex(self) -> str:
        if self.raw_latex:
            return self.raw_latex
        
        # Handle content - could be list of TextSpans or strings
        if isinstance(self.content, list):
            parts = []
            for item in self.content:
                if isinstance(item, TextSpan):
                    parts.append(item.to_latex())
                elif isinstance(item, str):
                    parts.append(item)
                else:
                    parts.append(str(item))
            content = "".join(parts)
        elif isinstance(self.content, str):
            content = self.content
        else:
            content = str(self.content)
        
        return f"\\begin{{proof}}\n{content}\n\\end{{proof}}"


@dataclass
class MathElement:
    """Base class for numbered mathematical elements"""
    type: str
    number: int
    label: Optional[str] = None
    name: str = ""
    short_name: str = ""
    content: List[TextSpan] = field(default_factory=list)
    raw_latex: str = ""
    line_number: int = 0
    section_path: List[str] = field(default_factory=list)
    
    def to_latex(self) -> str:
        if self.raw_latex:
            return self.raw_latex
        
        # Handle content - could be list of TextSpans or strings
        if isinstance(self.content, list):
            content_parts = []
            for item in self.content:
                if isinstance(item, TextSpan):
                    content_parts.append(item.to_latex())
                elif isinstance(item, str):
                    content_parts.append(item)
                else:
                    content_parts.append(str(item))
            content = "".join(content_parts)
        elif isinstance(self.content, str):
            content = self.content
        else:
            content = str(self.content)
        
        label_str = f"\\label{{{self.label}}}" if self.label else ""
        name_str = f"[{self.name}]" if self.name else ""
        
        return f"\\begin{{{self.type}}}{name_str}\n{label_str}\n{content}\n\\end{{{self.type}}}"


@dataclass
class Theorem(MathElement):
    """Theorem with optional proof"""
    proof: Optional[Proof] = None
    
    def to_latex(self) -> str:
        base = super().to_latex()
        if self.proof:
            base += "\n" + self.proof.to_latex()
        return base


@dataclass
class Definition(MathElement):
    """Definition with term being defined"""
    term: str = ""  # The term being defined (extracted heuristically)
    
    def to_latex(self) -> str:
        return super().to_latex()


@dataclass
class Equation:
    """Numbered or unnumbered equation"""
    type: str = "equation"  # Added type attribute
    number: Optional[int] = None
    label: Optional[str] = None
    content: str = ""  # LaTeX math content
    raw_latex: str = ""
    is_numbered: bool = True
    
    def to_latex(self) -> str:
        if self.raw_latex:
            return self.raw_latex
        
        label_str = f"\\label{{{self.label}}}" if self.label else ""
        env = "equation" if self.is_numbered else "equation*"
        return f"\\begin{{{env}}}\n{label_str}\n{self.content}\n\\end{{{env}}}"


@dataclass
class Paragraph:
    """A paragraph of text"""
    content: List[TextSpan] = field(default_factory=list)
    raw_latex: str = ""
    
    def to_latex(self) -> str:
        if self.raw_latex:
            return self.raw_latex
        
        # Handle content - could be list of TextSpans or strings
        if isinstance(self.content, list):
            parts = []
            for item in self.content:
                if isinstance(item, TextSpan):
                    parts.append(item.to_latex())
                elif isinstance(item, str):
                    parts.append(item)
                else:
                    parts.append(str(item))
            return "".join(parts)
        elif isinstance(self.content, str):
            return self.content
        else:
            return str(self.content)


@dataclass
class Section:
    """A section, subsection, or subsubsection"""
    type: str  # "section", "subsection", "subsubsection"
    title: str
    label: Optional[str] = None
    number: str = ""  # Section number like "1.2"
    paragraphs: List[Paragraph] = field(default_factory=list)
    subsections: List['Section'] = field(default_factory=list)
    elements: List[Union[Theorem, Definition, Equation]] = field(default_factory=list)
    raw_latex: str = ""
    
    def to_latex(self) -> str:
        if self.raw_latex:
            return self.raw_latex
        
        label_str = f"\\label{{{self.label}}}" if self.label else ""
        parts = [
            f"\\{self.type}{{{self.title}}}{label_str}",
        ]
        
        # Add content
        for item in self.paragraphs + self.elements + self.subsections:
            if isinstance(item, Section):
                parts.append(item.to_latex())
            elif hasattr(item, 'to_latex'):
                parts.append(item.to_latex())
        
        return "\n\n".join(parts)


@dataclass
class BibliographyEntry:
    """A bibliography entry"""
    key: str
    entry_type: str  # "article", "book", "phdthesis", etc.
    fields: Dict[str, str] = field(default_factory=dict)
    raw_bibtex: str = ""
    
    def to_bibtex(self) -> str:
        if self.raw_bibtex:
            return self.raw_bibtex
        
        fields_str = ",\n".join(f"  {k} = {{{v}}}" for k, v in self.fields.items())
        return f"@{self.entry_type}{{{self.key},\n{fields_str}\n}}"


@dataclass
class StructuredDocument:
    """Complete structured representation of a mathematical paper"""
    # Metadata
    title: str = ""
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    date: str = ""
    
    # LaTeX technical info
    packages: List[Dict[str, str]] = field(default_factory=list)  # [{name, options}]
    custom_commands: List[str] = field(default_factory=list)
    preamble: str = ""
    
    # Content
    sections: List[Section] = field(default_factory=list)
    
    # Flat collections for easy access
    all_elements: List[Union[Theorem, Definition, Equation]] = field(default_factory=list)
    all_equations: List[Equation] = field(default_factory=list)
    bibliography: List[BibliographyEntry] = field(default_factory=list)
    
    # Cross-reference maps
    label_map: Dict[str, Any] = field(default_factory=dict)  # label -> element
    citation_map: Dict[str, BibliographyEntry] = field(default_factory=dict)  # cite_key -> entry
    
    def to_latex(self) -> str:
        """Reconstruct complete LaTeX document"""
        parts = [
            "\\documentclass[12pt]{article}",
            "% Preamble",
        ]
        
        # Add packages if known
        if self.packages:
            for pkg in self.packages:
                pkg_name = pkg.get('name', '')
                pkg_opts = pkg.get('options', '')
                if pkg_opts:
                    parts.append(f"\\usepackage[{pkg_opts}]{{{pkg_name}}}")
                else:
                    parts.append(f"\\usepackage{{{pkg_name}}}")
        
        # Add custom commands
        if self.custom_commands:
            parts.append("")
            parts.append("% Custom commands")
            for cmd in self.custom_commands:
                parts.append(cmd)
        
        # Add remaining preamble
        if self.preamble:
            parts.append("")
            parts.append("% Additional preamble")
            # Filter out already-added packages
            preamble_lines = self.preamble.split('\n')
            for line in preamble_lines:
                if 'usepackage' not in line and 'documentclass' not in line:
                    parts.append(line)
        
        parts.extend([
            "",
            "\\begin{document}",
            "",
        ])
        
        # Add title
        if self.title:
            parts.append(f"\\title{{{self.title}}}")
        
        # Add authors
        if self.authors:
            authors_str = ' \\and '.join(self.authors)
            parts.append(f"\\author{{{authors_str}}}")
        
        parts.append("\\maketitle")
        parts.append("")
        
        # Add abstract
        if self.abstract:
            parts.append(f"\\begin{{abstract}}")
            parts.append(self.abstract)
            parts.append(f"\\end{{abstract}}")
            parts.append("")
        
        # Add sections
        for section in self.sections:
            parts.append(section.to_latex())
        
        # Add bibliography
        if self.bibliography:
            parts.extend([
                "",
                "\\begin{{thebibliography}}{{{}}}".format(len(self.bibliography)),
            ])
            for entry in self.bibliography:
                parts.append(f"\\bibitem{{{entry.key}}} {self._format_bib_entry(entry)}")
            parts.extend([
                "\\end{{thebibliography}}",
            ])
        
        parts.extend([
            "",
            "\\end{document}",
        ])
        
        return "\n".join(parts)
    
    def _format_bib_entry(self, entry: BibliographyEntry) -> str:
        """Format bibliography entry for thebibliography environment"""
        parts = []
        if "author" in entry.fields:
            parts.append(entry.fields["author"])
        if "title" in entry.fields:
            parts.append(f"\\textit{{{entry.fields['title']}}}")
        if "journal" in entry.fields:
            parts.append(entry.fields["journal"])
        if "year" in entry.fields:
            parts.append(entry.fields["year"])
        return ", ".join(parts)
    
    def save(self, path: str):
        """Save structured document to JSON"""
        data = asdict(self)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        print(f"Structured document saved to: {path}")
    
    @classmethod
    def load(cls, path: str) -> 'StructuredDocument':
        """Load structured document from JSON"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # TODO: Properly reconstruct nested dataclasses
        # For now, return as-is
        doc = cls(**data)
        return doc
    
    def find_by_label(self, label: str) -> Optional[Any]:
        """Find element by label"""
        return self.label_map.get(label)
    
    def find_by_type(self, element_type: str) -> List[Any]:
        """Find all elements of a given type"""
        return [e for e in self.all_elements if e.type == element_type]
    
    def get_dependency_graph(self) -> Dict:
        """Generate dependency graph data"""
        nodes = []
        edges = []
        
        for element in self.all_elements:
            node_id = element.label or f"{element.type}_{element.number}"
            nodes.append({
                "id": node_id,
                "type": element.type,
                "name": element.short_name or element.name,
                "number": element.number,
            })
            
            # Find references in content
            refs = self._extract_refs(element)
            for ref in refs:
                edges.append({"source": node_id, "target": ref})
        
        return {"nodes": nodes, "edges": edges}
    
    def _extract_refs(self, element) -> List[str]:
        """Extract \ref commands from element content"""
        refs = []
        for span in element.content:
            if span.type == "ref":
                refs.append(span.content)
            refs.extend(self._extract_refs_recursive(span))
        return refs
    
    def _extract_refs_recursive(self, span: TextSpan) -> List[str]:
        """Recursively extract refs from children"""
        refs = []
        for child in span.children:
            if child.type == "ref":
                refs.append(child.content)
            refs.extend(self._extract_refs_recursive(child))
        return refs


class StructuredParser:
    """Parser that creates complete structured representation"""
    
    def __init__(self):
        self.doc = StructuredDocument()
        self.counters = defaultdict(int)
        self.current_section: Optional[Section] = None
        self.section_stack: List[Section] = []
    
    def parse_file(self, tex_path: str) -> StructuredDocument:
        """Parse a LaTeX file into structured document"""
        with open(tex_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return self.parse(content)
    
    def parse(self, content: str) -> StructuredDocument:
        """Parse LaTeX content"""
        # Extract preamble
        self._extract_preamble(content)
        
        # Extract document body
        body_match = re.search(r'\\begin\{document\}(.*?)\\end\{document\}', content, re.DOTALL)
        if not body_match:
            raise ValueError("Could not find document environment")
        
        body = body_match.group(1)
        
        # Extract metadata
        self._extract_metadata(body)
        
        # Parse sections
        self.doc.sections = self._parse_sections(body)
        
        # Build indices
        self._build_indices()
        
        return self.doc
    
    def _extract_preamble(self, content: str):
        """Extract preamble and packages"""
        preamble_match = re.search(r'(.*?)\\begin\{document\}', content, re.DOTALL)
        if preamble_match:
            preamble = preamble_match.group(1)
            self.doc.preamble = preamble
            
            # Extract packages
            for match in re.finditer(r'\\usepackage(?:\[(.*?)\])?\{(.*?)\}', preamble):
                options, name = match.groups()
                self.doc.packages.append({
                    "name": name,
                    "options": options or ""
                })
            
            # Extract custom commands
            for match in re.finditer(r'\\newcommand\{(.+?)\}(?:\[(\d+)\])?\{(.+?)\}', preamble, re.DOTALL):
                cmd, nargs, definition = match.groups()
                self.doc.custom_commands.append(
                    f"\\newcommand{{{cmd}}}[{nargs or 0}]{{{definition}}}"
                )
    
    def _extract_metadata(self, body: str):
        """Extract title, authors, abstract from document body"""
        # Title
        title_match = re.search(r'\\title\{(.*?)\}', body, re.DOTALL)
        if title_match:
            self.doc.title = self._clean_latex(title_match.group(1))
        
        # Authors
        for match in re.finditer(r'\\author\{(.*?)\}', body, re.DOTALL):
            author = self._clean_latex(match.group(1))
            self.doc.authors.append(author)
        
        # Abstract
        abstract_match = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', body, re.DOTALL)
        if abstract_match:
            self.doc.abstract = self._clean_latex(abstract_match.group(1))
    
    def _parse_sections(self, body: str) -> List[Section]:
        """Parse sections and their content"""
        sections = []
        
        # Find all sections
        section_pattern = r'\\(section|subsection|subsubsection)(?:\*?)?\{(.*?)\}(?:\s*\\label\{(.*?)\})?'
        
        matches = list(re.finditer(section_pattern, body, re.DOTALL))
        
        for i, match in enumerate(matches):
            sec_type, title, label = match.groups()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            content = body[start:end]
            
            section = self._parse_section_content(sec_type, title, label or "", content)
            sections.append(section)
        
        return sections
    
    def _parse_section_content(self, sec_type: str, title: str, label: str, content: str) -> Section:
        """Parse content within a section"""
        section = Section(
            type=sec_type,
            title=self._clean_latex(title),
            label=label,
            raw_latex=f"\\{sec_type}{{{title}}}{'\\\\label{' + label + '}' if label else ''}"
        )
        
        # Parse theorems, definitions, etc.
        section.elements = self._parse_elements(content)
        
        # Parse paragraphs (text between elements)
        section.paragraphs = self._parse_paragraphs(content)
        
        return section
    
    def _parse_elements(self, content: str) -> List[Union[Theorem, Definition, Equation]]:
        """Parse mathematical elements from content"""
        elements = []
        
        # Patterns for different environments
        patterns = [
            ("theorem", r'\\begin\{theorem\}(?:\[(.*?)\])?(.*?)\\end\{theorem\}'),
            ("definition", r'\\begin\{definition\}(?:\[(.*?)\])?(.*?)\\end\{definition\}'),
            ("lemma", r'\\begin\{lemma\}(?:\[(.*?)\])?(.*?)\\end\{lemma\}'),
            ("proposition", r'\\begin\{proposition\}(?:\[(.*?)\])?(.*?)\\end\{proposition\}'),
            ("corollary", r'\\begin\{corollary\}(?:\[(.*?)\])?(.*?)\\end\{corollary\}'),
            ("remark", r'\\begin\{remark\}(?:\[(.*?)\])?(.*?)\\end\{remark\}'),
            ("equation", r'\\begin\{equation\}(.*?)\\end\{equation\}'),
            ("equation_star", r'\\begin\{equation\*\}(.*?)\\end\{equation\*}'),
        ]
        
        for env_type, pattern in patterns:
            for match in re.finditer(pattern, content, re.DOTALL):
                if env_type in ["equation", "equation_star"]:
                    eq_content = match.group(1).strip()
                    label_match = re.search(r'\\label\{(.*?)\}', eq_content)
                    label = label_match.group(1) if label_match else None
                    
                    self.counters["equation"] += 1
                    eq = Equation(
                        number=self.counters["equation"],
                        label=label,
                        content=re.sub(r'\\label\{.*?\}', '', eq_content).strip(),
                        is_numbered=(env_type == "equation"),
                        raw_latex=match.group(0)
                    )
                    elements.append(eq)
                    self.doc.all_equations.append(eq)
                else:
                    name = match.group(1) if match.group(1) else ""
                    body = match.group(2) if len(match.groups()) > 1 and match.group(2) else match.group(1)
                    
                    label_match = re.search(r'\\label\{(.*?)\}', body)
                    label = label_match.group(1) if label_match else None
                    
                    self.counters[env_type] += 1
                    
                    # Extract proof if exists
                    proof = None
                    proof_match = re.search(r'\\begin\{proof\}(.*?)\\end\{proof\}', body, re.DOTALL)
                    if proof_match:
                        proof_content = proof_match.group(1)
                        proof = Proof(
                            content=self._parse_text_spans(proof_content),
                            raw_latex=proof_match.group(0)
                        )
                        body = body[:proof_match.start()] + body[proof_match.end():]
                    
                    element = MathElement(
                        type=env_type,
                        number=self.counters[env_type],
                        label=label,
                        name=name,
                        content=self._parse_text_spans(body),
                        raw_latex=match.group(0)
                    )
                    elements.append(element)
        
        # Sort by position in document
        elements.sort(key=lambda x: x.line_number if hasattr(x, 'line_number') else 0)
        return elements
    
    def _parse_paragraphs(self, content: str) -> List[Paragraph]:
        """Parse text paragraphs"""
        paragraphs = []
        
        # Split by double newline or environment boundaries
        # Remove environment content first
        clean_content = re.sub(r'\\begin\{.*?\}.*?\\end\{.*?\}', '', content, flags=re.DOTALL)
        
        for para_text in clean_content.split('\n\n'):
            para_text = para_text.strip()
            if para_text and not para_text.startswith('\\'):
                paragraphs.append(Paragraph(
                    content=self._parse_text_spans(para_text),
                    raw_latex=para_text
                ))
        
        return paragraphs
    
    def _parse_text_spans(self, text: str) -> List[TextSpan]:
        """Parse text into spans with type information"""
        spans = []
        
        # Pattern to match various LaTeX constructs
        patterns = [
            ("math_display", r'\\\[(.*?)\\\]'),
            ("math_inline", r'\$(.+?)\$'),
            ("cite", r'\\cite(?:\[(.*?)\])?\{(.*?)\}'),
            ("ref", r'\\(?:ref|eqref)\{(.*?)\}'),
            ("label", r'\\label\{(.*?)\}'),
        ]
        
        # Simple parsing - can be improved
        # For now, just create a single text span
        spans.append(TextSpan(
            type="text",
            content=self._clean_latex(text),
            raw_latex=text
        ))
        
        return spans
    
    def _build_indices(self):
        """Build label map and other indices"""
        for section in self.doc.sections:
            self._index_section(section)
    
    def _index_section(self, section: Section):
        """Recursively index a section"""
        if section.label:
            self.doc.label_map[section.label] = section
        
        for element in section.elements:
            self.doc.all_elements.append(element)
            if element.label:
                self.doc.label_map[element.label] = element
        
        for subsection in section.subsections:
            self._index_section(subsection)
    
    def _clean_latex(self, text: str) -> str:
        """Clean LaTeX markup"""
        # Remove comments
        text = re.sub(r'(?<!\\)%.*$', '', text, flags=re.MULTILINE)
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text.strip()


def main():
    """Example usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python structured_parser.py <tex_file>")
        return
    
    parser = StructuredParser()
    doc = parser.parse_file(sys.argv[1])
    
    # Save structured data
    output_path = sys.argv[1].replace('.tex', '_structured.json')
    doc.save(output_path)
    
    # Generate LaTeX reconstruction
    latex_path = sys.argv[1].replace('.tex', '_reconstructed.tex')
    with open(latex_path, 'w') as f:
        f.write(doc.to_latex())
    
    print(f"\n✅ Parsed {len(doc.all_elements)} mathematical elements")
    print(f"✅ Found {len(doc.all_equations)} equations")
    print(f"✅ Document structure has {len(doc.sections)} main sections")


if __name__ == "__main__":
    main()
