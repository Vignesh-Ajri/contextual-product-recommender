# CPRP Research Paper

This directory contains the LaTeX source code for the research paper: **"Contextual Product Recommender Platform Based on User Digital Activity Patterns"**.

## Files
* `main.tex`: The main document written in the IEEE conference format.
* `references.bib`: The bibliography file containing all citations.
* `figures/`: Directory containing TikZ diagrams:
  * `architecture.tex`: System Architecture diagram.
  * `er_diagram.tex`: Database Entity-Relationship diagram.
  * `flowchart.tex`: Recommendation Flow diagram.

## How to Compile
You can compile this paper locally using a LaTeX distribution (like TeX Live, MiKTeX, or MacTeX) or online using Overleaf.

### Using Overleaf (Recommended)
1. Zip the entire `research_paper` folder.
2. Go to [Overleaf](https://www.overleaf.com/) and create a "New Project" $\rightarrow$ "Upload Project".
3. Upload the zip file.
4. Open `main.tex` and click "Recompile". Overleaf will automatically handle the TikZ figures and the bibliography.

### Compiling Locally
Open a terminal in the `research_paper` directory and run:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

This will generate `main.pdf`.
