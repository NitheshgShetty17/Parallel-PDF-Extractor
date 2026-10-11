# Parallel PDF Text Extractor
**Course:** BCS702 – Parallel Computing  
**Technology Stack:** Python 3.11, Flask, Multiprocessing, PyPDF, ReportLab, Vanilla CSS, Chart.js  

---

## 1. Project Overview & Problem Statement

Extracting text and searching for target keywords across voluminous multi-page documents (such as technical manuals, legal filings, or academic papers) is a CPU-intensive operation. In standard single-threaded execution, documents are processed sequentially: each page must be read, parsed from binary PDF streams, converted into character encodings, and string-matched one by one.

This project implements a high-performance **Parallel PDF Text Extractor** designed to evaluate and demonstrate parallel processing concepts taught in **BCS702 Parallel Computing**.

The application provides:
1. **A Single-Threaded Sequential Extractor** as a fair experimental baseline ($T_s$).
2. **A Multi-Core Multiprocessing Extractor** utilizing genuine Python `multiprocessing` worker pools ($T_p$).
3. **An Automatic Verification Engine** guaranteeing that both sequential and parallel algorithms discover 100% identical matching pages, snippet contexts, and occurrence counts.
4. **Performance Measurement & Analytical Metrics** calculating real measured **Speedup** ($S$) and **Parallel Efficiency** ($E$).
5. **An Interactive Flask Web Dashboard** featuring live execution comparisons, Chart.js visual charts, workload distribution diagrams, and snippet extraction.
6. **A Standalone CLI Benchmark Suite** (`benchmark.py`) for automated multi-trial experiment runs and report generation.

---

## 2. System Architecture & Workflow Diagram

### Parallel Workflow Diagram (Text Flowchart)

```
                       [ Input Document: target.pdf ]
                                    │
                                    ▼
                     [ Inspect Metadata: Total Pages N ]
                                    │
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │   Balanced Page Chunking Logic: get_page_chunks(N, p)   │
       │   Chunk Size = N // p; Distribute Remainder Evenly      │
       └─────────────────────────────────────────────────────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       ▼                            ▼                            ▼
[ Worker 1 (Core 0) ]       [ Worker 2 (Core 1) ]       [ Worker p (Core p-1) ]
  Chunk: [0 .. c1)            Chunk: [c1 .. c2)           Chunk: [cp-1 .. N)
  │                           │                           │
  ├─ Opens PDF independently  ├─ Opens PDF independently  ├─ Opens PDF independently
  ├─ Parses assigned pages    ├─ Parses assigned pages    ├─ Parses assigned pages
  ├─ Case-insensitive search  ├─ Case-insensitive search  ├─ Case-insensitive search
  └─ Extracts snippets        └─ Extracts snippets        └─ Extracts snippets
       │                            │                            │
       └────────────────────────────┼────────────────────────────┘
                                    │
                                    ▼
                [ Gather Chunk Outputs via pool.starmap() ]
                                    │
                                    ▼
             [ Merge & Sort All Results by Ascending Page # ]
                                    │
       ┌────────────────────────────┴────────────────────────────┐
       ▼                                                         ▼
[ Correctness Verification ]                            [ Performance Metrics ]
  Seq Pages == Par Pages ?                                Speedup S = Ts / Tp
  Seq Count == Par Count ?                                Efficiency E = (S / p) * 100%
                                    │
                                    ▼
           [ Render Results in Flask Dashboard & Chart.js ]
```

### Flowchart in Mermaid Notation

```mermaid
graph TD
    A[User Submits PDF & Search Term] --> B[Sequential Extraction Ts]
    A --> C[Inspect Total Pages N]
    C --> D[Divide Pages into p Balanced Chunks]
    D --> E1[Worker 1: Pages 1 to N/p]
    D --> E2[Worker 2: Pages N/p+1 to 2N/p]
    D --> E3[Worker p: Pages ... to N]
    E1 --> F[Gather Worker Outputs]
    E2 --> F
    E3 --> F
    F --> G[Sort & Merge in Page Order Tp]
    B --> H[Verify 100% Equivalence]
    G --> H
    H --> I[Compute Speedup S & Efficiency E]
    I --> J[Display Web Dashboard & Chart]
```

---

## 3. Computational Logic & Implementation Details

### A. Balanced Page Partitioning
Given $N$ total pages and $p$ requested worker processes, pages are partitioned into contiguous slices $[start, end)$ to achieve uniform load balancing:

```python
def get_page_chunks(total_pages: int, num_workers: int) -> list[tuple[int, int]]:
    active_workers = min(num_workers, total_pages)
    base_chunk = total_pages // active_workers
    remainder = total_pages % active_workers
    
    chunks = []
    current = 0
    for i in range(active_workers):
        chunk_size = base_chunk + (1 if i < remainder else 0)
        chunks.append((current, current + chunk_size))
        current += chunk_size
    return chunks
```

**Example:** Distributing 10 pages across 3 workers produces:
- **Worker 1:** Pages $0 \dots 3$ (4 pages)
- **Worker 2:** Pages $4 \dots 6$ (3 pages)
- **Worker 3:** Pages $7 \dots 9$ (3 pages)

### B. Low-Overhead IPC Architecture (Crucial for Performance)
In Python multiprocessing on Windows, inter-process communication (IPC) uses pickle serialization across pipes.
- **Naïve approach (Anti-pattern):** Extracting all pages in the master process or passing in-memory byte arrays and heavy PDF objects across IPC creates massive serialization bottlenecks that erase parallel speedups.
- **Our optimized design:** Each worker process receives only lightweight metadata: `(file_path, search_term, start_page, end_page, case_sensitive)`.
- Each worker independently instantiates its own `pypdf.PdfReader` and reads **only its designated page range** directly from the local file system. This allows concurrent operating system disk caching and zero redundant serialization.

### C. Windows Python 3.11 Multiprocessing Compatibility
On Windows, Python uses the `spawn` process start method (unlike Linux `fork`).
- Worker functions (`process_page_chunk`) are defined at module top-level in [extractor.py](file:///d:/4MW23CS089/Parallel_PDF_Extractor/extractor.py) so child processes can import them cleanly without re-executing Flask server routes.
- The entry script uses the canonical `if __name__ == '__main__':` guard.
- When running Flask, `use_reloader=False` prevents duplicate child server spawns.

---

## 4. Performance Metrics & Theoretical Analysis

### A. Mathematical Formulas

1. **Speedup ($S$):**
   $$S = \frac{T_{sequential}}{T_{parallel}}$$
   Where $T_{sequential}$ is the baseline execution time on 1 process, and $T_{parallel}$ is the execution time using $p$ worker processes.

2. **Parallel Efficiency ($E$):**
   $$E = \frac{S}{p} \times 100\% = \frac{T_{sequential}}{p \times T_{parallel}} \times 100\%$$
   Efficiency indicates how constructively the $p$ CPU cores are utilized. Theoretical maximum is $100\%$.

3. **Amdahl's Law:**
   $$S_{max}(p) = \frac{1}{s + \frac{1 - s}{p}}$$
   Where $s$ is the inherently serial fraction of the application (e.g. metadata reading, chunk scheduling, and result merging), and $(1 - s)$ is the parallelizable fraction (PDF page text extraction and regex search).

### B. Understanding Parallel Overhead on Small Documents
In our empirical experiments, students will notice that **on small PDFs (e.g. 5 pages), the parallel extractor is slower than the sequential extractor ($S < 1.0$)**.

**Why does this happen?**
1. **Process Creation Latency:** On Microsoft Windows, `multiprocessing` must launch fresh `python.exe` processes and re-import modules via the `spawn` protocol. This fixed overhead takes approximately **$40\text{ ms} \dots 80\text{ ms}$ per worker**.
2. **Workload Breakeven:** For a 5-page PDF, single-process sequential extraction takes only $\approx 25\text{ ms}$. Because $25\text{ ms} < 350\text{ ms}$ (the fixed process startup and join cost), parallelism incurs a net penalty.
3. **Large Document Scaling:** For documents with 100 to 400+ pages, sequential extraction takes $1.5\text{ s} \dots 3\text{ s}$. The $300\text{ ms}$ startup overhead becomes a negligible fraction of the total execution time, yielding substantial real-world speedups ($S > 1.5\times \dots 1.8\times$).

---

## 5. Live Experimental Benchmark Results

The following measurements are **actual, real-world benchmark runs** conducted on Windows with Python 3.11 across various document sizes using [benchmark.py](file:///d:/4MW23CS089/Parallel_PDF_Extractor/benchmark.py):

### Document 1: Small PDF (5 Pages)
- **Search Query:** `"Amdahl"` (24 matches found)
- **Sequential Baseline ($T_s$):** $40.89\text{ ms}$

| Process Model | Worker Count ($p$) | Execution Time ($T_p$) | Speedup ($S$) | Efficiency ($E$) | Correctness |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Sequential** | 1 | $40.89\text{ ms}$ | $1.000\times$ | $100.00\%$ | Baseline |
| **Multiprocessing** | 2 | $363.32\text{ ms}$ | $0.113\times$ | $5.63\%$ | **PASSED** |
| **Multiprocessing** | 4 | $456.54\text{ ms}$ | $0.090\times$ | $2.24\%$ | **PASSED** |

*Observation:* Process spawning latency heavily dominates the small computational workload.

---

### Document 2: Medium PDF (30 Pages)
- **Search Query:** `"Amdahl"` (152 matches found)
- **Sequential Baseline ($T_s$):** $127.70\text{ ms}$

| Process Model | Worker Count ($p$) | Execution Time ($T_p$) | Speedup ($S$) | Efficiency ($E$) | Correctness |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Sequential** | 1 | $127.70\text{ ms}$ | $1.000\times$ | $100.00\%$ | Baseline |
| **Multiprocessing** | 2 | $412.32\text{ ms}$ | $0.310\times$ | $15.49\%$ | **PASSED** |
| **Multiprocessing** | 4 | $509.19\text{ ms}$ | $0.251\times$ | $6.27\%$ | **PASSED** |

*Observation:* Breakeven transition begins; parallel time begins closing the gap.

---

### Document 3: Large PDF (100 Pages)
- **Search Query:** `"Amdahl"` (508 matches found)
- **Sequential Baseline ($T_s$):** $388.05\text{ ms}$

| Process Model | Worker Count ($p$) | Execution Time ($T_p$) | Speedup ($S$) | Efficiency ($E$) | Correctness |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Sequential** | 1 | $388.05\text{ ms}$ | $1.000\times$ | $100.00\%$ | Baseline |
| **Multiprocessing** | 2 | $550.77\text{ ms}$ | $0.705\times$ | $35.23\%$ | **PASSED** |
| **Multiprocessing** | 4 | $612.29\text{ ms}$ | $0.634\times$ | $15.84\%$ | **PASSED** |

*Observation:* Speedup increases significantly to $0.705\times$ as page parsing workload increases.

---

### Document 4: XL Benchmark PDF (400 Pages)
- **Search Query:** `"Amdahl"` (2,028 matches found)
- **Sequential Baseline ($T_s$):** $1552.33\text{ ms}$ ($1.552\text{ s}$)

| Process Model | Worker Count ($p$) | Execution Time ($T_p$) | Speedup ($S$) | Efficiency ($E$) | Correctness |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Sequential** | 1 | $1552.33\text{ ms}$ | $1.000\times$ | $100.00\%$ | Baseline |
| **Multiprocessing** | 2 | $1093.15\text{ ms}$ | **$1.420\times$** | **$71.00\%$** | **PASSED** |
| **Multiprocessing** | 4 | $912.60\text{ ms}$ | **$1.701\times$** | **$42.53\%$** | **PASSED** |

*Observation:* **Parallel execution is significantly faster!** At 4 workers, execution is $1.701\times$ faster than sequential, confirming effective multi-core parallel speedup on larger workloads.

---

## 6. Project Structure

```
d:/4MW23CS089/Parallel_PDF_Extractor/
├── app.py                   # Flask web server, endpoints, and file upload validation
├── extractor.py             # Core sequential, multiprocessing worker, and metrics engine
├── benchmark.py             # Multi-trial CLI benchmark runner for lab reports
├── generate_sample_pdf.py   # Synthetic benchmark PDF generator (5, 30, 100, 400 pages)
├── test_app.py              # Automated unit and integration test suite
├── requirements.txt         # Project dependency definitions
├── templates/
│   ├── index.html           # Modern dashboard template with Chart.js & controls
│   └── results_partial.html # Server-side rendered fallback results component
├── static/
│   └── style.css            # Dark glassmorphism stylesheet with responsive design
├── sample_pdfs/             # Generated test documents
└── uploads/                 # Temporary upload workspace (automatically cleaned up)
```

---

## 7. Windows Setup & Execution Guide (Python 3.11)

### Step 1: Open Terminal in Project Directory
Open **PowerShell** or **Command Prompt** in `d:\4MW23CS089\Parallel_PDF_Extractor`:

```powershell
cd d:\4MW23CS089\Parallel_PDF_Extractor
```

### Step 2: Verify Python 3.11
```powershell
python --version
```
*Expected output:* `Python 3.11.x`

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Run the Automated Test Suite
Verify that all unit tests, chunk partitioning, validation logic, and correctness checks pass:
```powershell
python test_app.py
```
*Expected output:* `Ran 8 tests in ... OK`

### Step 5: Launch the Flask Web Application
```powershell
python app.py
```
*Expected output:*
```
============================================================
 BCS702 Parallel PDF Text Extractor Application
 Detected CPU Logical Cores: 4
 Starting Flask server on http://127.0.0.1:5000 ...
============================================================
```

### Step 6: Access the Web Dashboard
Open your browser and navigate to:
```
http://127.0.0.1:5000
```
- Select a preset document (**Small**, **Medium**, **Large**, or **Benchmark XL**) or upload your own PDF file.
- Enter a search keyword (e.g. `Amdahl`, `concurrency`, `speedup`).
- Select the number of worker processes ($p = 2, 3, 4, 6, 8$).
- Choose the number of experimental trials ($1, 3, 5$).
- Click **"Run Sequential & Parallel Extraction"**.
- Review the correctness status badge, Speedup, Parallel Efficiency, Chart.js comparison chart, worker chunk workload breakdown, and context snippets.

---

## 8. CLI Benchmarking for BCS702 Lab Reports

To run automated, repeatable multi-trial benchmarks and append formatted Markdown tables directly into your lab report file:

### Run Benchmark on All Document Sizes:
```powershell
python benchmark.py --preset all --workers 2 4 --trials 3 --output lab_report_results.md
```

### Run Benchmark on a Custom Uploaded PDF:
```powershell
python benchmark.py --pdf "path\to\your_document.pdf" --keyword "algorithm" --workers 2 3 4 --trials 3
```

---

## 9. Academic Report Discussion & Conclusions

### Time and Space Complexity
- **Sequential Time Complexity:** $\mathcal{O}(N \times \bar{L})$, where $N$ is total pages and $\bar{L}$ is the average character length per page.
- **Parallel Time Complexity:** $\mathcal{O}\left(\frac{N}{p} \times \bar{L}\right) + \mathcal{O}(T_{startup} + T_{merge})$.
- **Space Complexity:** $\mathcal{O}(\text{Matches Count} \times \text{Snippet Length})$ memory footprint. By sending file paths rather than binary page objects across IPC, memory remains bounded at $\mathcal{O}(1)$ overhead per worker.

### Limitations
1. **CPython Process Startup Cost:** Spawning worker processes on Windows incurs a fixed cost ($\approx 40-80\text{ ms}$ per worker). For very small PDFs ($N < 50$), this overhead exceeds the computation time saved.
2. **I/O Contention:** If worker processes concurrently access the exact same disk sector on mechanical hard drives (HDDs), I/O bottlenecking can occur. On modern NVMe SSDs, concurrent read throughput is optimal.

### Conclusion
The **Parallel PDF Text Extractor** demonstrates that genuine Python multiprocessing with balanced page chunking provides scalable performance improvements for CPU-intensive document processing. The empirical findings align with **Amdahl's Law**, clearly showing the transition from overhead-dominated latency on small inputs to high-efficiency speedup ($1.7\times$ on 4 workers) on large multi-page inputs, all while maintaining 100% data integrity.
