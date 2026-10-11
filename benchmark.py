"""
benchmark.py
============
Standalone repeatable benchmarking suite for the BCS702 Parallel Computing assignment.
Executes multi-trial performance experiments across different worker process counts (1, 2, 3, 4, 8),
calculates statistical averages, verifies algorithm correctness, and prints academic Markdown tables
ready for direct inclusion in lab reports.
"""

import argparse
import os
import sys
import time
from typing import List, Dict, Any
from extractor import extract_sequential, extract_parallel, verify_correctness, calculate_performance_metrics
from generate_sample_pdf import generate_test_suite


def run_benchmark(pdf_path: str, search_term: str, worker_counts: List[int], trials: int = 3) -> Dict[str, Any]:
    """
    Executes multiple trials of sequential and parallel extraction to gather reliable average times.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

    print("=" * 75)
    print(f"BENCHMARK RUN: {os.path.basename(pdf_path)}")
    print(f"Search Query: '{search_term}' | Trials per configuration: {trials}")
    print("=" * 75)

    # 1. Warm-up & baseline sequential run
    print(f"\n[1/2] Running Sequential Extraction ({trials} trials)...")
    seq_times: List[float] = []
    seq_result = None

    for t in range(trials):
        res = extract_sequential(pdf_path, search_term)
        seq_times.append(res["time_seconds"])
        seq_result = res
        print(f"  Trial {t + 1}: {res['time_seconds'] * 1000:.2f} ms (Matches: {res['total_matches']})")

    avg_seq_time = sum(seq_times) / len(seq_times)
    total_pages = seq_result["total_pages"]
    print(f"  >> Average Sequential Time: {avg_seq_time * 1000:.2f} ms ({avg_seq_time:.4f} s)")

    # 2. Parallel runs across varying worker counts
    print(f"\n[2/2] Running Parallel Extraction across worker counts {worker_counts}...")
    parallel_stats: List[Dict[str, Any]] = []

    for workers in worker_counts:
        p_times: List[float] = []
        par_result = None
        all_trials_verified = True

        print(f"\n  Testing Workers = {workers} ({trials} trials):")
        for t in range(trials):
            pres = extract_parallel(pdf_path, search_term, num_workers=workers)
            p_times.append(pres["time_seconds"])
            par_result = pres

            v = verify_correctness(seq_result, pres)
            if not v["is_verified"]:
                all_trials_verified = False

            print(f"    Trial {t + 1}: {pres['time_seconds'] * 1000:.2f} ms | Verified: {v['is_verified']}")

        avg_par_time = sum(p_times) / len(p_times)
        metrics = calculate_performance_metrics(avg_seq_time, avg_par_time, workers)

        parallel_stats.append({
            "workers": workers,
            "avg_par_time_ms": avg_par_time * 1000,
            "avg_par_time_sec": avg_par_time,
            "speedup": metrics["speedup"],
            "efficiency": metrics["efficiency_percent"],
            "verified": all_trials_verified,
            "total_matches": par_result["total_matches"] if par_result else 0
        })

    return {
        "pdf_name": os.path.basename(pdf_path),
        "total_pages": total_pages,
        "search_term": search_term,
        "trials": trials,
        "avg_seq_time_ms": avg_seq_time * 1000,
        "avg_seq_time_sec": avg_seq_time,
        "seq_matches": seq_result["total_matches"] if seq_result else 0,
        "parallel_stats": parallel_stats
    }


def print_markdown_table(benchmark_data: Dict[str, Any], output_file: str = None):
    """
    Formats the benchmark results as a GitHub Markdown table suitable for academic reports.
    """
    lines = []
    lines.append(f"\n### Experimental Benchmark Results: `{benchmark_data['pdf_name']}`")
    lines.append(f"- **Document Size:** {benchmark_data['total_pages']} pages")
    lines.append(f"- **Search Term:** `\"{benchmark_data['search_term']}\"` ({benchmark_data['seq_matches']} matches found)")
    lines.append(f"- **Trials per Config:** {benchmark_data['trials']} (Averaged)")
    lines.append(f"- **Sequential Baseline Time ($T_s$):** {benchmark_data['avg_seq_time_ms']:.2f} ms ({benchmark_data['avg_seq_time_sec']:.4f} s)\n")
    lines.append("| Process Model | Worker Count ($p$) | Avg Execution Time ($T_p$) | Speedup ($S = T_s / T_p$) | Efficiency ($E = S / p \\times 100\\%$) | Correctness |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
    lines.append(f"| **Sequential** | 1 | {benchmark_data['avg_seq_time_ms']:.2f} ms | 1.000x | 100.00% | Baseline |")

    for stat in benchmark_data["parallel_stats"]:
        status_icon = "PASSED" if stat["verified"] else "MISMATCH"
        lines.append(
            f"| **Multiprocessing** | {stat['workers']} | {stat['avg_par_time_ms']:.2f} ms | "
            f"**{stat['speedup']:.3f}x** | {stat['efficiency']:.2f}% | {status_icon} |"
        )

    lines.append("\n#### Academic Observation:")
    # Speedup insight
    max_stat = max(benchmark_data["parallel_stats"], key=lambda x: x["speedup"])
    if max_stat["speedup"] > 1.0:
        lines.append(
            f"- Maximum speedup of **{max_stat['speedup']:.3f}x** achieved at **{max_stat['workers']} workers**, "
            f"with parallel efficiency of **{max_stat['efficiency']:.2f}%**."
        )
    else:
        lines.append(
            f"- For document size ({benchmark_data['total_pages']} pages), sequential execution was faster due to "
            f"process spawning and inter-process communication (IPC) coordination overhead on Windows."
        )

    formatted_output = "\n".join(lines)
    print(formatted_output)

    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(formatted_output + "\n\n")
        print(f"\n[+] Results successfully appended to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="BCS702 Parallel Computing PDF Extractor Benchmark")
    parser.add_argument("--pdf", type=str, default="", help="Path to PDF file to test (leave blank to use sample)")
    parser.add_argument("--preset", type=str, choices=["small", "medium", "large", "all"], default="large",
                        help="Preset test file to generate and test if --pdf is not specified")
    parser.add_argument("--keyword", type=str, default="Amdahl", help="Keyword or phrase to search")
    parser.add_argument("--trials", type=int, default=3, help="Number of benchmark trials to average")
    parser.add_argument("--workers", nargs="+", type=int, default=[2, 3, 4], help="Worker counts to benchmark")
    parser.add_argument("--output", type=str, default="benchmark_results.md", help="File to append Markdown tables")

    args = parser.parse_args()

    # Ensure sample suite exists
    if not args.pdf or not os.path.exists(args.pdf):
        print("[*] Generating or locating benchmark sample PDFs...")
        suite = generate_test_suite()

        if args.preset == "all":
            targets = [suite["small"], suite["medium"], suite["large"]]
        else:
            targets = [suite[args.preset]]
    else:
        targets = [args.pdf]

    for target in targets:
        data = run_benchmark(
            pdf_path=target,
            search_term=args.keyword,
            worker_counts=args.workers,
            trials=args.trials
        )
        print_markdown_table(data, output_file=args.output)


if __name__ == "__main__":
    main()
