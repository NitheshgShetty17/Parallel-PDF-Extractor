"""
extractor.py
=============
Core logic for the BCS702 Parallel Computing project: Parallel PDF Text Extractor.
Contains both sequential and multiprocessing-based parallel text extraction,
fair performance measurement, automatic correctness verification, and metric calculations.
"""

import os
import re
import time
from multiprocessing import Pool
from typing import Any, Dict, List, Tuple
from pypdf import PdfReader


def extract_snippets(text: str, search_term: str, max_snippets: int = 5, context_chars: int = 60) -> List[str]:
    """
    Extract readable text snippets surrounding the search term.
    
    Args:
        text: Plain text extracted from a PDF page.
        search_term: The keyword or phrase to search for.
        max_snippets: Maximum number of snippet excerpts to return per page.
        context_chars: Number of characters of surrounding context on each side.
        
    Returns:
        List of formatted string snippets with ellipses.
    """
    if not text or not search_term:
        return []

    # Clean whitespace and linebreaks for cleaner display
    cleaned_text = re.sub(r'\s+', ' ', text).strip()
    term_len = len(search_term)
    lower_text = cleaned_text.lower()
    lower_term = search_term.lower()

    snippets: List[str] = []
    start_pos = 0

    while len(snippets) < max_snippets:
        pos = lower_text.find(lower_term, start_pos)
        if pos == -1:
            break

        snippet_start = max(0, pos - context_chars)
        snippet_end = min(len(cleaned_text), pos + term_len + context_chars)

        prefix = "..." if snippet_start > 0 else ""
        suffix = "..." if snippet_end < len(cleaned_text) else ""

        snippet = prefix + cleaned_text[snippet_start:snippet_end] + suffix
        snippets.append(snippet)

        start_pos = pos + term_len

    return snippets


def process_page_chunk(file_path: str, search_term: str, start_page: int, end_page: int, case_sensitive: bool = False) -> Dict[str, Any]:
    """
    Worker function executed by an independent process in the multiprocessing pool.
    
    CRITICAL PARALLEL DESIGN POINT:
    - Instead of serializing and transferring heavy PDF objects across IPC channels,
      each worker receives only the lightweight file path and its assigned page range [start_page, end_page).
    - The worker opens the PDF reader locally and processes only its assigned subset of pages.
    - This eliminates memory duplication and inter-process communication serialization bottlenecks.
    
    Args:
        file_path: Absolute or relative path to the PDF file on disk.
        search_term: The search word or phrase.
        start_page: Zero-based starting page index (inclusive).
        end_page: Zero-based ending page index (exclusive).
        case_sensitive: Whether to perform case-sensitive search.
        
    Returns:
        Dictionary containing worker chunk metadata and list of matching page results.
    """
    matching_pages: List[Dict[str, Any]] = []
    pages_processed = 0

    if not os.path.exists(file_path):
        return {
            "start_page": start_page + 1,
            "end_page": end_page,
            "pages_processed": 0,
            "matching_pages": [],
            "error": f"File not found: {file_path}"
        }

    try:
        reader = PdfReader(file_path)
        term_to_search = search_term if case_sensitive else search_term.lower()

        for page_idx in range(start_page, end_page):
            if page_idx >= len(reader.pages):
                break

            pages_processed += 1
            page = reader.pages[page_idx]
            page_text = page.extract_text() or ""

            text_to_search = page_text if case_sensitive else page_text.lower()

            if term_to_search in text_to_search:
                # Count occurrences
                count = text_to_search.count(term_to_search)
                snippets = extract_snippets(page_text, search_term, max_snippets=4)

                matching_pages.append({
                    "page_number": page_idx + 1,  # 1-indexed for user display
                    "match_count": count,
                    "snippets": snippets
                })

    except Exception as e:
        return {
            "start_page": start_page + 1,
            "end_page": end_page,
            "pages_processed": pages_processed,
            "matching_pages": matching_pages,
            "error": str(e)
        }

    return {
        "start_page": start_page + 1,
        "end_page": end_page,
        "pages_processed": pages_processed,
        "matching_pages": matching_pages,
        "error": None
    }


def get_page_chunks(total_pages: int, num_workers: int) -> List[Tuple[int, int]]:
    """
    Divides the total number of pages into balanced, contiguous index intervals.
    
    Example: 10 pages across 3 workers -> [(0, 4), (4, 7), (7, 10)]
    Worker 1 gets 4 pages; Worker 2 and 3 get 3 pages each.
    
    Args:
        total_pages: Total number of pages in the PDF.
        num_workers: Desired number of worker processes.
        
    Returns:
        List of (start_idx, end_idx) tuples for zero-based slicing.
    """
    if total_pages <= 0 or num_workers <= 0:
        return []

    # If workers exceed total pages, clamp workers to total_pages to avoid empty workers
    active_workers = min(num_workers, total_pages)
    base_chunk = total_pages // active_workers
    remainder = total_pages % active_workers

    chunks: List[Tuple[int, int]] = []
    current_start = 0

    for i in range(active_workers):
        # Distribute the remainder evenly across the first 'remainder' workers
        chunk_size = base_chunk + (1 if i < remainder else 0)
        chunks.append((current_start, current_start + chunk_size))
        current_start += chunk_size

    return chunks


def extract_sequential(file_path: str, search_term: str, case_sensitive: bool = False) -> Dict[str, Any]:
    """
    Executes sequential text extraction on a single process.
    
    Iterates through PDF pages one by one, extracts text using pypdf,
    searches for the keyword, and precisely measures execution time using time.perf_counter().
    
    Args:
        file_path: Path to the target PDF file.
        search_term: Word or phrase to locate.
        case_sensitive: Whether matching should be case-sensitive.
        
    Returns:
        Dictionary containing execution time, page matches, match counts, and snippets.
    """
    t_start = time.perf_counter()

    reader = PdfReader(file_path)
    total_pages = len(reader.pages)
    matching_pages: List[Dict[str, Any]] = []
    total_matches = 0

    term_to_search = search_term if case_sensitive else search_term.lower()

    for page_idx in range(total_pages):
        page = reader.pages[page_idx]
        page_text = page.extract_text() or ""

        text_to_search = page_text if case_sensitive else page_text.lower()

        if term_to_search in text_to_search:
            count = text_to_search.count(term_to_search)
            total_matches += count
            snippets = extract_snippets(page_text, search_term, max_snippets=4)

            matching_pages.append({
                "page_number": page_idx + 1,
                "match_count": count,
                "snippets": snippets
            })

    t_end = time.perf_counter()
    duration = t_end - t_start

    return {
        "method": "sequential",
        "time_seconds": duration,
        "total_pages": total_pages,
        "matching_pages": matching_pages,
        "total_matches": total_matches,
        "pages_with_matches": len(matching_pages),
        "workers_used": 1
    }


def extract_parallel(file_path: str, search_term: str, num_workers: int = 4, case_sensitive: bool = False) -> Dict[str, Any]:
    """
    Executes parallel text extraction using genuine Python multiprocessing.
    
    Divides PDF pages into balanced groups and distributes them across separate worker processes.
    Workers run in parallel, opening the PDF reader locally and extracting their assigned chunks.
    Results are gathered and merged strictly in chronological page order.
    
    Args:
        file_path: Path to the target PDF file.
        search_term: Word or phrase to locate.
        num_workers: Number of worker processes to spawn (e.g. 2, 3, 4).
        case_sensitive: Whether matching should be case-sensitive.
        
    Returns:
        Dictionary containing parallel execution time, results, worker breakdowns, and metrics.
    """
    # Quick metadata inspection to obtain page count
    initial_reader = PdfReader(file_path)
    total_pages = len(initial_reader.pages)

    if total_pages == 0:
        return {
            "method": "parallel",
            "time_seconds": 0.0,
            "total_pages": 0,
            "matching_pages": [],
            "total_matches": 0,
            "pages_with_matches": 0,
            "workers_used": num_workers,
            "chunks": [],
            "worker_details": []
        }

    # Partition pages into balanced chunks
    chunks = get_page_chunks(total_pages, num_workers)
    actual_workers = len(chunks)

    # Prepare arguments for multiprocessing pool
    tasks = [
        (file_path, search_term, start, end, case_sensitive)
        for (start, end) in chunks
    ]

    t_start = time.perf_counter()

    # Multiprocessing pool execution with serverless environment fallback
    try:
        with Pool(processes=actual_workers) as pool:
            worker_outputs = pool.starmap(process_page_chunk, tasks)
    except (OSError, PermissionError, NotImplementedError):
        # Fallback for restricted serverless containers (e.g., AWS Lambda / Vercel Serverless)
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=actual_workers) as executor:
            worker_outputs = list(executor.map(lambda t: process_page_chunk(*t), tasks))

    t_end = time.perf_counter()
    duration = t_end - t_start

    # Merge results in ascending page order
    all_matching_pages: List[Dict[str, Any]] = []
    worker_details: List[Dict[str, Any]] = []
    total_matches = 0

    for worker_idx, out in enumerate(worker_outputs):
        chunk_start, chunk_end = chunks[worker_idx]
        worker_details.append({
            "worker_id": worker_idx + 1,
            "page_range": f"{chunk_start + 1} - {chunk_end}",
            "pages_count": out.get("pages_processed", 0),
            "matches_found": sum(p["match_count"] for p in out.get("matching_pages", [])),
            "error": out.get("error")
        })

        for match_item in out.get("matching_pages", []):
            all_matching_pages.append(match_item)
            total_matches += match_item["match_count"]

    # Guarantee strict ascending page order
    all_matching_pages.sort(key=lambda x: x["page_number"])

    return {
        "method": "parallel",
        "time_seconds": duration,
        "total_pages": total_pages,
        "matching_pages": all_matching_pages,
        "total_matches": total_matches,
        "pages_with_matches": len(all_matching_pages),
        "workers_used": actual_workers,
        "chunks": chunks,
        "worker_details": worker_details
    }


def verify_correctness(seq_res: Dict[str, Any], par_res: Dict[str, Any]) -> Dict[str, Any]:
    """
    Automatically verifies that sequential and parallel implementations
    produced 100% identical search results.
    
    Compares:
    1. Total matches count
    2. Matching page numbers sequence
    3. Per-page match occurrences count
    
    Returns:
        Verification dictionary with boolean flag, diagnostic details, and explanation.
    """
    seq_matches = seq_res.get("matching_pages", [])
    par_matches = par_res.get("matching_pages", [])

    seq_pages = [m["page_number"] for m in seq_matches]
    par_pages = [m["page_number"] for m in par_matches]

    seq_counts = [m["match_count"] for m in seq_matches]
    par_counts = [m["match_count"] for m in par_matches]

    pages_match = (seq_pages == par_pages)
    counts_match = (seq_counts == par_counts)
    total_match = (seq_res.get("total_matches", 0) == par_res.get("total_matches", 0))

    is_verified = pages_match and counts_match and total_match

    if is_verified:
        message = (
            f"Sequential and parallel methods returned identical search results. "
            f"Confirmed {seq_res.get('total_matches', 0)} keyword occurrences across {len(seq_pages)} matching pages."
        )
    else:
        message = (
            f"Result discrepancy detected! "
            f"Pages match: {pages_match}, Counts match: {counts_match}, Total match: {total_match}."
        )

    return {
        "is_verified": is_verified,
        "pages_match": pages_match,
        "counts_match": counts_match,
        "total_matches_match": total_match,
        "seq_matching_pages": seq_pages,
        "par_matching_pages": par_pages,
        "seq_total_matches": seq_res.get("total_matches", 0),
        "par_total_matches": par_res.get("total_matches", 0),
        "pages_with_matches": len(seq_pages),
        "message": message
    }


def calculate_performance_metrics(seq_time: float, par_time: float, num_workers: int) -> Dict[str, Any]:
    """
    Calculates Speedup and Parallel Efficiency from measured execution times.
    
    Formulas:
        Speedup (S) = T_sequential / T_parallel
        Parallel Efficiency (E) = (Speedup / p) * 100%
        
    Args:
        seq_time: Sequential execution time in seconds.
        par_time: Parallel execution time in seconds.
        num_workers: Number of worker processes used.
        
    Returns:
        Dictionary with computed metrics and exact observation description.
    """
    safe_par_time = max(par_time, 1e-7)
    safe_seq_time = max(seq_time, 1e-7)

    speedup = safe_seq_time / safe_par_time

    if num_workers > 0:
        efficiency = (speedup / num_workers) * 100.0
    else:
        efficiency = 0.0

    speedup_card = round(speedup, 3)
    speedup_desc = round(speedup, 2)

    if speedup > 1.05:
        observation = f"Parallel execution is {speedup_desc:.2f}× faster than sequential execution."
    elif speedup >= 0.95:
        observation = f"Sequential and parallel execution times are nearly identical ({speedup_desc:.2f}× speedup)."
    else:
        observation = f"Parallel execution was slower ({speedup_desc:.2f}× speedup) than sequential execution due to process startup overhead."

    return {
        "sequential_time_sec": round(seq_time, 5),
        "parallel_time_sec": round(par_time, 5),
        "sequential_time_ms": round(seq_time * 1000, 2),
        "parallel_time_ms": round(par_time * 1000, 2),
        "speedup": speedup_card,
        "speedup_desc": f"{speedup_desc:.2f}",
        "efficiency_percent": round(efficiency, 2),
        "num_workers": num_workers,
        "observation": observation
    }
