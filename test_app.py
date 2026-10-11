"""
test_app.py
===========
Unit and integration test suite to verify all core functional requirements:
1. Sequential vs Parallel equivalence (100% correctness verification)
2. Validation for missing files, invalid non-PDF uploads, empty search queries
3. Multiprocessing balanced chunking
4. Web endpoints (GET /, POST /extract)
5. Metric calculations (Speedup, Efficiency)
6. Automatic temporary file cleanup
"""

import io
import os
import unittest
from app import app, UPLOAD_FOLDER
from extractor import (
    extract_sequential,
    extract_parallel,
    verify_correctness,
    calculate_performance_metrics,
    get_page_chunks
)
from generate_sample_pdf import generate_test_suite


class TestParallelPDFExtractor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Prepare sample PDFs before running tests."""
        cls.suite = generate_test_suite("sample_pdfs")
        cls.small_pdf = cls.suite["small"]
        cls.medium_pdf = cls.suite["medium"]

    def setUp(self):
        """Create Flask test client."""
        self.client = app.test_client()
        self.client.testing = True

    def test_chunking_logic(self):
        """Test balanced page partitioning among workers."""
        # Case 1: 10 pages across 3 workers -> 4, 3, 3
        chunks_10_3 = get_page_chunks(10, 3)
        self.assertEqual(chunks_10_3, [(0, 4), (4, 7), (7, 10)])
        self.assertEqual(sum(end - start for start, end in chunks_10_3), 10)

        # Case 2: 5 pages across 4 workers -> 2, 1, 1, 1
        chunks_5_4 = get_page_chunks(5, 4)
        self.assertEqual(chunks_5_4, [(0, 2), (2, 3), (3, 4), (4, 5)])
        self.assertEqual(sum(end - start for start, end in chunks_5_4), 5)

        # Case 3: More workers than pages (2 pages across 4 workers) -> 1, 1 (clamped to 2)
        chunks_2_4 = get_page_chunks(2, 4)
        self.assertEqual(chunks_2_4, [(0, 1), (1, 2)])

    def test_sequential_vs_parallel_accuracy(self):
        """Verify sequential and multiprocessing produce identical search results."""
        keyword = "Amdahl"
        seq_res = extract_sequential(self.small_pdf, keyword)
        par_res = extract_parallel(self.small_pdf, keyword, num_workers=2)

        verification = verify_correctness(seq_res, par_res)
        self.assertTrue(verification["is_verified"], "Sequential and Parallel results must match!")
        self.assertEqual(seq_res["total_matches"], par_res["total_matches"])
        self.assertEqual(
            [p["page_number"] for p in seq_res["matching_pages"]],
            [p["page_number"] for p in par_res["matching_pages"]]
        )

    def test_metrics_calculation(self):
        """Verify speedup and efficiency calculations."""
        # 10s sequential, 5s parallel with 2 workers -> speedup 2.0x, efficiency 100%
        m = calculate_performance_metrics(10.0, 5.0, 2)
        self.assertEqual(m["speedup"], 2.0)
        self.assertEqual(m["efficiency_percent"], 100.0)

        # Zero or microsecond time handling
        m_zero = calculate_performance_metrics(0.0, 0.0, 4)
        self.assertIsInstance(m_zero["speedup"], float)
        self.assertIsInstance(m_zero["efficiency_percent"], float)

    def test_web_index_page(self):
        """Verify main web page renders with HTTP 200."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Parallel PDF Text Extractor", response.data)
        self.assertIn(b"BCS702 Parallel Computing", response.data)

    def test_validation_empty_search_term(self):
        """Verify validation rejects empty or whitespace search queries."""
        response = self.client.post("/extract", data={
            "search_term": "   ",
            "num_workers": "2"
        }, headers={"X-Requested-With": "XMLHttpRequest"})
        
        self.assertEqual(response.status_code, 400)
        json_data = response.get_json()
        self.assertIn("Validation Error", json_data["message"])

    def test_validation_missing_file(self):
        """Verify validation rejects requests missing an uploaded PDF."""
        response = self.client.post("/extract", data={
            "search_term": "Amdahl",
            "num_workers": "2"
        }, headers={"X-Requested-With": "XMLHttpRequest"})

        self.assertEqual(response.status_code, 400)
        json_data = response.get_json()
        self.assertIn("Missing file", json_data["message"])

    def test_validation_invalid_file_extension(self):
        """Verify validation rejects non-PDF file uploads."""
        data = {
            "search_term": "Amdahl",
            "num_workers": "2",
            "pdf_file": (io.BytesIO(b"Fake content"), "test_file.txt")
        }
        response = self.client.post("/extract", data=data, content_type="multipart/form-data",
                                    headers={"X-Requested-With": "XMLHttpRequest"})
        self.assertEqual(response.status_code, 400)
        json_data = response.get_json()
        self.assertIn("Only standard PDF files (.pdf) are supported", json_data["message"])

    def test_extract_ajax_endpoint_success(self):
        """Verify full extraction via AJAX POST with uploaded PDF returns complete JSON structure."""
        with open(self.small_pdf, "rb") as f:
            pdf_bytes = f.read()

        data = {
            "search_term": "Amdahl",
            "num_workers": "2",
            "pdf_file": (io.BytesIO(pdf_bytes), "upload_test.pdf")
        }
        response = self.client.post("/extract", data=data, content_type="multipart/form-data",
                                    headers={"X-Requested-With": "XMLHttpRequest"})
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()

        self.assertEqual(json_data["status"], "success")
        self.assertTrue(json_data["verification"]["is_verified"])
        self.assertIn("sequential", json_data)
        self.assertIn("parallel", json_data)
        self.assertIn("metrics", json_data)
        self.assertGreater(json_data["total_matches"], 0)
        self.assertEqual(json_data["parallel"]["workers_used"], 2)

    def test_custom_pdf_upload_and_cleanup(self):
        """Verify custom PDF upload processes correctly and cleans up temporary file."""
        with open(self.small_pdf, "rb") as f:
            pdf_bytes = f.read()

        data = {
            "search_term": "Amdahl",
            "num_workers": "4",
            "pdf_file": (io.BytesIO(pdf_bytes), "temp_cleanup_test.pdf")
        }
        response = self.client.post("/extract", data=data, content_type="multipart/form-data",
                                    headers={"X-Requested-With": "XMLHttpRequest"})
        self.assertEqual(response.status_code, 200)

        # Verify no temporary files remain in uploads folder
        remaining_files = os.listdir(UPLOAD_FOLDER)
        matching_uploads = [f for f in remaining_files if "temp_cleanup_test" in f]
        self.assertEqual(len(matching_uploads), 0, "Uploaded file must be safely removed after processing!")

    def test_worker_selection_clamp(self):
        """Verify worker count clamps to supported options [1, 2, 4, 8]."""
        with open(self.small_pdf, "rb") as f:
            pdf_bytes = f.read()

        # If invalid worker passed (e.g. 99), defaults to 4
        data = {
            "search_term": "Amdahl",
            "num_workers": "99",
            "pdf_file": (io.BytesIO(pdf_bytes), "worker_clamp_test.pdf")
        }
        response = self.client.post("/extract", data=data, content_type="multipart/form-data",
                                    headers={"X-Requested-With": "XMLHttpRequest"})
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data["parallel"]["workers_requested"], 4)


if __name__ == "__main__":
    unittest.main()
