
### Experimental Benchmark Results: `small_5pages.pdf`
- **Document Size:** 5 pages
- **Search Term:** `"Amdahl"` (24 matches found)
- **Trials per Config:** 1 (Averaged)
- **Sequential Baseline Time ($T_s$):** 65.69 ms (0.0657 s)

| Process Model | Worker Count ($p$) | Avg Execution Time ($T_p$) | Speedup ($S = T_s / T_p$) | Efficiency ($E = S / p \times 100\%$) | Correctness |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Sequential** | 1 | 65.69 ms | 1.000x | 100.00% | Baseline |
| **Multiprocessing** | 2 | 364.72 ms | **0.180x** | 9.01% | PASSED |

#### Academic Observation:
- For document size (5 pages), sequential execution was faster due to process spawning and inter-process communication (IPC) coordination overhead on Windows.


### Experimental Benchmark Results: `small_5pages.pdf`
- **Document Size:** 5 pages
- **Search Term:** `"Amdahl"` (24 matches found)
- **Trials per Config:** 2 (Averaged)
- **Sequential Baseline Time ($T_s$):** 40.89 ms (0.0409 s)

| Process Model | Worker Count ($p$) | Avg Execution Time ($T_p$) | Speedup ($S = T_s / T_p$) | Efficiency ($E = S / p \times 100\%$) | Correctness |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Sequential** | 1 | 40.89 ms | 1.000x | 100.00% | Baseline |
| **Multiprocessing** | 2 | 363.32 ms | **0.113x** | 5.63% | PASSED |
| **Multiprocessing** | 4 | 456.54 ms | **0.090x** | 2.24% | PASSED |

#### Academic Observation:
- For document size (5 pages), sequential execution was faster due to process spawning and inter-process communication (IPC) coordination overhead on Windows.


### Experimental Benchmark Results: `medium_30pages.pdf`
- **Document Size:** 30 pages
- **Search Term:** `"Amdahl"` (152 matches found)
- **Trials per Config:** 2 (Averaged)
- **Sequential Baseline Time ($T_s$):** 127.70 ms (0.1277 s)

| Process Model | Worker Count ($p$) | Avg Execution Time ($T_p$) | Speedup ($S = T_s / T_p$) | Efficiency ($E = S / p \times 100\%$) | Correctness |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Sequential** | 1 | 127.70 ms | 1.000x | 100.00% | Baseline |
| **Multiprocessing** | 2 | 412.32 ms | **0.310x** | 15.49% | PASSED |
| **Multiprocessing** | 4 | 509.19 ms | **0.251x** | 6.27% | PASSED |

#### Academic Observation:
- For document size (30 pages), sequential execution was faster due to process spawning and inter-process communication (IPC) coordination overhead on Windows.


### Experimental Benchmark Results: `large_100pages.pdf`
- **Document Size:** 100 pages
- **Search Term:** `"Amdahl"` (508 matches found)
- **Trials per Config:** 2 (Averaged)
- **Sequential Baseline Time ($T_s$):** 388.05 ms (0.3881 s)

| Process Model | Worker Count ($p$) | Avg Execution Time ($T_p$) | Speedup ($S = T_s / T_p$) | Efficiency ($E = S / p \times 100\%$) | Correctness |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Sequential** | 1 | 388.05 ms | 1.000x | 100.00% | Baseline |
| **Multiprocessing** | 2 | 550.77 ms | **0.705x** | 35.23% | PASSED |
| **Multiprocessing** | 4 | 612.29 ms | **0.634x** | 15.84% | PASSED |

#### Academic Observation:
- For document size (100 pages), sequential execution was faster due to process spawning and inter-process communication (IPC) coordination overhead on Windows.

