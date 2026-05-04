==========================================================================
   Job Shop and Open Shop Scheduling
   Project: TPA1 - SAAD (FEUP)
==========================================================================

1. REPOSITORY STRUCTURE
-----------------------
.
├── TPA1/
│   ├── code.ipynb				  # Full implementation & experiments
│   ├── instances/               # Taillard instances (ta01 to ta80)
│   ├── results/                 # Exported CSV result files
│   ├── Presentation.pdf         # Project presentation
│   ├── Report.pdf               # Technical report (LaTeX)
│   └── README.txt               # This information file


2. OVERVIEW
-----------
This repository contains the materials and code developed for the project 
TPA1, which studies and compares Mixed-Integer Programming (MIP) and 
Constraint Programming (CP) approaches for solving the Job Shop 
Scheduling Problem (JSP) and the Open Shop Scheduling Problem (OSP).


3. FOLDER DETAILS
-----------------
- Report.pdf: 
    Technical report detailing mathematical formulations and analysis.

- Presentation.pdf: 
    Final PowerPoint presentation summarizing the problem, models, 
    experiments, and conclusions.

- instances/: 
    Taillard benchmark instances downloaded from:
    * https://optimizizer.com/TA.php
    * https://github.com/tamy0612/JSPLIB

- results/: 
    CSV files storing makespan, solve times, and optimality metrics.


4. CODE DESCRIPTION
-------------------
The notebook in the code/ folder includes:
- Class-based implementations for JSP and OSP variants.
- Mixed-Integer Programming (MIP) model (using PuLP and CBC).
- Constraint Programming (CP) model (using Google OR-Tools CP-SAT).
- Automated experimental setup and result collection.

The code is self-contained and can be executed from start to end.


5. EXECUTION INSTRUCTIONS
-------------------------
1. Ensure Python 3.11.14 is installed.
2. Use an Anaconda environment (recommended).
3. Install required libraries:
   > pip install pulp ortools pandas numpy matplotlib
4. Open the notebook in the /code folder.
5. Run all cells sequentially to reproduce results.


6. ENVIRONMENT & SOLVERS
------------------------
- Programming Language: Python 3.11.14
- Environment: Anaconda
- Solvers:
    * CBC (via PuLP) for MIP
    * CP-SAT (OR-Tools) for CP


7. AUTHORS & INSTITUTION
------------------------
- Beatriz Sonnemberg
- Maria Beatriz Moreira
- Marta Costa

Faculty of Engineering, University of Porto (FEUP)
MECD - Analytical Decision Support Systems (SAAD)
Academic Year 2025/2026

--------------------------------------------------------------------------
End of README.txt
==========================================================================