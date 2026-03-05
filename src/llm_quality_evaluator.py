#!/usr/bin/env python3
"""
LLM Quality Evaluator - Uses LLM to assess parsing and review quality
More nuanced than rule-based evaluation
"""

import json
import os
import urllib.request
from typing import Dict, List, Optional


class LLMQualityEvaluator:
    """Use LLM to evaluate quality of parsing or review"""
    
    def __init__(self, api_key: str, api_type: str = "kimi"):
        self.api_key = api_key
        self.api_type = api_type
    
    def _call_llm(self, prompt: str, max_tokens: int = 2000) -> str:
        """Call LLM API"""
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
                {"role": "system", "content": "You are a quality assessment expert. Evaluate technical work objectively."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
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
    
    def evaluate_parsing(self, original_tex: str, parsed_structure: Dict) -> Dict:
        """Evaluate quality of parsing using LLM"""
        
        # Sample original content (first 3000 chars)
        original_sample = original_tex[:3000]
        
        # Sample parsed elements
        elements_sample = json.dumps(parsed_structure.get('elements', [])[:5], indent=2, ensure_ascii=False)
        
        prompt = f"""Evaluate the quality of LaTeX parsing by comparing original content with extracted structure.

## ORIGINAL CONTENT (Sample):
```latex
{original_sample}
```

## EXTRACTED ELEMENTS (Sample):
```json
{elements_sample}
```

## EVALUATION CRITERIA

1. **Completeness** (0-25 points)
   - Are major theorems/definitions captured?
   - Are equations included?
   - Is the section structure preserved?

2. **Accuracy** (0-25 points)
   - Are theorem statements correctly extracted?
   - Are labels correctly identified?
   - Is the content truncated appropriately?

3. **Structure Preservation** (0-25 points)
   - Is the hierarchy (section/subsection) maintained?
   - Are relationships between elements clear?
   - Can the paper be logically reconstructed?

4. **Usefulness for Review** (0-25 points)
   - Can a reviewer understand the paper from this structure?
   - Are proof sketches or key arguments captured?
   - Is there enough detail for meaningful analysis?

## OUTPUT FORMAT
Return JSON:
{{
  "overall_score": 0-100,
  "grade": "A|B|C|D|F",
  "can_reconstruct": true|false,
  "dimension_scores": {{
    "completeness": 0-25,
    "accuracy": 0-25,
    "structure": 0-25,
    "usefulness": 0-25
  }},
  "findings": {{
    "strengths": ["...", "..."],
    "weaknesses": ["...", "..."],
    "critical_issues": ["...", "..."]
  }},
  "recommendations": ["...", "..."]
}}

Be objective and specific. Cite examples from the content.
"""
        
        try:
            response = self._call_llm(prompt, max_tokens=1500)
            result = json.loads(response)
            return result
        except Exception as e:
            print(f"LLM evaluation failed: {e}")
            return self._fallback_evaluation()
    
    def evaluate_review(self, original_tex: str, review_text: str) -> Dict:
        """Evaluate quality of peer review using LLM"""
        
        # Sample original content
        original_sample = original_tex[:2000]
        
        prompt = f"""Evaluate the quality of this peer review for a mathematical paper.

## ORIGINAL PAPER (Sample):
```latex
{original_sample}
...
```

## PEER REVIEW:
```
{review_text[:4000]}
```

## EVALUATION CRITERIA

1. **Understanding of Paper** (0-20 points)
   - Does the reviewer understand the main contribution?
   - Are the key theorems correctly identified?
   - Is the mathematical context accurate?

2. **Critical Analysis** (0-20 points)
   - Are there specific criticisms of proofs?
   - Are mathematical errors or gaps identified?
   - Is the analysis deep or superficial?

3. **Actionability** (0-20 points)
   - Are suggestions concrete and specific?
   - Can the author act on this feedback?
   - Are locations/theorem numbers provided?

4. **Constructiveness** (0-20 points)
   - Is the tone professional and constructive?
   - Are positive aspects acknowledged?
   - Is the review balanced?

5. **Recommendation Clarity** (0-20 points)
   - Is there a clear accept/reject/revise recommendation?
   - Is the reasoning for the recommendation explained?
   - Are the conditions for acceptance clear?

## OUTPUT FORMAT
Return JSON:
{{
  "overall_score": 0-100,
  "grade": "A|B|C|D|F",
  "is_acceptable": true|false,
  "dimension_scores": {{
    "understanding": 0-20,
    "critical_analysis": 0-20,
    "actionability": 0-20,
    "constructiveness": 0-20,
    "recommendation": 0-20
  }},
  "assessment": {{
    "summary": "Brief assessment of review quality",
    "key_strengths": ["...", "..."],
    "major_weaknesses": ["...", "..."],
    "critical_gaps": ["...", "..."]
  }},
  "improvement_suggestions": ["...", "..."]
}}

Be specific and objective. Quote specific parts of the review if relevant.
"""
        
        try:
            response = self._call_llm(prompt, max_tokens=1500)
            result = json.loads(response)
            return result
        except Exception as e:
            print(f"LLM evaluation failed: {e}")
            return self._fallback_evaluation()
    
    def compare_parsers(self, original_tex: str, parser_results: Dict[str, Dict]) -> Dict:
        """Compare multiple parsers and recommend best"""
        
        results_summary = ""
        for name, result in parser_results.items():
            stats = result.get('metadata', {}).get('stats', {})
            results_summary += f"\n{name}:\n"
            results_summary += f"  Sections: {stats.get('sections', 'N/A')}\n"
            results_summary += f"  Elements: {stats.get('elements', 'N/A')}\n"
            results_summary += f"  Equations: {stats.get('equations', 'N/A')}\n"
        
        prompt = f"""Compare different parsing approaches for this mathematical paper.

## ORIGINAL SAMPLE:
```latex
{original_tex[:1500]}
```

## PARSER RESULTS:
{results_summary}

## TASK
Evaluate which parser would be best for generating a high-quality peer review.

Consider:
1. Completeness (are all key theorems captured?)
2. Accuracy (are statements correctly extracted?)
3. Detail level (is there enough content for analysis?)
4. Structure (is the organization clear?)

## OUTPUT FORMAT
Return JSON:
{{
  "ranking": ["parser_name_1", "parser_name_2", "parser_name_3"],
  "winner": "best_parser_name",
  "justification": "Why this parser is best for peer review generation",
  "concerns": ["Any issues with the winning parser"],
  "recommendation": "Specific advice for using this parser"
}}
"""
        
        try:
            response = self._call_llm(prompt, max_tokens=1200)
            result = json.loads(response)
            return result
        except Exception as e:
            print(f"Comparison failed: {e}")
            return {"error": str(e)}
    
    def _fallback_evaluation(self) -> Dict:
        """Fallback when LLM fails"""
        return {
            "overall_score": 50,
            "grade": "C",
            "can_reconstruct": False,
            "dimension_scores": {
                "completeness": 12,
                "accuracy": 12,
                "structure": 13,
                "usefulness": 13
            },
            "findings": {
                "strengths": ["LLM evaluation unavailable"],
                "weaknesses": ["Could not assess quality"],
                "critical_issues": ["Manual review required"]
            },
            "recommendations": ["Retry with LLM", "Use rule-based evaluation as backup"]
        }
    
    def print_report(self, evaluation: Dict, eval_type: str = "parsing"):
        """Print formatted evaluation report"""
        print("\n" + "="*70)
        print(f"🤖 LLM QUALITY EVALUATION - {eval_type.upper()}")
        print("="*70)
        
        print(f"\n🎯 OVERALL SCORE: {evaluation.get('overall_score', 'N/A')}/100")
        print(f"   Grade: {evaluation.get('grade', 'N/A')}")
        
        if 'can_reconstruct' in evaluation:
            print(f"   Can Reconstruct: {'✅ Yes' if evaluation['can_reconstruct'] else '❌ No'}")
        if 'is_acceptable' in evaluation:
            print(f"   Acceptable: {'✅ Yes' if evaluation['is_acceptable'] else '❌ No'}")
        
        print("\n📊 DIMENSION SCORES:")
        scores = evaluation.get('dimension_scores', {})
        for dim, score in scores.items():
            bar = "█" * int(score / 5) + "░" * (5 - int(score / 5))
            print(f"  {dim:20} [{bar}] {score}")
        
        findings = evaluation.get('findings', evaluation.get('assessment', {}))
        
        if 'strengths' in findings or 'key_strengths' in findings:
            print("\n✅ STRENGTHS:")
            strengths = findings.get('strengths', findings.get('key_strengths', []))
            for s in strengths[:5]:
                print(f"  • {s}")
        
        if 'weaknesses' in findings or 'major_weaknesses' in findings:
            print("\n❌ WEAKNESSES:")
            weaknesses = findings.get('weaknesses', findings.get('major_weaknesses', []))
            for w in weaknesses[:5]:
                print(f"  • {w}")
        
        if 'critical_issues' in findings or 'critical_gaps' in findings:
            print("\n🚨 CRITICAL ISSUES:")
            issues = findings.get('critical_issues', findings.get('critical_gaps', []))
            for i in issues[:5]:
                print(f"  • {i}")
        
        print("\n💡 RECOMMENDATIONS:")
        recs = evaluation.get('recommendations', evaluation.get('improvement_suggestions', []))
        for r in recs[:5]:
            print(f"  • {r}")
        
        print("\n" + "="*70)


def main():
    """Example usage"""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python llm_quality_evaluator.py <type> <file1> [file2]")
        print("  type: parsing | review | compare")
        print("  file1: original tex or review")
        print("  file2: parsed structure (for parsing eval)")
        sys.exit(1)
    
    eval_type = sys.argv[1]
    file1 = sys.argv[2]
    
    # Load API key
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
    
    if not api_key:
        print("Error: No API key found")
        sys.exit(1)
    
    evaluator = LLMQualityEvaluator(api_key=api_key)
    
    if eval_type == "parsing":
        if len(sys.argv) < 4:
            print("Error: Need parsed structure file for parsing evaluation")
            sys.exit(1)
        
        with open(file1, 'r') as f:
            original = f.read()
        with open(sys.argv[3], 'r') as f:
            parsed = json.load(f)
        
        result = evaluator.evaluate_parsing(original, parsed)
        evaluator.print_report(result, "parsing")
        
        # Save report
        output = file1.replace('.tex', '_llm_eval.json')
        with open(output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nReport saved to: {output}")
    
    elif eval_type == "review":
        with open(file1, 'r') as f:
            original = f.read()
        with open(sys.argv[3], 'r') as f:
            review = f.read()
        
        result = evaluator.evaluate_review(original, review)
        evaluator.print_report(result, "review")
    
    else:
        print(f"Unknown evaluation type: {eval_type}")


if __name__ == "__main__":
    main()
