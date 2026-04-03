#!/bin/bash

# SonoffLAN-InfluxDB E2E Test - Quick Reference Guide
# Run this script to execute the test suite or follow manual commands below

# ============================================================================
# QUICK START - Run All Tests
# ============================================================================

# 1. Run full E2E integration test suite
cd /Users/nattakritj/Documents/Work/SonoffLAN-influx
PYTHONPATH=src .venv/bin/python -m pytest tests/test_e2e_integration.py -v -s

# Expected output: 5 PASSED, 1 FAILED, 2 BLOCKED
# (1 failure = InfluxDB auth gate, 2 blocked = dependent on auth)

# ============================================================================
# DIAGNOSTICS - Troubleshoot Authentication Issue
# ============================================================================

# Run comprehensive diagnostics
PYTHONPATH=src .venv/bin/python -m pytest tests/test_diagnostics.py -v -s

# Run specific diagnostic tests:

# 1. Check token format
PYTHONPATH=src .venv/bin/python -m pytest tests/test_diagnostics.py::TestDiagnostics::test_verify_token_format -v -s

# 2. Check environment setup
PYTHONPATH=src .venv/bin/python -m pytest tests/test_diagnostics.py::TestDiagnostics::test_report_environment -v -s

# 3. Check authentication
PYTHONPATH=src .venv/bin/python -m pytest tests/test_diagnostics.py::TestDiagnostics::test_diagnose_influx_auth -v -s

# 4. Run local E2E workflow (no InfluxDB needed)
PYTHONPATH=src .venv/bin/python -m pytest tests/test_diagnostics.py::TestDiagnostics::test_e2e_workflow_no_influx -v -s

# ============================================================================
# AUTHENTICATION ISSUE - Manual Verification Steps
# ============================================================================

# Step 1: Verify InfluxDB is running
echo "Checking if InfluxDB is running..."
curl -v http://192.168.2.10:8181/ping
# Expected: 204 No Content (if public ping endpoint) or some response

# Step 2: Test token directly with curl
echo "Testing token authentication..."
INFLUX_TOKEN="apivi3_AwBnUa4uyFJw_b5QZl6cZG1X7XriXLxaSelwPoTt8loiGzHXo256oB1ZCHRjkMML5Ajnv_cnO56flhBWdpH10w"
curl -H "Authorization: Token ${INFLUX_TOKEN}" \
     http://192.168.2.10:8181/api/v1/buckets
# Expected: 200 OK with JSON list of buckets

# Step 3: Check for specific bucket
echo "Checking for sonoff_test bucket..."
curl -H "Authorization: Token ${INFLUX_TOKEN}" \
     "http://192.168.2.10:8181/api/v1/buckets?name=sonoff_test"
# Expected: 200 OK with bucket details

# ============================================================================
# FIX THE AUTHENTICATION ISSUE
# ============================================================================

# Option A: Regenerate the token (RECOMMENDED)
# 1. Log into InfluxDB UI: http://192.168.2.10:8181
# 2. Go to: Data → Tokens → Create Token
# 3. Select "Custom Token"
# 4. Grant: Write access to "sonoff_test" bucket
# 5. Copy the full token value
# 6. Update the token in the test script:
#    Edit: tests/test_e2e_integration.py (line 36: self.influx_token = "...")
#    Edit: tests/test_diagnostics.py (line 44: self.influx_token = "...")

# Option B: Check if token expired
# 1. Log into InfluxDB UI: http://192.168.2.10:8181
# 2. Go to: Data → Tokens
# 3. Find the token in the list
# 4. Check "Expires" column for expiration date
# 5. If expired: delete old token and create new one (Option A)

# Option C: Verify bucket exists
# 1. Log into InfluxDB UI: http://192.168.2.10:8181
# 2. Go to: Load Data → Buckets
# 3. Verify "sonoff_test" bucket exists
# 4. If not: create new bucket named "sonoff_test"

# ============================================================================
# AFTER FIXING AUTHENTICATION
# ============================================================================

# Re-run the connectivity test
PYTHONPATH=src .venv/bin/python -m pytest tests/test_e2e_integration.py::TestE2EIntegration::test_02_influx_connectivity -v -s
# Expected: PASSED

# Re-run the full E2E suite
PYTHONPATH=src .venv/bin/python -m pytest tests/test_e2e_integration.py -v -s
# Expected: 8 PASSED (all tests pass)

# ============================================================================
# OUTPUT FILES
# ============================================================================

# Test Reports:
#   - E2E_TEST_REPORT.md           (comprehensive test report)
#   - E2E_TEST_SUMMARY.txt         (this quick reference)
#   - e2e_test_output.log          (test execution log)
#   - diagnostics_output.log       (diagnostic output log)

# Test Code:
#   - tests/test_e2e_integration.py (main E2E test suite - 8 tests)
#   - tests/test_diagnostics.py     (diagnostic tests - 5 tests)

# ============================================================================
# TEST RESULTS SUMMARY
# ============================================================================

# Current Status:
#   ✅ Configuration Parsing        - PASS
#   ✅ Energy Extraction (Single)   - PASS
#   ✅ Energy Extraction (Multi)    - PASS
#   ✅ Environment Setup            - PASS
#   ✅ Token Format Validation      - PASS
#   ❌ InfluxDB Connectivity        - FAIL (401 Unauthorized)
#   ⏸️  Write to InfluxDB            - BLOCKED (awaiting auth)
#   ⏸️  Query InfluxDB               - BLOCKED (awaiting auth)

# What Works:
#   - Device configuration parsing from environment
#   - Energy metric extraction (all UIID variants)
#   - Multi-channel device support
#   - Async I/O patterns
#   - Type safety with TypedDict and dataclasses

# What's Blocked:
#   - InfluxDB write operations (401 token error)

# ============================================================================
# KEY FILES
# ============================================================================

cat << 'MANIFEST'
PROJECT STRUCTURE:
  src/
    __main__.py        - Daemon entry point
    config.py          - Environment config parsing
    extractor.py       - Energy metric extraction
    writer.py          - InfluxDB 3 Core writer
    ewelink/
      __init__.py      - Registry coordinator
      base.py          - Base classes and signals
      local.py         - LAN discovery and comms

  tests/
    test_e2e_integration.py   - 8 E2E test cases
    test_diagnostics.py       - 5 diagnostic tests
    test_extractor.py         - Unit tests for extractor
    test_writer.py            - Unit tests for writer
    conftest.py               - pytest configuration

  Documentation:
    E2E_TEST_REPORT.md        - Full test report
    E2E_TEST_SUMMARY.txt      - This quick reference
    README.md                 - Project overview
    CLAUDE.md                 - Project instructions
    DEVICES.md                - Supported device list

MANIFEST

# ============================================================================
# CONTACT & SUPPORT
# ============================================================================

# For issues with the test suite, check:
# 1. E2E_TEST_REPORT.md (detailed analysis)
# 2. E2E_TEST_SUMMARY.txt (this file)
# 3. Run: PYTHONPATH=src .venv/bin/python -m pytest tests/test_diagnostics.py -v -s

# For InfluxDB token issues, use these curl commands:
# curl http://192.168.2.10:8181/ping
# curl -H "Authorization: Token YOUR_TOKEN" http://192.168.2.10:8181/api/v1/buckets

# ============================================================================
