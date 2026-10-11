"""
generate_sample_pdf.py
======================
Utility script to generate realistic synthetic PDF documents of various sizes
(Small ~5 pages, Medium ~30 pages, Large ~100 pages) for testing and benchmarking
the Parallel PDF Text Extractor.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak


SAMPLE_TEXT_TEMPLATES = [
    (
        "Parallel Computing and High Performance Systems",
        "Parallel computing is a type of computation in which many calculations or processes "
        "are carried out simultaneously. Large problems can often be divided into smaller ones, "
        "which can then be solved at the same time. There are several different forms of parallel "
        "computing: bit-level, instruction-level, data, and task parallelism. In modern multi-core "
        "architectures, achieving maximum speedup requires minimizing synchronization overhead "
        "and balanced workload distribution among active worker processes."
    ),
    (
        "Amdahl's Law and Theoretical Speedup Bounds",
        "Amdahl's law is a formula which gives the theoretical speedup in latency of the execution "
        "of a task at fixed workload that can be expected of a system whose resources are improved. "
        "Named after computer scientist Gene Amdahl, it states that if a program has a serial portion "
        "s, the maximum achievable speedup using p processors is bounded by 1 / (s + (1 - s) / p). "
        "Even with an infinite number of processors, the speedup can never exceed 1 / s."
    ),
    (
        "Process Scheduling and Concurrency in Operating Systems",
        "Concurrency is the execution of multiple instruction sequences at the same time. "
        "In modern operating systems, multiprocessing allows true parallel execution on multiple "
        "CPU cores, avoiding the limitations of the Global Interpreter Lock (GIL) found in CPython. "
        "When designing parallel algorithms, worker allocation and process creation cost must be "
        "carefully evaluated to avoid performance degradation on small computational jobs."
    ),
    (
        "Data Partitioning and Load Balancing",
        "In distributed and shared-memory parallel computing, load balancing refers to the practice "
        "of distributing work evenly across available computing resources. A parallel efficiency metric "
        "measures the fraction of time for which processors are being used constructively. "
        "Imbalanced partitions cause worker starvation where fast workers idle while waiting for the slowest."
    ),
    (
        "Inter-Process Communication and Overhead",
        "Inter-process communication (IPC) mechanisms allow processes to manage shared data. "
        "However, excessive serialization (pickling) and IPC bandwidth can become a significant bottleneck. "
        "In our PDF extractor design, each worker independently reads its assigned page range from disk, "
        "eliminating redundant memory transfers across process boundaries and boosting throughput."
    )
]


def generate_pdf(filename: str, target_pages: int = 10, search_keyword: str = "Amdahl") -> str:
    """
    Generates a PDF file with approximately target_pages pages.
    
    Args:
        filename: Destination filepath for the PDF.
        target_pages: Number of pages to generate.
        search_keyword: A specific keyword to pepper across pages for testing.
        
    Returns:
        The path of the created PDF file.
    """
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor='#1e293b',
        spaceAfter=12
    )

    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor='#334155',
        spaceAfter=8
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor='#475569',
        spaceAfter=10
    )

    story = []

    for page_num in range(1, target_pages + 1):
        story.append(Paragraph(f"Parallel Computing Benchmark Document — Page {page_num} of {target_pages}", title_style))
        story.append(Spacer(1, 10))

        # Add 3-4 sections per page to create realistic text volume
        for section_idx in range(4):
            template_idx = (page_num + section_idx) % len(SAMPLE_TEXT_TEMPLATES)
            sec_title, sec_text = SAMPLE_TEXT_TEMPLATES[template_idx]

            # Inject target keyword conditionally (e.g. every even page or specific pages)
            extra_sentence = ""
            if page_num % 2 == 0 or page_num % 3 == 0:
                extra_sentence = (
                    f" Notice: The keyword '{search_keyword}' is discussed in detail within Section "
                    f"{section_idx + 1} regarding system scaling and parallel efficiency benchmarks."
                )

            story.append(Paragraph(f"{sec_title} (Section {section_idx + 1})", section_style))
            story.append(Paragraph(f"{sec_text}{extra_sentence}", body_style))
            story.append(Spacer(1, 8))

        # Page break if not the last page
        if page_num < target_pages:
            story.append(PageBreak())

    doc.build(story)
    return filename


def generate_test_suite(output_dir: str = "sample_pdfs") -> dict:
    """
    Generates small, medium, large, and xlarge test PDFs for laboratory benchmarks.
    """
    os.makedirs(output_dir, exist_ok=True)
    files = {
        "small": generate_pdf(os.path.join(output_dir, "small_5pages.pdf"), target_pages=5, search_keyword="Amdahl"),
        "medium": generate_pdf(os.path.join(output_dir, "medium_30pages.pdf"), target_pages=30, search_keyword="Amdahl"),
        "large": generate_pdf(os.path.join(output_dir, "large_100pages.pdf"), target_pages=100, search_keyword="Amdahl"),
        "xlarge": generate_pdf(os.path.join(output_dir, "xlarge_400pages.pdf"), target_pages=400, search_keyword="Amdahl"),
    }
    return files


if __name__ == "__main__":
    print("Generating benchmark sample PDF files...")
    suite = generate_test_suite()
    print("Successfully generated test suite:")
    for key, path in suite.items():
        print(f"  - {key.upper()}: {path} ({os.path.getsize(path) / 1024:.1f} KB)")
