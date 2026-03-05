#!/usr/bin/env python3
"""
LLM-Based Structured Parser - Uses LLM to intelligently parse LaTeX documents
Slices document into chunks to control prompt length
"""

import json
import re
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Tuple
from collections import defaultdict
import urllib.request


@dataclass
class ChunkParseResult:
    """Result of parsing a single chunk"""
    chunk_index: int
    sections: List[Dict]
    elements: List[Dict]
    equations: List[Dict]
    citations: List[Dict]
    labels: List[str]
    refs: List[str]


class LLMParser:
    """Parser that uses LLM to extract structure from LaTeX chunks"""
    
    def __init__(self, api_key: str, api_type: str = "kimi"):
        self.api_key = api_key
        self.api_type = api_type
        self.max_chunk_tokens = 3000  # Leave room for response
    
    def _call_llm(self, prompt: str, max_tokens: int = 2000) -> str:
        """Call LLM API"""
        if self.api_type == "kimi":
            return self._call_kimi(prompt, max_tokens)
        elif self.api_type == "siliconflow":
            return self._call_siliconflow(prompt, max_tokens)
        else:
            raise ValueError(f"Unknown API type: {self.api_type}")
    
    def _call_kimi(self, prompt: str, max_tokens: int) -> str:
        """Call Kimi API"""
        url = "https://api.moonshot.cn/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        data = {
            "model": "kimi-latest",
            "messages": [
                {"role": "system", "content": "You are a LaTeX parsing expert. Extract structured information from mathematical papers."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"}
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    
    def _call_siliconflow(self, prompt: str, max_tokens: int) -> str:
        """Call Silicon Flow API"""
        url = "https://api.siliconflow.cn/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-ai/deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are a LaTeX parsing expert. Extract structured information from mathematical papers."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"}
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    
    def slice_document(self, tex_content: str, max_chars: int = 8000) -> List[str]:
        """
        Slice document into manageable chunks.
        Tries to slice at natural boundaries (sections, environments).
        """
        chunks = []
        
        # First, try to split by major sections
        section_pattern = r'(\\section\{[^}]+\})'
        sections = re.split(section_pattern, tex_content)
        
        current_chunk = sections[0] if sections else ""  # Preamble
        
        for i in range(1, len(sections), 2):
            if i < len(sections):
                section_header = sections[i]
                section_content = sections[i+1] if i+1 < len(sections) else ""
                
                section_text = section_header + section_content
                
                # If adding this section exceeds limit, save current and start new
                if len(current_chunk) + len(section_text) > max_chars and len(current_chunk) > 1000:
                    chunks.append(current_chunk)
                    current_chunk = section_text
                else:
                    current_chunk += section_text
        
        # Add remaining content
        if current_chunk:
            chunks.append(current_chunk)
        
        # If any chunk is still too large, split by environments
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > max_chars:
                final_chunks.extend(self._split_by_environments(chunk, max_chars))
            else:
                final_chunks.append(chunk)
        
        return final_chunks
    
    def _split_by_environments(self, text: str, max_chars: int) -> List[str]:
        """Split text by theorem/definition environments"""
        chunks = []
        
        # Pattern to match theorem-like environments
        env_pattern = r'(\\begin\{(theorem|definition|lemma|proposition|corollary)\}.*?\\end\{\2\})'
        
        parts = re.split(env_pattern, text, flags=re.DOTALL)
        
        current_chunk = ""
        for part in parts:
            if len(current_chunk) + len(part) > max_chars and len(current_chunk) > 500:
                chunks.append(current_chunk)
                current_chunk = part
            else:
                current_chunk += part
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def parse_chunk(self, chunk: str, chunk_index: int) -> ChunkParseResult:
        """Parse a single chunk using LLM"""
        
        prompt = f"""Parse the following LaTeX content and extract structured information.

## LaTeX CONTENT (Chunk {chunk_index}):
```latex
{chunk[:6000]}  # Limit input size
```

## INSTRUCTIONS
Extract the following and return as JSON:

1. **sections**: List of sections/subsections found in this chunk
   - type: "section", "subsection", or "subsubsection"
   - title: The section title
   - label: Any \\label{{...}} in the section (if present)

2. **elements**: List of theorem-like environments
   - type: "theorem", "definition", "lemma", "proposition", "corollary", "remark"
   - number: The theorem number (if numbered)
   - label: The \\label{{...}} content
   - name: Optional name from [Name] argument
   - statement: The statement content (first 200 chars)
   - has_proof: true if \\begin{{proof}} follows

3. **equations**: List of numbered equations
   - number: Equation number
   - label: The \\label{{...}} content
   - content: The equation content (LaTeX)

4. **citations**: List of \\cite{{...}} found
   - keys: List of citation keys

5. **labels**: All \\label{{...}} labels defined in this chunk

6. **refs**: All \\ref{{...}} or \\eqref{{...}} references in this chunk

Return ONLY valid JSON in this format:
{{
  "sections": [...],
  "elements": [...],
  "equations": [...],
  "citations": [...],
  "labels": [...],
  "refs": [...]
}}
"""
        
        try:
            response = self._call_llm(prompt, max_tokens=2000)
            data = json.loads(response)
            
            return ChunkParseResult(
                chunk_index=chunk_index,
                sections=data.get("sections", []),
                elements=data.get("elements", []),
                equations=data.get("equations", []),
                citations=data.get("citations", []),
                labels=data.get("labels", []),
                refs=data.get("refs", [])
            )
        except Exception as e:
            print(f"Error parsing chunk {chunk_index}: {e}")
            return ChunkParseResult(
                chunk_index=chunk_index,
                sections=[], elements=[], equations=[], citations=[],
                labels=[], refs=[]
            )
    
    def merge_results(self, results: List[ChunkParseResult]) -> Dict:
        """Merge results from multiple chunks"""
        merged = {
            "sections": [],
            "elements": [],
            "equations": [],
            "citations": [],
            "labels": set(),
            "refs": set(),
        }
        
        seen_labels = set()
        
        for result in results:
            # Merge sections (avoid duplicates by label)
            for sec in result.sections:
                if sec.get("label") not in seen_labels:
                    merged["sections"].append(sec)
                    if sec.get("label"):
                        seen_labels.add(sec["label"])
            
            # Merge elements (avoid duplicates by label)
            for elem in result.elements:
                if elem.get("label") not in seen_labels:
                    merged["elements"].append(elem)
                    if elem.get("label"):
                        seen_labels.add(elem["label"])
            
            # Merge equations
            for eq in result.equations:
                if eq.get("label") not in seen_labels:
                    merged["equations"].append(eq)
                    if eq.get("label"):
                        seen_labels.add(eq["label"])
            
            # Merge citations
            merged["citations"].extend(result.citations)
            
            # Merge labels and refs
            merged["labels"].update(result.labels)
            merged["refs"].update(result.refs)
        
        # Convert sets to lists for JSON serialization
        merged["labels"] = list(merged["labels"])
        merged["refs"] = list(merged["refs"])
        
        return merged
    
    def parse_file(self, tex_path: str, output_path: Optional[str] = None) -> Dict:
        """Parse a LaTeX file using LLM-based chunking"""
        print(f"Reading {tex_path}...")
        with open(tex_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Extract document body
        body_match = re.search(r'\\begin\{document\}(.*?)\\end\{document\}', content, re.DOTALL)
        if body_match:
            body = body_match.group(1)
        else:
            body = content
        
        print("Slicing document...")
        chunks = self.slice_document(body)
        print(f"Created {len(chunks)} chunks")
        
        print("Parsing chunks with LLM...")
        results = []
        for i, chunk in enumerate(chunks):
            print(f"  Parsing chunk {i+1}/{len(chunks)}...")
            result = self.parse_chunk(chunk, i)
            results.append(result)
        
        print("Merging results...")
        merged = self.merge_results(results)
        
        # Add metadata
        merged["metadata"] = {
            "source_file": tex_path,
            "num_chunks": len(chunks),
            "total_elements": len(merged["elements"]),
            "total_equations": len(merged["equations"]),
            "total_sections": len(merged["sections"]),
        }
        
        # Save if output path provided
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(merged, f, indent=2, ensure_ascii=False)
            print(f"Saved to {output_path}")
        
        return merged


def main():
    """Example usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python llm_parser.py <tex_file> [output.json]")
        sys.exit(1)
    
    tex_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else tex_file.replace('.tex', '_llm_parsed.json')
    
    # Load API key
    api_key = None
    key_paths = [
        os.path.expanduser("~/.openclaw/workspace/mycode/kimi_key"),
        "./kimi_key",
    ]
    for path in key_paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                api_key = f.read().strip()
            break
    
    if not api_key:
        print("Error: No API key found")
        sys.exit(1)
    
    parser = LLMParser(api_key=api_key, api_type="kimi")
    result = parser.parse_file(tex_file, output_file)
    
    print("\n=== Parsing Summary ===")
    print(f"Sections: {len(result['sections'])}")
    print(f"Elements: {len(result['elements'])}")
    print(f"Equations: {len(result['equations'])}")
    print(f"Unique labels: {len(result['labels'])}")
    print(f"References: {len(result['refs'])}")


if __name__ == "__main__":
    main()
