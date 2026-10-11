"""
app.py
======
Flask Web Application for BCS702 Parallel Computing:
Parallel PDF Text Extractor.

Handles custom PDF uploads, runs sequential and multiprocessing extractions,
verifies output correctness, calculates speedup and efficiency,
and cleans up temporary files safely.
"""

import os
import uuid
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
from pypdf import PdfReader

from extractor import (
    extract_sequential,
    extract_parallel,
    verify_correctness,
    calculate_performance_metrics
)

app = Flask(__name__)
app.secret_key = "bcs702-parallel-computing-secret-key"

import tempfile

# Use writable temporary directory in serverless environments (e.g. Vercel)
IS_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
if IS_SERVERLESS:
    UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), "pdf_uploads")
else:
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")

ALLOWED_EXTENSIONS = {"pdf"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename: str) -> bool:
    """Check if uploaded file has a valid .pdf extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET"])
def index():
    """Render main application interface."""
    cpu_cores = os.cpu_count() or 4
    return render_template(
        "index.html",
        cpu_cores=cpu_cores,
        results=None
    )


@app.route("/extract", methods=["POST"])
def extract():
    """
    Handle PDF extraction request via AJAX JSON or Form Post.
    Executes Sequential and Multiprocessing Parallel extractors,
    verifies correctness, computes metrics, and cleans up uploaded files.
    """
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json

    search_term = request.form.get("search_term", "").strip()

    # Worker count selection (1, 2, 4, 8)
    try:
        num_workers = int(request.form.get("num_workers", 4))
        if num_workers not in [1, 2, 4, 8]:
            num_workers = 4
    except (ValueError, TypeError):
        num_workers = 4

    # 1. Validation: Search Term
    if not search_term:
        err_msg = "Validation Error: Please enter a keyword or phrase to search."
        if is_ajax:
            return jsonify({"status": "error", "message": err_msg}), 400
        flash(err_msg, "error")
        return redirect(url_for("index"))

    # 2. Validation: File Upload
    if "pdf_file" not in request.files:
        err_msg = "Validation Error: Missing file. Please select a PDF file to upload."
        if is_ajax:
            return jsonify({"status": "error", "message": err_msg}), 400
        flash(err_msg, "error")
        return redirect(url_for("index"))

    file = request.files["pdf_file"]
    if not file or file.filename == "":
        err_msg = "Validation Error: No file selected. Please choose a valid PDF file."
        if is_ajax:
            return jsonify({"status": "error", "message": err_msg}), 400
        flash(err_msg, "error")
        return redirect(url_for("index"))

    if not allowed_file(file.filename):
        err_msg = "Validation Error: Only standard PDF files (.pdf) are supported."
        if is_ajax:
            return jsonify({"status": "error", "message": err_msg}), 400
        flash(err_msg, "error")
        return redirect(url_for("index"))

    target_pdf_path = None
    temp_file_to_clean = None
    original_filename = secure_filename(file.filename) or "uploaded_document.pdf"

    try:
        # Save uploaded file temporarily with a unique name
        unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
        saved_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(saved_path)
        target_pdf_path = saved_path
        temp_file_to_clean = saved_path

        # 3. Validation: Verify PDF structure and pages
        try:
            reader = PdfReader(target_pdf_path)
            total_pages = len(reader.pages)
            if total_pages == 0:
                raise ValueError("The uploaded PDF contains 0 pages.")
        except Exception as e:
            err_msg = f"Validation Error: Failed to parse PDF document. Details: {e}"
            if is_ajax:
                return jsonify({"status": "error", "message": err_msg}), 400
            flash(err_msg, "error")
            return redirect(url_for("index"))

        # 4. Measure Sequential Execution (Baseline)
        seq_result = extract_sequential(target_pdf_path, search_term, case_sensitive=False)

        # 5. Measure Parallel Execution (Multiprocessing)
        par_result = extract_parallel(target_pdf_path, search_term, num_workers=num_workers, case_sensitive=False)

        # 6. Correctness Verification & Metrics
        verification = verify_correctness(seq_result, par_result)
        metrics = calculate_performance_metrics(
            seq_result["time_seconds"],
            par_result["time_seconds"],
            par_result["workers_used"]
        )

        response_data = {
            "status": "success",
            "filename": original_filename,
            "search_term": search_term,
            "total_pages": total_pages,
            "sequential": {
                "time_sec": round(seq_result["time_seconds"], 5),
                "time_ms": round(seq_result["time_seconds"] * 1000, 2)
            },
            "parallel": {
                "time_sec": round(par_result["time_seconds"], 5),
                "time_ms": round(par_result["time_seconds"] * 1000, 2),
                "workers_requested": num_workers,
                "workers_used": par_result["workers_used"],
                "worker_details": par_result.get("worker_details", [])
            },
            "metrics": metrics,
            "verification": verification,
            "matching_pages": seq_result["matching_pages"],
            "total_matches": seq_result["total_matches"]
        }

        if is_ajax:
            return jsonify(response_data)

        # Fallback for standard non-AJAX POST
        cpu_cores = os.cpu_count() or 4
        return render_template(
            "index.html",
            cpu_cores=cpu_cores,
            results=response_data,
            search_term=search_term,
            num_workers=num_workers
        )

    finally:
        # 7. Safe Cleanup of Temporary Uploaded File
        if temp_file_to_clean and os.path.exists(temp_file_to_clean):
            try:
                os.remove(temp_file_to_clean)
            except Exception as e:
                app.logger.warning(f"Could not remove temporary file {temp_file_to_clean}: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print(" BCS702 Parallel PDF Text Extractor")
    print(f" Detected CPU Logical Cores: {os.cpu_count()}")
    print(" Starting Flask server on http://127.0.0.1:5000 ...")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)

