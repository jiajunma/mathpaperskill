#!/usr/bin/env python3
"""
Review Quality Evaluator - Assesses the quality of AI-generated peer reviews
"""

import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from collections import defaultdict


@dataclass
class ReviewQualityMetrics:
    """Metrics for review quality"""
    # Content depth
    has_specific_theorem_analysis: bool = False
    has_mathematical_error_identification: bool = False
    has_proof_gap_analysis: bool = False
    has_notation_criticism: bool = False
    
    # Specificity
    cites_theorem_numbers: bool = False
    cites_definition_numbers: bool = False
    quotes_paper_content: bool = False
    gives_concrete_suggestions: bool = False
    
    # Structure
    has_clear_recommendation: bool = False
    has_prioritized_issues: bool = False
    has_severity_assessment: bool = False
    
    # Actionability
    suggestions_are_actionable: bool = False
    suggestions_have_locations: bool = False
    
    # Overall
    is_constructive: bool = False
    is_objective: bool = False
    avoids_generic_statements: bool = False
    
    # Score (0-100)
    overall_score: int = 0
    grade: str = "F"


class ReviewQualityEvaluator:
    """Evaluate the quality of a peer review"""
    
    def __init__(self, review_text: str):
        self.review_text = review_text
        self.metrics = ReviewQualityMetrics()
        self.issues = []
        self.strengths = []
    
    def evaluate(self) -> ReviewQualityMetrics:
        """Perform comprehensive quality evaluation"""
        self._check_content_depth()
        self._check_specificity()
        self._check_structure()
        self._check_actionability()
        self._check_tone()
        self._calculate_score()
        return self.metrics
    
    def _check_content_depth(self):
        """Check if review analyzes content deeply"""
        text = self.review_text.lower()
        
        # Check for theorem analysis
        theorem_patterns = [
            r'theorem\s+\d+',
            r'proposition\s+\d+',
            r'lemma\s+\d+',
            r'the main result',
            r'the proof of',
        ]
        self.metrics.has_specific_theorem_analysis = any(
            re.search(p, text) for p in theorem_patterns
        )
        if not self.metrics.has_specific_theorem_analysis:
            self.issues.append("Does not reference specific theorems by number")
        else:
            self.strengths.append("References specific theorems")
        
        # Check for mathematical error identification
        error_patterns = [
            r'error',
            r'incorrect',
            r'wrong',
            r'mistake',
            r'imprecise',
            r'unclear',
            r'undefined',
        ]
        self.metrics.has_mathematical_error_identification = any(
            re.search(p, text) for p in error_patterns
        )
        if not self.metrics.has_mathematical_error_identification:
            self.issues.append("Does not identify any mathematical issues")
        
        # Check for proof gap analysis
        gap_patterns = [
            r'gap',
            r'missing step',
            r'not clear',
            r'needs proof',
            r'should be justified',
            r'citation needed',
        ]
        self.metrics.has_proof_gap_analysis = any(
            re.search(p, text) for p in gap_patterns
        )
        if not self.metrics.has_proof_gap_analysis:
            self.issues.append("Does not analyze proof completeness")
        else:
            self.strengths.append("Analyzes proof gaps")
        
        # Check for notation criticism
        notation_patterns = [
            r'notation',
            r'symbol',
            r'consistent',
            r'confusing',
            r'undefined',
        ]
        self.metrics.has_notation_criticism = any(
            re.search(p, text) for p in notation_patterns
        )
    
    def _check_specificity(self):
        """Check if review is specific enough"""
        text = self.review_text
        
        # Check for theorem citations
        self.metrics.cites_theorem_numbers = bool(
            re.search(r'Theorem\s+\d+|Thm\.?\s*\d+', text)
        )
        if not self.metrics.cites_theorem_numbers:
            self.issues.append("Does not cite theorem numbers")
        else:
            self.strengths.append("Cites specific theorem numbers")
        
        # Check for definition citations
        self.metrics.cites_definition_numbers = bool(
            re.search(r'Definition\s+\d+|Def\.?\s*\d+', text)
        )
        
        # Check for quotes from paper
        quote_patterns = [
            r'["\'][^"\']{20,}["\']',  # Long quotes
            r'Equation\s*\(\s*\d+\s*\)',
            r'\(\\ref\{[^}]+\}\)',
        ]
        self.metrics.quotes_paper_content = any(
            re.search(p, text) for p in quote_patterns
        )
        
        # Check for concrete suggestions
        concrete_patterns = [
            r'should\s+\w+',
            r'needs\s+to\s+\w+',
            r'add\s+',
            r'clarify\s+',
            r'prove\s+',
            r'justify\s+',
        ]
        self.metrics.gives_concrete_suggestions = any(
            re.search(p, text, re.IGNORECASE) for p in concrete_patterns
        )
        if not self.metrics.gives_concrete_suggestions:
            self.issues.append("Lacks concrete suggestions")
        else:
            self.strengths.append("Provides concrete suggestions")
    
    def _check_structure(self):
        """Check if review has good structure"""
        text = self.review_text.lower()
        
        # Check for clear recommendation
        recommendation_patterns = [
            r'recommend\s*:?\s*accept',
            r'recommend\s*:?\s*reject',
            r'recommend\s*:?\s*revision',
            r'accept\s*with\s*minor',
            r'major\s*revision',
        ]
        self.metrics.has_clear_recommendation = any(
            re.search(p, text) for p in recommendation_patterns
        )
        if not self.metrics.has_clear_recommendation:
            self.issues.append("No clear accept/reject recommendation")
        else:
            self.strengths.append("Provides clear recommendation")
        
        # Check for prioritized issues
        priority_patterns = [
            r'critical',
            r'serious',
            r'major issue',
            r'minor issue',
            r'important',
        ]
        self.metrics.has_prioritized_issues = any(
            re.search(p, text) for p in priority_patterns
        )
        
        # Check for severity assessment
        self.metrics.has_severity_assessment = bool(
            re.search(r'(minor|major|critical|serious)', text)
        )
    
    def _check_actionability(self):
        """Check if suggestions are actionable"""
        text = self.review_text.lower()
        
        # Check for actionable language
        actionable_patterns = [
            r'should\s+be\s+\w+ed',
            r'needs\s+to\s+be',
            r'must\s+provide',
            r'add\s+a\s+proof',
            r'clarify\s+that',
        ]
        self.metrics.suggestions_are_actionable = any(
            re.search(p, text) for p in actionable_patterns
        )
        if not self.metrics.suggestions_are_actionable:
            self.issues.append("Suggestions are not actionable")
        
        # Check for location-specific suggestions
        location_patterns = [
            r'in\s+section\s+\d+',
            r'in\s+theorem\s+\d+',
            r'after\s+equation',
            r'before\s+the\s+proof',
            r'page\s+\d+',
            r'line\s+\d+',
        ]
        self.metrics.suggestions_have_locations = any(
            re.search(p, text) for p in location_patterns
        )
    
    def _check_tone(self):
        """Check review tone"""
        text = self.review_text.lower()
        
        # Check for constructive tone
        constructive_patterns = [
            r'would benefit',
            r'could be improved',
            r'suggest',
            r'recommend',
        ]
        negative_patterns = [
            r'this paper is bad',
            r'poor quality',
            r'not worth',
            r'completely wrong',
        ]
        self.metrics.is_constructive = (
            any(re.search(p, text) for p in constructive_patterns) and
            not any(re.search(p, text) for p in negative_patterns)
        )
        
        # Check for objectivity
        objective_patterns = [
            r'the theorem states',
            r'the proof shows',
            r'equation\s*\(',
            r'definition\s+\d+\s+implies',
        ]
        subjective_patterns = [
            r'i think',
            r'i believe',
            r'in my opinion',
            r'obviously',
            r'clearly',
        ]
        objective_count = sum(1 for p in objective_patterns if re.search(p, text))
        subjective_count = sum(1 for p in subjective_patterns if re.search(p, text))
        self.metrics.is_objective = objective_count > subjective_count
        
        # Check for generic statements
        generic_statements = [
            r'the paper needs more explanation',
            r'more details would be helpful',
            r'the writing could be improved',
            r'some parts are unclear',
        ]
        has_generic = any(re.search(p, text) for p in generic_statements)
        self.metrics.avoids_generic_statements = not has_generic
        if not self.metrics.avoids_generic_statements:
            self.issues.append("Contains vague/generic statements without specifics")
    
    def _calculate_score(self):
        """Calculate overall quality score"""
        score = 0
        
        # Content depth (max 30)
        if self.metrics.has_specific_theorem_analysis: score += 10
        if self.metrics.has_mathematical_error_identification: score += 10
        if self.metrics.has_proof_gap_analysis: score += 10
        
        # Specificity (max 25)
        if self.metrics.cites_theorem_numbers: score += 8
        if self.metrics.quotes_paper_content: score += 8
        if self.metrics.gives_concrete_suggestions: score += 9
        
        # Structure (max 20)
        if self.metrics.has_clear_recommendation: score += 10
        if self.metrics.has_prioritized_issues: score += 5
        if self.metrics.has_severity_assessment: score += 5
        
        # Actionability (max 15)
        if self.metrics.suggestions_are_actionable: score += 10
        if self.metrics.suggestions_have_locations: score += 5
        
        # Tone (max 10)
        if self.metrics.is_constructive: score += 5
        if self.metrics.avoids_generic_statements: score += 5
        
        self.metrics.overall_score = score
        
        # Assign grade
        if score >= 85: self.metrics.grade = "A"
        elif score >= 70: self.metrics.grade = "B"
        elif score >= 55: self.metrics.grade = "C"
        elif score >= 40: self.metrics.grade = "D"
        else: self.metrics.grade = "F"
    
    def print_report(self):
        """Print quality evaluation report"""
        print("\n" + "="*70)
        print("📊 REVIEW QUALITY EVALUATION")
        print("="*70)
        
        print(f"\n🎯 OVERALL SCORE: {self.metrics.overall_score}/100 (Grade: {self.metrics.grade})")
        
        print("\n✅ STRENGTHS:")
        for s in self.strengths[:5]:
            print(f"  • {s}")
        
        print("\n❌ ISSUES:")
        for i in self.issues[:10]:
            print(f"  • {i}")
        
        print("\n📋 DETAILED METRICS:")
        print("-" * 50)
        
        sections = [
            ("Content Depth", [
                ("Specific theorem analysis", self.metrics.has_specific_theorem_analysis),
                ("Mathematical error identification", self.metrics.has_mathematical_error_identification),
                ("Proof gap analysis", self.metrics.has_proof_gap_analysis),
                ("Notation criticism", self.metrics.has_notation_criticism),
            ]),
            ("Specificity", [
                ("Cites theorem numbers", self.metrics.cites_theorem_numbers),
                ("Quotes paper content", self.metrics.quotes_paper_content),
                ("Concrete suggestions", self.metrics.gives_concrete_suggestions),
            ]),
            ("Structure", [
                ("Clear recommendation", self.metrics.has_clear_recommendation),
                ("Prioritized issues", self.metrics.has_prioritized_issues),
                ("Severity assessment", self.metrics.has_severity_assessment),
            ]),
            ("Actionability", [
                ("Actionable suggestions", self.metrics.suggestions_are_actionable),
                ("Location-specific", self.metrics.suggestions_have_locations),
            ]),
            ("Tone", [
                ("Constructive tone", self.metrics.is_constructive),
                ("Avoids generic statements", self.metrics.avoids_generic_statements),
            ]),
        ]
        
        for section_name, checks in sections:
            print(f"\n{section_name}:")
            for name, value in checks:
                status = "✓" if value else "✗"
                print(f"  [{status}] {name}")
        
        print("\n" + "="*70)
        
        # Pass/Fail
        if self.metrics.grade in ["A", "B"]:
            print("✅ REVIEW QUALITY: PASSED")
        elif self.metrics.grade == "C":
            print("⚠️  REVIEW QUALITY: MARGINAL (needs improvement)")
        else:
            print("❌ REVIEW QUALITY: FAILED (requires major revision)")
        
        print("="*70)
    
    def is_acceptable(self, min_grade: str = "C") -> bool:
        """Check if review meets minimum quality standard"""
        grade_order = {"F": 0, "D": 1, "C": 2, "B": 3, "A": 4}
        return grade_order[self.metrics.grade] >= grade_order[min_grade]


def evaluate_review_file(review_path: str) -> ReviewQualityMetrics:
    """Evaluate a review from file"""
    with open(review_path, 'r', encoding='utf-8') as f:
        review_text = f.read()
    
    evaluator = ReviewQualityEvaluator(review_text)
    metrics = evaluator.evaluate()
    evaluator.print_report()
    
    return metrics


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python review_quality_evaluator.py <review_file.md>")
        sys.exit(1)
    
    evaluate_review_file(sys.argv[1])
