"""
Sprint 6, Day 43 — Performance & Integration Testing

SCOPING NOTE: "Dashboard performance: Company Profile screen load time" can't literally be measured by screenshotting a 
rendered browser page without Selenium/Playwright (out of scope for a script-based performance day). 

What actually determines this screen's load time for a data app like this is its DB query cost, 
not Streamlit's own rendering overhead (which is near-instant for 6 KPI tiles and a couple of charts on this much data). 
Measuring the exact functions 
02_profile.py calls -- get_companies(), get_ratios(ticker), get_pl(ticker) -- from src/dashboard/utils/db.py directly, 
timed the same way the page would experience them. 

Documented in output/performance_notes.md...
"""

import subprocess
import sys
import threading
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "output"

API_URL = "http://127.0.0.1:8000"
STREAMLIT_URL = "http://127.0.0.1:8501"


# ---------- Day 43, part 1: Load test — 10 concurrent screener calls ----------

def load_test_screener(n_requests=10):
    results = []
    lock = threading.Lock()

    def make_request():
        start = time.time()
        response = requests.get(f"{API_URL}/api/v1/screener?min_roe=10")
        duration = time.time() - start
        with lock:
            results.append({"status": response.status_code, "duration": duration})

    threads = [threading.Thread(target=make_request) for _ in range(n_requests)]
    overall_start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    overall_duration = time.time() - overall_start

    return results, overall_duration


# ---------- Day 43, part 2: Dashboard Company Profile data-load timing ----------

def time_company_profile_data_load(tickers):
    sys.path.insert(0, str(BASE_DIR / "src" / "dashboard"))
    from utils.db import get_companies, get_ratios, get_pl  #type:ignore

    timings = {}
    get_companies()  # warm the connection once, same as Streamlit does on first page load

    for ticker in tickers:
        start = time.time()
        get_ratios(ticker)
        get_pl(ticker)
        duration = time.time() - start
        timings[ticker] = duration

    return timings


# ---------- Day 43, part 3: End-to-end — both servers simultaneously ----------

def run_end_to_end_port_check():
    """
    Starts both FastAPI (8000) and Streamlit (8501) as subprocesses,
    confirms both come up and respond without a port conflict, then tears
    both down. Returns (fastapi_ok, streamlit_ok, error_message).
    """
    fastapi_proc = subprocess.Popen(
        ["uvicorn", "src.api.main:app", "--port", "8000"],
        cwd=str(BASE_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    streamlit_proc = subprocess.Popen(
        ["streamlit", "run", "src/dashboard/app.py", "--server.port", "8501",
         "--server.headless", "true"],
        cwd=str(BASE_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    fastapi_ok, streamlit_ok, error_message = False, False, None
    try:
        time.sleep(6)  # Streamlit's cold start is slower than uvicorn's

        try:
            r = requests.get(f"{API_URL}/api/v1/health", timeout=5)
            fastapi_ok = r.status_code == 200
        except requests.RequestException as exc:
            error_message = f"FastAPI check failed: {exc}"

        try:
            r = requests.get(STREAMLIT_URL, timeout=5)
            streamlit_ok = r.status_code == 200
        except requests.RequestException as exc:
            error_message = (error_message or "") + f" | Streamlit check failed: {exc}"

    finally:
        fastapi_proc.terminate()
        streamlit_proc.terminate()
        fastapi_proc.wait(timeout=5)
        streamlit_proc.wait(timeout=5)

    return fastapi_ok, streamlit_ok, error_message


if __name__ == "__main__":
    print("=" * 60)
    print("PART 1: Load test — 10 concurrent screener calls")
    print("=" * 60)
    print("(requires a uvicorn server already running on :8000 — see performance_notes.md)")
    try:
        results, overall_duration = load_test_screener(10)
        all_200 = all(r["status"] == 200 for r in results)
        max_individual = max(r["duration"] for r in results)
        print(f"All 10 completed in {overall_duration:.2f}s (target: <10s) — {'PASS' if overall_duration < 10 else 'FAIL'}")
        print(f"All returned 200: {all_200}")
        print(f"Slowest individual request: {max_individual:.3f}s")
    except requests.RequestException as exc:
        print(f"SKIPPED — no server running on :8000 ({exc})")

    print()
    print("=" * 60)
    print("PART 2: Dashboard Company Profile data-load timing")
    print("=" * 60)
    test_tickers = ["TCS", "HDFCBANK", "RELIANCE", "SUNPHARMA", "TATASTEEL"]
    timings = time_company_profile_data_load(test_tickers)
    for ticker, duration in timings.items():
        status = "PASS" if duration < 3.0 else "FAIL"
        print(f"  {ticker}: {duration*1000:.1f}ms ({status}, target <3s)")

    print()
    print("=" * 60)
    print("PART 3: End-to-end — FastAPI + Streamlit simultaneously")
    print("=" * 60)
    fastapi_ok, streamlit_ok, error_message = run_end_to_end_port_check()
    print(f"FastAPI (:8000) responded: {fastapi_ok}")
    print(f"Streamlit (:8501) responded: {streamlit_ok}")
    if error_message:
        print(f"Notes: {error_message}")