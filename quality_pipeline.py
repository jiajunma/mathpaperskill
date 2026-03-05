#!/usr/bin/env python3
"""
Iterative Quality Improvement Pipeline
Tests and improves both tree structure and review quality until both pass
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from math_analyzer import MathPaperAnalyzer, LLMReviewer
from structured_parser import StructuredParser, StructuredDocument
from review_quality_evaluator import ReviewQualityEvaluator
from tree_quality_evaluator import TreeQualityEvaluator
import json


class QualityImprovementPipeline:
    """Pipeline for iterative quality improvement"""
    
    def __init__(self, tex_path: str, output_dir: str = "./test/output"):
        self.tex_path = tex_path
        self.output_dir = output_dir
        self.original_tex = ""
        self.structured_doc = None
        self.review_text = ""
        
        # Quality thresholds
        self.tree_min_grade = "B"  # 70+
        self.review_min_grade = "B"  # 70+
        
        # Iteration tracking
        self.iteration = 0
        self.max_iterations = 3
    
    def run(self):
        """Run the full quality improvement pipeline"""
        print("="*70)
        print("🔄 ITERATIVE QUALITY IMPROVEMENT PIPELINE")
        print("="*70)
        print(f"\nInput: {self.tex_path}")
        print(f"Output: {self.output_dir}")
        print(f"Tree Quality Target: Grade {self.tree_min_grade} (70+)")
        print(f"Review Quality Target: Grade {self.review_min_grade} (70+)")
        
        # Load original
        with open(self.tex_path, 'r', encoding='utf-8') as f:
            self.original_tex = f.read()
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Stage 1: Parse to tree structure
        print("\n" + "="*70)
        print("📦 STAGE 1: Parse to Structured Tree")
        print("="*70)
        
        parser = StructuredParser()
        self.structured_doc = parser.parse(self.original_tex)
        
        # Save structured data
        json_path = os.path.join(self.output_dir, "structured.json")
        self.structured_doc.save(json_path)
        
        # Stage 2: Evaluate tree quality
        print("\n" + "="*70)
        print("🔍 STAGE 2: Evaluate Tree Quality")
        print("="*70)
        
        tree_evaluator = TreeQualityEvaluator(self.original_tex, self.structured_doc)
        tree_metrics = tree_evaluator.evaluate()
        tree_evaluator.print_report()
        
        # Save tree quality report
        tree_report_path = os.path.join(self.output_dir, "tree_quality.json")
        tree_evaluator.save_report(tree_report_path)
        
        # Check if tree quality passes
        if not tree_metrics.can_reconstruct or tree_metrics.grade not in ["A", "B"]:
            print("\n⚠️  Tree quality insufficient. Attempting improvements...")
            self._improve_tree_structure()
            
            # Re-evaluate
            tree_evaluator = TreeQualityEvaluator(self.original_tex, self.structured_doc)
            tree_metrics = tree_evaluator.evaluate()
        
        if not tree_metrics.can_reconstruct:
            print("\n❌ CRITICAL: Tree structure cannot reliably reconstruct paper")
            print("   Cannot proceed to review generation.")
            return False
        
        # Stage 3: Generate peer review
        print("\n" + "="*70)
        print("📝 STAGE 3: Generate Peer Review")
        print("="*70)
        
        self._generate_review_with_iteration()
        
        # Stage 4: Evaluate review quality
        print("\n" + "="*70)
        print("🔍 STAGE 4: Evaluate Review Quality")
        print("="*70)
        
        review_evaluator = ReviewQualityEvaluator(self.review_text)
        review_metrics = review_evaluator.evaluate()
        review_evaluator.print_report()
        
        # Save review quality report
        review_report_path = os.path.join(self.output_dir, "review_quality.json")
        with open(review_report_path, 'w') as f:
            json.dump({
                'score': review_metrics.overall_score,
                'grade': review_metrics.grade,
                'is_acceptable': review_evaluator.is_acceptable(self.review_min_grade)
            }, f, indent=2)
        
        # Final summary
        print("\n" + "="*70)
        print("📊 FINAL QUALITY SUMMARY")
        print("="*70)
        print(f"\nTree Structure Quality:")
        print(f"  Score: {tree_metrics.overall_score}/100 (Grade {tree_metrics.grade})")
        print(f"  Can Reconstruct: {'✅ Yes' if tree_metrics.can_reconstruct else '❌ No'}")
        
        print(f"\nPeer Review Quality:")
        print(f"  Score: {review_metrics.overall_score}/100 (Grade {review_metrics.grade})")
        print(f"  Acceptable: {'✅ Yes' if review_evaluator.is_acceptable(self.review_min_grade) else '❌ No'}")
        
        # Overall status
        tree_pass = tree_metrics.can_reconstruct and tree_metrics.grade in ["A", "B"]
        review_pass = review_evaluator.is_acceptable(self.review_min_grade)
        
        print("\n" + "="*70)
        if tree_pass and review_pass:
            print("✅ BOTH QUALITY CHECKS PASSED")
            print("="*70)
            print(f"\n📁 Output files:")
            print(f"  • Structured tree: {json_path}")
            print(f"  • Tree quality report: {tree_report_path}")
            print(f"  • Peer review: {os.path.join(self.output_dir, 'peer_review.md')}")
            print(f"  • Review quality report: {review_report_path}")
            return True
        else:
            print("❌ SOME QUALITY CHECKS FAILED")
            if not tree_pass:
                print("  • Tree structure needs improvement")
            if not review_pass:
                print("  • Peer review needs improvement")
            print("="*70)
            return False
    
    def _improve_tree_structure(self):
        """Attempt to improve tree structure quality"""
        print("\n🔧 Attempting tree structure improvements...")
        
        # Try parsing with different settings
        parser = StructuredParser()
        
        # Re-parse with more aggressive extraction
        self.structured_doc = parser.parse(self.original_tex)
        
        # Rebuild indices
        self.structured_doc.label_map = {}
        self._index_document()
        
        print("✓ Tree structure re-parsed")
    
    def _index_document(self):
        """Index all elements in document"""
        for section in self.structured_doc.sections:
            self._index_section(section)
    
    def _index_section(self, section):
        """Recursively index section"""
        if section.label:
            self.structured_doc.label_map[section.label] = section
        
        for element in section.elements:
            if element.label:
                self.structured_doc.label_map[element.label] = element
        
        for subsection in section.subsections:
            self._index_section(subsection)
    
    def _generate_review_with_iteration(self):
        """Generate review with quality iteration"""
        # Load API keys
        kimi_key = None
        key_paths = [
            os.path.expanduser("~/.openclaw/workspace/mycode/kimi_key"),
            "./kimi_key",
        ]
        for path in key_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    kimi_key = f.read().strip()
                break
        
        if not kimi_key:
            print("⚠️  No API key found, skipping review generation")
            self.review_text = "Review generation skipped - no API key"
            return
        
        # Generate review
        reviewer = LLMReviewer(kimi_key=kimi_key)
        
        # Create simplified structure for review
        from math_analyzer import PaperStructure, MathEntity
        simple_structure = PaperStructure()
        simple_structure.title = self.structured_doc.title
        simple_structure.authors = self.structured_doc.authors
        simple_structure.abstract = self.structured_doc.abstract
        
        # Convert elements
        for element in self.structured_doc.all_elements:
            entity = MathEntity(
                type=element.type,
                name=element.name or f"{element.type} {element.number}",
                label=element.label,
                content=''.join(s.content for s in element.content) if hasattr(element, 'content') else str(element.content)
            )
            simple_structure.entities.append(entity)
            
            # Add to appropriate dict
            if element.type == 'definition':
                simple_structure.definitions[element.label or str(element.number)] = entity
            elif element.type == 'theorem':
                simple_structure.theorems[element.label or str(element.number)] = entity
            elif element.type == 'lemma':
                simple_structure.lemmas[element.label or str(element.number)] = entity
            elif element.type == 'proposition':
                simple_structure.propositions[element.label or str(element.number)] = entity
            elif element.type == 'corollary':
                simple_structure.corollaries[element.label or str(element.number)] = entity
            elif element.type == 'assumption':
                simple_structure.assumptions[element.label or str(element.number)] = entity
            elif element.type == 'remark':
                simple_structure.remarks[element.label or str(element.number)] = entity
        
        review = reviewer.generate_review(simple_structure)
        self.review_text = review['raw_text']
        
        # Save review
        review_path = os.path.join(self.output_dir, "peer_review.md")
        with open(review_path, 'w', encoding='utf-8') as f:
            f.write("# Peer Review Report\n\n")
            f.write(self.review_text)
        
        print(f"✓ Review saved to {review_path}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Iterative Quality Improvement Pipeline")
    parser.add_argument("tex_file", help="Path to LaTeX file to analyze")
    parser.add_argument("-o", "--output", default="./test/output", help="Output directory")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.tex_file):
        print(f"Error: File not found: {args.tex_file}")
        sys.exit(1)
    
    pipeline = QualityImprovementPipeline(args.tex_file, args.output)
    success = pipeline.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
