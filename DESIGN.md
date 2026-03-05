# Math Paper Analyzer - Structured Document Model

## Core Design Goal
Parse mathematical papers into a structured tree that can theoretically reconstruct the entire article.

## Document Tree Structure

```
Document
├── metadata
│   ├── title
│   ├── authors[]
│   ├── abstract
│   ├── keywords[]
│   ├── packages[]        # LaTeX packages used
│   └── commands[]        # Custom commands defined
│
├── preamble              # LaTeX preamble content
│
├── sections[]            # Main content tree
│   └── Section
│       ├── type: "section" | "subsection" | "subsubsection"
│       ├── title
│       ├── label
│       ├── content: TextBlock[]
│       ├── children: Section[]  # Subsections
│       └── elements: Element[]  # Theorems, equations, etc.
│
├── elements[]            # All numbered elements (flat list for easy access)
│   ├── Theorem
│   │   ├── number
│   │   ├── label
│   │   ├── name/title
│   │   ├── statement: TextBlock[]
│   │   ├── proof: Proof
│   │   └── dependencies: ref[]
│   │
│   ├── Definition
│   │   ├── number
│   │   ├── label
│   │   ├── term: string  # The term being defined
│   │   └── definition: TextBlock[]
│   │
│   ├── Equation
│   │   ├── number
│   │   ├── label
│   │   ├── content: string  # LaTeX math content
│   │   └── inline: boolean
│   │
│   └── ... (Lemma, Proposition, Corollary, Remark, Example)
│
├── bibliography[]        # References
│   └── Citation
│       ├── key
│       ├── authors
│       ├── title
│       ├── journal/book
│       └── year
│
└── dependencies          # Dependency graph
    ├── ref_map: {label -> Element}
    ├── citation_map: {cite_key -> Citation}
    └── theorem_deps: [(source, target)]
```

## TextBlock Structure

```
TextBlock
├── type: "text" | "math_inline" | "math_display" | "cite" | "ref" | "command"
├── content: string
├── raw_latex: string     # Original LaTeX
└── children: TextBlock[] # Nested structures
```

## Key Features

1. **Complete Preservation**: Every character, command, and environment is stored
2. **Tree Navigation**: Parent-child relationships for easy traversal
3. **Cross-References**: All \ref, \cite, \label resolved and linked
4. **Reconstructible**: Can regenerate original LaTeX from structure
5. **Queryable**: Easy to find specific theorems, definitions, etc.

## Storage Format

JSON with references resolved as IDs for space efficiency.
Separate file for bibliography.

## Usage

```python
from math_analyzer import StructuredPaperAnalyzer

# Parse paper
analyzer = StructuredPaperAnalyzer()
doc = analyzer.parse("paper.tex")

# Save structured data
doc.save("output/structured.json")

# Reconstruct LaTeX
latex = doc.to_latex()

# Query specific elements
theorems = doc.find_elements(type="theorem")
main_theorem = doc.find_by_label("thm:main")
```
