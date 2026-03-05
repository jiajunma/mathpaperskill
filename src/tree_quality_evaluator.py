#!/usr/bin/env python3
"""
Tree Structure Quality Evaluator - Validates the structured document tree
Ensures the tree accurately represents the original paper and can reconstruct it
"""

import re
import json
import difflib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict
import hashlib


@dataclass
class TreeQualityMetrics:
    """Metrics for tree structure quality"""
    # Completeness
    preamble_coverage: float = 0.0  # % of preamble elements captured
    section_coverage: float = 0.0   # % of sections captured
    element_coverage: float = 0.0   # % of theorems/defs/etc captured
    equation_coverage: float = 0.0  # % of equations captured
    citation_coverage: float = 0.0  # % of citations captured
    
    # Accuracy
    label_resolution_rate: float = 0.0  # % of \ref that resolve to existing labels
    cross_reference_accuracy: float = 0.0  # % of correct cross-refs
    section_hierarchy_correct: bool = False
    
    # Reconstructibility
    reconstruction_similarity: float = 0.0  # Text similarity % after reconstruction
    math_content_preserved: bool = False
    theorem_statements_complete: bool = False
    
    # Structural Integrity
    no_orphaned_nodes: bool = False  # All elements reachable from root
    no_dangling_refs: bool = False   # All \ref point to existing labels
    proper_nesting: bool = False      # Sections properly nested
    
    # Overall
    overall_score: int = 0
    grade: str = "F"
    can_reconstruct: bool = False


class TreeQualityEvaluator:
    """Evaluate the quality of structured document tree"""
    
    def __init__(self, original_tex: str, structured_doc: Any):
        self.original_tex = original_tex
        self.doc = structured_doc
        self.metrics = TreeQualityMetrics()
        self.issues = []
        self.warnings = []
    
    def evaluate(self) -> TreeQualityMetrics:
        """Perform comprehensive tree quality evaluation"""
        self._check_completeness()
        self._check_accuracy()
        self._check_reconstructibility()
        self._check_structural_integrity()
        self._calculate_score()
        return self.metrics
    
    def _check_completeness(self):
        """Check if all elements from original are captured"""
        # Count elements in original
        original_counts = self._count_original_elements()
        
        # Count elements in tree
        tree_counts = {
            'sections': len(self.doc.sections),
            'theorems': len(self.doc.all_elements),
            'equations': len(self.doc.all_equations),
            'citations': len(self.doc.bibliography),
        }
        
        # Calculate coverage
        if original_counts['sections'] > 0:
            self.metrics.section_coverage = tree_counts['sections'] / original_counts['sections']
        
        if original_counts['theorems'] > 0:
            self.metrics.element_coverage = tree_counts['theorems'] / original_counts['theorems']
        
        if original_counts['equations'] > 0:
            self.metrics.equation_coverage = tree_counts['equations'] / original_counts['equations']
        
        if original_counts['citations'] > 0:
            self.metrics.citation_coverage = tree_counts['citations'] / original_counts['citations']
        
        # Check coverage thresholds
        if self.metrics.section_coverage < 0.9:
            self.issues.append(f"Section coverage low: {self.metrics.section_coverage:.1%}")
        if self.metrics.element_coverage < 0.8:
            self.issues.append(f"Element coverage low: {self.metrics.element_coverage:.1%}")
        if self.metrics.equation_coverage < 0.7:
            self.issues.append(f"Equation coverage low: {self.metrics.equation_coverage:.1%}")
    
    def _count_original_elements(self) -> Dict[str, int]:
        """Count elements in original LaTeX"""
        counts = {
            'sections': len(re.findall(r'\\section\{', self.original_tex)),
            'subsections': len(re.findall(r'\\subsection\{', self.original_tex)),
            'theorems': len(re.findall(r'\\begin\{theorem\}', self.original_tex)),
            'definitions': len(re.findall(r'\\begin\{definition\}', self.original_tex)),
            'lemmas': len(re.findall(r'\\begin\{lemma\}', self.original_tex)),
            'propositions': len(re.findall(r'\\begin\{proposition\}', self.original_tex)),
            'corollaries': len(re.findall(r'\\begin\{corollary\}', self.original_tex)),
            'equations': len(re.findall(r'\\begin\{equation\}', self.original_tex)),
            'citations': len(re.findall(r'\\cite\{', self.original_tex)),
        }
        # Total theorems + definitions + etc
        counts['theorems'] = sum([
            counts['theorems'],
            counts['definitions'],
            counts['lemmas'],
            counts['propositions'],
            counts['corollaries']
        ])
        return counts
    
    def _check_accuracy(self):
        """Check if parsed elements are accurate"""
        # Check label resolution
        all_labels = set(self.doc.label_map.keys())
        
        # Find all \ref in original
        refs_in_original = set(re.findall(r'\\(?:ref|eqref)\{([^}]+)\}', self.original_tex))
        
        if refs_in_original:
            resolved = len(refs_in_original.intersection(all_labels))
            self.metrics.label_resolution_rate = resolved / len(refs_in_original)
            
            unresolved = refs_in_original - all_labels
            if unresolved:
                self.warnings.append(f"Unresolved references: {unresolved}")
        
        # Check section hierarchy
        self.metrics.section_hierarchy_correct = self._verify_section_hierarchy()
    
    def _verify_section_hierarchy(self) -> bool:
        """Verify section nesting is correct"""
        def check_sections(sections, expected_level=1):
            for sec in sections:
                if sec.type == "section" and expected_level != 1:
                    return False
                if sec.type == "subsection" and expected_level != 2:
                    return False
                if sec.type == "subsubsection" and expected_level != 3:
                    return False
                if not check_sections(sec.subsections, expected_level + 1):
                    return False
            return True
        
        return check_sections(self.doc.sections)
    
    def _check_reconstructibility(self):
        """Check if tree can reconstruct original accurately"""
        try:
            # Attempt reconstruction
            reconstructed = self.doc.to_latex()
            
            # Calculate similarity
            self.metrics.reconstruction_similarity = self._calculate_similarity(
                self.original_tex, reconstructed
            )
            
            # Check if math content is preserved
            self.metrics.math_content_preserved = self._check_math_preserved()
            
            # Check theorem statements
            self.metrics.theorem_statements_complete = self._check_theorems_complete()
            
        except Exception as e:
            self.issues.append(f"Reconstruction failed: {e}")
            self.metrics.reconstruction_similarity = 0.0
    
    def _calculate_similarity(self, original: str, reconstructed: str) -> float:
        """Calculate text similarity between original and reconstructed"""
        # Normalize both texts
        orig_normalized = self._normalize_for_comparison(original)
        recon_normalized = self._normalize_for_comparison(reconstructed)
        
        # Use SequenceMatcher for similarity
        matcher = difflib.SequenceMatcher(None, orig_normalized, recon_normalized)
        return matcher.ratio()
    
    def _normalize_for_comparison(self, text: str) -> str:
        """Normalize text for comparison"""
        # Remove comments
        text = re.sub(r'(?<!\\)%.*$', '', text, flags=re.MULTILINE)
        # Normalize whitespace
        text = ' '.join(text.split())
        # Lowercase for comparison
        text = text.lower()
        return text
    
    def _check_math_preserved(self) -> bool:
        """Check if mathematical content is preserved"""
        # Extract math from original
        original_math = set(re.findall(r'\\\[(.*?)\\\]', self.original_tex, re.DOTALL))
        original_math.update(re.findall(r'\$(.+?)\$', self.original_tex))
        
        # Extract math from reconstructed (simplified check)
        reconstructed = self.doc.to_latex()
        reconstructed_math = set(re.findall(r'\\\[(.*?)\\\]', reconstructed, re.DOTALL))
        reconstructed_math.update(re.findall(r'\$(.+?)\$', reconstructed))
        
        # Check preservation rate
        if not original_math:
            return True
        
        preserved = len(original_math.intersection(reconstructed_math))
        return preserved / len(original_math) >= 0.8
    
    def _check_theorems_complete(self) -> bool:
        """Check if all theorem statements are complete"""
        for element in self.doc.all_elements:
            if element.type in ['theorem', 'proposition', 'lemma', 'corollary']:
                if not element.content or len(element.content) < 10:
                    return False
        return True
    
    def _check_structural_integrity(self):
        """Check tree structure integrity"""
        # Check for orphaned nodes
        reachable = self._get_all_reachable_elements()
        all_elements = set(id(e) for e in self.doc.all_elements)
        
        orphaned = all_elements - reachable
        self.metrics.no_orphaned_nodes = len(orphaned) == 0
        
        if orphaned:
            self.issues.append(f"Found {len(orphaned)} orphaned elements")
        
        # Check for dangling refs
        self.metrics.no_dangling_refs = self.metrics.label_resolution_rate >= 0.9
        
        # Check proper nesting
        self.metrics.proper_nesting = self.metrics.section_hierarchy_correct
    
    def _get_all_reachable_elements(self) -> set:
        """Get IDs of all elements reachable from root"""
        reachable = set()
        
        def traverse_section(section):
            for elem in section.elements:
                reachable.add(id(elem))
            for subsection in section.subsections:
                traverse_section(subsection)
        
        for section in self.doc.sections:
            traverse_section(section)
        
        return reachable
    
    def _calculate_score(self):
        """Calculate overall quality score"""
        score = 0
        
        # Completeness (max 40)
        score += self.metrics.section_coverage * 10
        score += self.metrics.element_coverage * 15
        score += self.metrics.equation_coverage * 10
        score += self.metrics.citation_coverage * 5
        
        # Accuracy (max 25)
        score += self.metrics.label_resolution_rate * 15
        if self.metrics.section_hierarchy_correct:
            score += 10
        
        # Reconstructibility (max 25)
        score += self.metrics.reconstruction_similarity * 20
        if self.metrics.math_content_preserved:
            score += 5
        
        # Structural Integrity (max 10)
        if self.metrics.no_orphaned_nodes:
            score += 3
        if self.metrics.no_dangling_refs:
            score += 3
        if self.metrics.proper_nesting:
            score += 4
        
        self.metrics.overall_score = int(score)
        
        # Can reconstruct?
        self.metrics.can_reconstruct = (
            self.metrics.reconstruction_similarity >= 0.7 and
            self.metrics.no_orphaned_nodes and
            self.metrics.element_coverage >= 0.7
        )
        
        # Assign grade
        if self.metrics.can_reconstruct and score >= 85:
            self.metrics.grade = "A"
        elif self.metrics.can_reconstruct and score >= 70:
            self.metrics.grade = "B"
        elif score >= 55:
            self.metrics.grade = "C"
        elif score >= 40:
            self.metrics.grade = "D"
        else:
            self.metrics.grade = "F"
    
    def print_report(self):
        """Print quality evaluation report"""
        print("\n" + "="*70)
        print("🌲 TREE STRUCTURE QUALITY EVALUATION")
        print("="*70)
        
        print(f"\n🎯 OVERALL SCORE: {self.metrics.overall_score}/100 (Grade: {self.metrics.grade})")
        print(f"   Can Reconstruct: {'✅ YES' if self.metrics.can_reconstruct else '❌ NO'}")
        
        print("\n📊 COMPLETENESS METRICS:")
        print(f"  Section Coverage:     {self.metrics.section_coverage:>6.1%}")
        print(f"  Element Coverage:     {self.metrics.element_coverage:>6.1%}")
        print(f"  Equation Coverage:    {self.metrics.equation_coverage:>6.1%}")
        print(f"  Citation Coverage:    {self.metrics.citation_coverage:>6.1%}")
        
        print("\n📊 ACCURACY METRICS:")
        print(f"  Label Resolution:     {self.metrics.label_resolution_rate:>6.1%}")
        print(f"  Section Hierarchy:    {'✅ Correct' if self.metrics.section_hierarchy_correct else '❌ Incorrect'}")
        
        print("\n📊 RECONSTRUCTIBILITY:")
        print(f"  Text Similarity:      {self.metrics.reconstruction_similarity:>6.1%}")
        print(f"  Math Preserved:       {'✅ Yes' if self.metrics.math_content_preserved else '❌ No'}")
        print(f"  Theorems Complete:    {'✅ Yes' if self.metrics.theorem_statements_complete else '❌ No'}")
        
        print("\n📊 STRUCTURAL INTEGRITY:")
        print(f"  No Orphaned Nodes:    {'✅ Yes' if self.metrics.no_orphaned_nodes else '❌ No'}")
        print(f"  No Dangling Refs:     {'✅ Yes' if self.metrics.no_dangling_refs else '❌ No'}")
        print(f"  Proper Nesting:       {'✅ Yes' if self.metrics.proper_nesting else '❌ No'}")
        
        if self.issues:
            print("\n❌ CRITICAL ISSUES:")
            for issue in self.issues[:10]:
                print(f"  • {issue}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings[:10]:
                print(f"  • {warning}")
        
        print("\n" + "="*70)
        
        if self.metrics.grade in ["A", "B"]:
            print("✅ TREE QUALITY: PASSED - Can reliably reconstruct paper")
        elif self.metrics.grade == "C":
            print("⚠️  TREE QUALITY: MARGINAL - Reconstruction may have issues")
        else:
            print("❌ TREE QUALITY: FAILED - Significant data loss")
        
        print("="*70)
    
    def get_detailed_diff(self) -> str:
        """Get detailed diff between original and reconstructed"""
        try:
            reconstructed = self.doc.to_latex()
            orig_lines = self.original_tex.splitlines()
            recon_lines = reconstructed.splitlines()
            
            diff = difflib.unified_diff(
                orig_lines, recon_lines,
                fromfile='original.tex',
                tofile='reconstructed.tex',
                lineterm=''
            )
            return '\n'.join(diff)
        except Exception as e:
            return f"Could not generate diff: {e}"
    
    def save_report(self, output_path: str):
        """Save evaluation report to JSON"""
        report = {
            'metrics': {
                'overall_score': self.metrics.overall_score,
                'grade': self.metrics.grade,
                'can_reconstruct': self.metrics.can_reconstruct,
                'section_coverage': self.metrics.section_coverage,
                'element_coverage': self.metrics.element_coverage,
                'equation_coverage': self.metrics.equation_coverage,
                'citation_coverage': self.metrics.citation_coverage,
                'label_resolution_rate': self.metrics.label_resolution_rate,
                'reconstruction_similarity': self.metrics.reconstruction_similarity,
                'math_content_preserved': self.metrics.math_content_preserved,
                'no_orphaned_nodes': self.metrics.no_orphaned_nodes,
                'no_dangling_refs': self.metrics.no_dangling_refs,
                'proper_nesting': self.metrics.proper_nesting,
            },
            'issues': self.issues,
            'warnings': self.warnings,
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print(f"Tree quality report saved to: {output_path}")


def evaluate_tree_quality(original_tex_path: str, structured_doc: Any) -> TreeQualityMetrics:
    """Evaluate tree quality from files"""
    with open(original_tex_path, 'r', encoding='utf-8') as f:
        original_tex = f.read()
    
    evaluator = TreeQualityEvaluator(original_tex, structured_doc)
    metrics = evaluator.evaluate()
    evaluator.print_report()
    
    return metrics


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent))
    
    if len(sys.argv) < 3:
        print("Usage: python tree_quality_evaluator.py <original.tex> <structured.json>")
        sys.exit(1)
    
    from structured_parser import StructuredDocument
    
    # Load original
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        original_tex = f.read()
    
    # Load structured doc
    doc = StructuredDocument.load(sys.argv[2])
    
    # Evaluate
    evaluator = TreeQualityEvaluator(original_tex, doc)
    metrics = evaluator.evaluate()
    evaluator.print_report()
    
    # Save report
    report_path = sys.argv[2].replace('.json', '_quality_report.json')
    evaluator.save_report(report_path)
