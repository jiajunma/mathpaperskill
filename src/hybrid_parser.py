#!/usr/bin/env python3
"""
Hybrid Parser - Combines regex speed with LLM accuracy
Uses regex for simple structures, LLM for complex/ambiguous cases
"""

import json
import re
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from collections import defaultdict
import urllib.request


@dataclass
class ParseCandidate:
    """A candidate element from regex parsing"""
    element_type: str
    content: str
    start_pos: int
    end_pos: int
    confidence: float = 0.0  # Regex confidence score
    needs_verification: bool = False


class HybridParser:
    """
    Hybrid parsing strategy:
    1. Fast regex pass extracts candidates
    2. LLM verifies ambiguous/complex candidates
    3. LLM handles nested structures regex can't parse
    """
    
    def __init__(self, api_key: Optional[str] = None, api_type: str = "kimi"):
        self.api_key = api_key
        self.api_type = api_type
        self.use_llm = api_key is not None
        
        # Regex patterns for initial extraction
        self.patterns = {
            'section': r'\\(section|subsection|subsubsection)(?:\*?)?\{([^}]+)\}',
            'theorem_env': r'\\begin\{(theorem|lemma|proposition|corollary|definition)\}(?:\[([^\]]*)\])?(.*?)\\end\{\1\}',
            'equation': r'\\begin\{equation\}(.*?)\\end\{equation\}',
            'equation_star': r'\\begin\{equation\*\}(.*?)\\end\{equation\*}',
            'label': r'\\label\{([^}]+)\}',
            'ref': r'\\(ref|eqref)\{([^}]+)\}',
            'cite': r'\\cite(?:\[([^\]]*)\])?\{([^}]+)\}',
        }
    
    def _call_llm(self, prompt: str, max_tokens: int = 1500) -> str:
        """Call LLM for verification or complex parsing"""
        if not self.use_llm:
            raise ValueError("No API key provided")
        
        if self.api_type == "kimi":
            return self._call_kimi(prompt, max_tokens)
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
                {"role": "system", "content": "You verify and correct LaTeX parsing. Be concise."},
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
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    
    def regex_extract(self, tex_content: str) -> Dict[str, List[ParseCandidate]]:
        """Fast regex extraction phase"""
        print("Phase 1: Regex extraction...")
        
        candidates = defaultdict(list)
        
        # Extract sections
        for match in re.finditer(self.patterns['section'], tex_content):
            level, title = match.groups()
            candidates['sections'].append(ParseCandidate(
                element_type=level,
                content=title,
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.9
            ))
        
        # Extract theorem-like environments
        for match in re.finditer(self.patterns['theorem_env'], tex_content, re.DOTALL):
            env_type, name, body = match.groups()
            
            # Check if complex (nested environments, difficult to parse)
            is_complex = self._is_complex_content(body)
            
            candidates['elements'].append(ParseCandidate(
                element_type=env_type,
                content=body.strip(),
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.7 if not is_complex else 0.4,
                needs_verification=is_complex
            ))
        
        # Extract equations
        for match in re.finditer(self.patterns['equation'], tex_content, re.DOTALL):
            candidates['equations'].append(ParseCandidate(
                element_type='equation',
                content=match.group(1).strip(),
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.8
            ))
        
        for match in re.finditer(self.patterns['equation_star'], tex_content, re.DOTALL):
            candidates['equations'].append(ParseCandidate(
                element_type='equation_star',
                content=match.group(1).strip(),
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.8
            ))
        
        # Extract all labels
        for match in re.finditer(self.patterns['label'], tex_content):
            candidates['labels'].append(ParseCandidate(
                element_type='label',
                content=match.group(1),
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.95
            ))
        
        # Extract all refs
        for match in re.finditer(self.patterns['ref'], tex_content):
            ref_type, label = match.groups()
            candidates['refs'].append(ParseCandidate(
                element_type=ref_type,
                content=label,
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.95
            ))
        
        print(f"  Found {len(candidates['sections'])} sections")
        print(f"  Found {len(candidates['elements'])} theorem-like elements")
        print(f"  Found {len(candidates['equations'])} equations")
        print(f"  Found {len(candidates['labels'])} labels")
        
        needs_verification = sum(1 for e in candidates['elements'] if e.needs_verification)
        print(f"  {needs_verification} elements need LLM verification")
        
        return dict(candidates)
    
    def _is_complex_content(self, content: str) -> bool:
        """Determine if content is too complex for regex"""
        # Check for nested environments
        nested_envs = len(re.findall(r'\\begin\{', content)) > 1
        
        # Check for tikz/circuit diagrams
        has_graphics = 'tikzpicture' in content or 'circuit' in content
        
        # Check for very long content (likely complex)
        is_long = len(content) > 2000
        
        # Check for unbalanced braces (indicates parsing error)
        brace_count = content.count('{') - content.count('}')
        unbalanced = brace_count != 0
        
        return nested_envs or has_graphics or is_long or unbalanced
    
    def llm_verify(self, candidate: ParseCandidate, context: str = "") -> Dict:
        """Use LLM to verify and enrich a candidate"""
        if not self.use_llm:
            return self._fallback_verify(candidate)
        
        prompt = f"""Verify and extract structured information from this LaTeX {candidate.element_type}.

CONTENT:
```latex
{candidate.content[:3000]}
```

CONTEXT (surrounding text):
```latex
{context[:500]}
```

Extract and return JSON:
{{
  "is_valid": true/false,  // Is this a correctly parsed element?
  "type": "theorem|lemma|proposition|corollary|definition",
  "number": "string or null",
  "label": "string or null",
  "name": "optional name from [Name]",
  "statement": "first 200 chars of statement",
  "has_proof": true/false,
  "issues": ["any parsing issues found"]
}}
"""
        
        try:
            response = self._call_llm(prompt, max_tokens=800)
            result = json.loads(response)
            return result
        except Exception as e:
            print(f"    LLM verification failed: {e}")
            return self._fallback_verify(candidate)
    
    def _fallback_verify(self, candidate: ParseCandidate) -> Dict:
        """Fallback when LLM is not available"""
        return {
            "is_valid": True,
            "type": candidate.element_type,
            "number": None,
            "label": None,
            "name": "",
            "statement": candidate.content[:200],
            "has_proof": False,
            "issues": ["Not verified by LLM"]
        }
    
    def llm_parse_complex(self, tex_content: str, problem_areas: List[Tuple[int, int]]) -> List[Dict]:
        """Use LLM to parse complex areas regex couldn't handle"""
        if not self.use_llm or not problem_areas:
            return []
        
        print(f"Phase 3: LLM parsing {len(problem_areas)} complex areas...")
        
        results = []
        for i, (start, end) in enumerate(problem_areas):
            chunk = tex_content[start:end]
            
            prompt = f"""Parse this complex LaTeX section. Extract all theorems, definitions, lemmas.

CONTENT:
```latex
{chunk[:4000]}
```

Return JSON array of elements:
[
  {{
    "type": "theorem|lemma|definition",
    "label": "...",
    "name": "...",
    "statement": "...",
    "position": "start offset in text"
  }}
]
"""
            
            try:
                response = self._call_llm(prompt, max_tokens=1500)
                elements = json.loads(response)
                if isinstance(elements, list):
                    for elem in elements:
                        elem['source'] = 'llm_complex_parse'
                    results.extend(elements)
                    print(f"  Area {i+1}: Found {len(elements)} elements")
            except Exception as e:
                print(f"  Area {i+1}: Failed - {e}")
        
        return results
    
    def find_problem_areas(self, tex_content: str) -> List[Tuple[int, int]]:
        """Find areas where regex parsing likely failed"""
        problem_areas = []
        
        # Find unclosed environments
        env_starts = [(m.start(), m.group(1)) for m in re.finditer(r'\\begin\{([^}]+)\}', tex_content)]
        env_ends = [(m.start(), m.group(1)) for m in re.finditer(r'\\end\{([^}]+)\}', tex_content)]
        
        # Simple check for mismatched environments
        stack = []
        for pos, env_name in sorted(env_starts + env_ends, key=lambda x: x[0]):
            if (pos, env_name) in env_starts:
                stack.append((pos, env_name))
            else:
                if stack and stack[-1][1] == env_name:
                    stack.pop()
                else:
                    # Mismatch found
                    problem_areas.append((max(0, pos - 500), min(len(tex_content), pos + 500)))
        
        # Remove duplicates and overlapping areas
        problem_areas = self._merge_overlapping_areas(problem_areas)
        
        return problem_areas[:5]  # Limit to 5 areas to control cost
    
    def _merge_overlapping_areas(self, areas: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Merge overlapping problem areas"""
        if not areas:
            return []
        
        # Sort by start position
        areas = sorted(areas, key=lambda x: x[0])
        
        merged = [areas[0]]
        for current in areas[1:]:
            last = merged[-1]
            if current[0] <= last[1]:  # Overlapping
                merged[-1] = (last[0], max(last[1], current[1]))
            else:
                merged.append(current)
        
        return merged
    
    def parse(self, tex_path: str, output_path: Optional[str] = None) -> Dict:
        """Main parsing pipeline"""
        print(f"\n{'='*70}")
        print("🔧 HYBRID PARSER")
        print(f"{'='*70}")
        print(f"File: {tex_path}")
        print(f"LLM enabled: {'Yes' if self.use_llm else 'No'}")
        
        # Read file
        with open(tex_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Extract document body
        body_match = re.search(r'\\begin\{document\}(.*?)\\end\{document\}', content, re.DOTALL)
        if body_match:
            body = body_match.group(1)
        else:
            body = content
        
        # Phase 1: Regex extraction
        candidates = self.regex_extract(body)
        
        # Phase 2: LLM verification for uncertain candidates
        verified_elements = []
        
        if self.use_llm:
            print("\nPhase 2: LLM verification...")
            to_verify = [e for e in candidates.get('elements', []) if e.needs_verification]
            
            for i, candidate in enumerate(to_verify[:10]):  # Limit to 10 to control cost
                print(f"  Verifying element {i+1}/{len(to_verify)}...")
                verified = self.llm_verify(candidate)
                if verified.get('is_valid', True):
                    verified_elements.append(verified)
        
        # Phase 3: LLM parsing for problem areas
        complex_elements = []
        if self.use_llm:
            problem_areas = self.find_problem_areas(body)
            if problem_areas:
                complex_elements = self.llm_parse_complex(body, problem_areas)
        
        # Combine results
        result = {
            "metadata": {
                "source_file": tex_path,
                "parsing_strategy": "hybrid",
                "llm_used": self.use_llm,
                "stats": {
                    "sections": len(candidates.get('sections', [])),
                    "elements_regex": len(candidates.get('elements', [])),
                    "elements_verified": len(verified_elements),
                    "elements_complex": len(complex_elements),
                    "equations": len(candidates.get('equations', [])),
                    "labels": len(candidates.get('labels', [])),
                    "refs": len(candidates.get('refs', [])),
                }
            },
            "sections": [
                {
                    "type": c.element_type,
                    "title": c.content,
                    "position": c.start_pos
                }
                for c in candidates.get('sections', [])
            ],
            "elements_regex": [
                {
                    "type": c.element_type,
                    "content": c.content[:500],
                    "confidence": c.confidence,
                    "needs_verification": c.needs_verification
                }
                for c in candidates.get('elements', [])
            ],
            "elements_verified": verified_elements,
            "elements_complex": complex_elements,
            "equations": [
                {
                    "type": c.element_type,
                    "content": c.content[:300]
                }
                for c in candidates.get('equations', [])
            ],
            "labels": list(set(c.content for c in candidates.get('labels', []))),
            "refs": list(set(c.content for c in candidates.get('refs', []))),
        }
        
        # Save if output path provided
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n✅ Results saved to: {output_path}")
        
        # Print summary
        print(f"\n{'='*70}")
        print("📊 PARSING SUMMARY")
        print(f"{'='*70}")
        stats = result['metadata']['stats']
        print(f"Sections: {stats['sections']}")
        print(f"Elements (regex): {stats['elements_regex']}")
        print(f"Elements (LLM verified): {stats['elements_verified']}")
        print(f"Elements (complex parsed): {stats['elements_complex']}")
        print(f"Total unique elements: {stats['elements_regex'] + stats['elements_complex']}")
        print(f"Equations: {stats['equations']}")
        print(f"Labels: {stats['labels']}")
        print(f"References: {stats['refs']}")
        
        return result


def main():
    """Example usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python hybrid_parser.py <tex_file> [output.json]")
        print("       Set KIMI_KEY environment variable for LLM mode")
        sys.exit(1)
    
    tex_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else tex_file.replace('.tex', '_hybrid.json')
    
    # Try to load API key
    api_key = os.environ.get('KIMI_KEY')
    if not api_key:
        key_paths = [
            os.path.expanduser("~/.openclaw/workspace/mycode/kimi_key"),
            "./kimi_key",
        ]
        for path in key_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    api_key = f.read().strip()
                break
    
    # Create parser
    parser = HybridParser(api_key=api_key, api_type="kimi" if api_key else None)
    
    # Parse
    result = parser.parse(tex_file, output_file)


if __name__ == "__main__":
    main()
