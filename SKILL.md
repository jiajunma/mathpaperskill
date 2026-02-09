---
name: math-paper-editing
description: Edits LaTeX math papers for clarity, correctness, and rigor in prose, notation, and proofs, following AMS style. Use when working with .tex files, LaTeX documents, or when the user asks to edit math papers or proofs.
---

# Math Paper Editing

## Quick Start

When editing math papers in LaTeX:

1. Read the local section context and recent definitions.
2. Improve prose for clarity and concision (AMS style).
3. Enforce consistent notation, labels, and theorem styling.
4. Fix LaTeX structure issues without changing meaning.
5. Clean citations and bibliography consistency.
6. For proofs, ensure research-level rigor and full justification.
7. Make **direct edits** to the files unless asked otherwise.

## Scope

This skill covers:
- Copyediting (grammar, flow, redundancy, tone)
- Mathematical notation correctness and consistency
- LaTeX structure and formatting improvements
- Citations and bibliography cleanup
- Proof creation, editing, and verification

## Editing Checklist

Use this checklist as you edit:

- [ ] Definitions and notation are introduced before use
- [ ] Variables are consistently named and formatted
- [ ] Theorem/lemma/proposition environments are used consistently
- [ ] Proofs are complete, concise, and logically ordered
- [ ] Cross-references compile and match labels
- [ ] Displayed equations are aligned and numbered appropriately
- [ ] Sentences around equations read smoothly in AMS style
- [ ] Bibliography entries and citations are consistent
 - [ ] All mathematical statements are justified without gaps

## AMS Style Notes

Apply these defaults unless the file already enforces a different style:
- Prefer concise, formal tone; avoid conversational phrasing
- Use “we” sparingly and consistently
- Prefer active voice for proofs and constructions
- Use standard terms: “proposition”, “lemma”, “theorem”, “corollary”
- Avoid unnecessary punctuation around displayed equations

## LaTeX Structure Guidance

Follow these norms:
- Use `\label{...}` immediately after `\caption{...}` or within theorem blocks
- Keep math operator names consistent (`\operatorname{...}` or `\DeclareMathOperator`)
- Avoid custom macros that shadow standard commands
- If a macro is used repeatedly, keep it; if not, inline it

## Proof Editing and Verification

Use this workflow when writing, revising, or verifying proofs:

1. Read the target LaTeX file and locate the proof area.
2. Determine task type:
   - Create: insert a new proof block following file format.
   - Edit: update an existing proof while preserving structure.
   - Verify: check the proof for gaps or errors and report them.
3. Generation: draft the proof with structure:
   - Summary with Verdict (complete vs partial) and Method Sketch.
   - Detailed Solution with a fully rigorous, step-by-step proof.
4. Verification: self-check the draft:
   - Every inference is justified.
   - All key lemmas are stated and used correctly.
   - No contradictions with earlier definitions.
   - TeX formatting is consistent.
5. Verification audit: re-verify the verification for missed gaps or hidden assumptions.
6. Decision:
   - Success: apply edits and finalize.
   - Stop: if a critical error invalidates downstream steps.
   - Ask for more information: if required statements, definitions, or scope are missing.
7. Loopback:
   - If issues found, return to Generation with fixes.
   - If clarification needed, pause and resume after user input.

### Core Requirements for Proofs

- Research-level rigor; no guessing or fabricated steps.
- All variables and relations in TeX delimiters (e.g., `Let $n$ be an integer.`).
- Preserve existing LaTeX sections, environments, and formatting.
- Handle claims/lemmas/theorems, not just full solutions.
- Decompose complex proofs into stated lemmas/claims.

### Verification Checklist

- Check each logical step for correctness or missing justification.
- Mark critical errors and note dependent invalid steps.
- Record justification gaps and continue checking downstream steps.
- Provide a Summary with:
  - Final Verdict (correct / critical error / justification gaps)
  - List of Findings with exact quotes and issue type.

### Proof Output Format

Use the document’s existing solution/proof template. If none exists:
```
\section*{Summary}
\textbf{Verdict.} ...
\textbf{Method Sketch.} ...

\section*{Detailed Solution}
...
```

## Citation Cleanup

- Normalize `\cite{}` usage (avoid mixed styles like `\citep`/`\citet` unless already used)
- Ensure each `\cite{}` key exists in the bibliography
- Keep bib entries consistent in casing and punctuation

## Output Expectations

- Apply edits directly to the LaTeX files
- Preserve the author’s mathematical meaning
- Do not rewrite large sections unless asked
