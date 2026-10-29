# Lab 1 - Measurements

GitHub user: hyeranyanieu2024-png
Laptop: Microsoft Surface Laptop 4, Windows 11 Enterprise
CPU: Intel Core i7-1185G7
Container CPUs: 8
Container memory limit: 2 GiB

## Section 5.1 - Script Permissions

Docker permissions: -rwxrwxrwx
Original Git file mode: 100644
Fixed Git file mode: 100755

The script ran in Docker, but Git did not record its executable permission. Fixed using git update-index --chmod=+x run_report.sh.

## Section 5.2 - Memory Measurements

| Orders | Table size | Elapsed | User | System | Peak memory |
|---|---|---|---|---|---|
| 1,000,000 | 106 MiB | 3.03 s | 3.11 s | 0.43 s | 507988 KB |
| 2,000,000 | 211 MiB | 4.59 s | 4.34 s | 0.73 s | 856316 KB |
| 4,000,000 | 423 MiB | 9.56 s | 8.19 s | 1.81 s | 1570212 KB |

Full dataset: 8,400,000 orders
Reported table size: 887 MiB
Result: Process killed due to memory exhaustion.

Memory event observations:
Initial oom_kill: 1
After tee experiment oom_kill: 2

The total memory needed for 8.4 million orders is estimated at approximately 3 GiB, exceeding the container's 2 GiB limit.

## Output Buffering Experiment

Command: python3 steps/report.py | tee /tmp/report.log

Result: The log was empty.
Explanation: Python buffered stdout when connected to a pipe. The process was killed before the buffered message could be flushed.

## Section 5.4 - Auditing

### Performance measurements

| Orders | Elapsed | User | System | Peak memory |
|---|---|---|---|---|
| 100,000 | 5.55 s | 3.43 s | 1.89 s | 129468 KB |
| 8,400,000 | 252.64 s | 169.99 s | 82.12 s | 636060 KB |

### System calls (100,000 orders)

openat: 100691
write: 100001
close: 100677
Total: 301369

Sample output file size: 1952269 bytes

Estimated writes with 128 KiB buffering: 15

Diagnosis: The script repeatedly opens, writes to, and closes the output file. Keeping the file open and buffering writes would greatly reduce system-call overhead.

## Section 6.1 - Extraction Fix

Problem: All six regional CSV files were empty.

Cause: Incorrect input file path, hidden grep errors, and missing pipeline error handling.

Fix: Use the DATA variable, remove error suppression, and enable set -euo pipefail.

| Measurement | Before | After |
|---|---|---|
| Elapsed | 0.17 s | 8.70 s |
| User | 0.02 s | 9.15 s |
| System | 0.13 s | 4.92 s |
| Peak memory | 8108 KB | 8064 KB |

Validation: All six regional extraction files PASS tools/check.py.

## Section 6.1 - Revenue Report Memory Fix

Problem: report.py was killed while processing 8.4 million orders.

Cause: Loading the entire dataset and creating monthly DataFrame copies exceeded the container's 2 GiB memory limit.

Fix: Process the dataset in chunks of 100,000 orders and accumulate monthly revenue totals.

Before fix:
- Full dataset: killed by OOM
- Reported table size: 887 MiB
- Estimated peak memory: approximately 3 GiB

After fix:
- Orders processed: 8,400,000
- Elapsed: 28.12 s
- User: 24.81 s
- System: 3.66 s
- Peak memory: 203812 KB
- Result: Completed successfully

Validation: PASS revenue_by_region_month.csv using tools/check.py.

## Section 6.1 - Audit Performance Fix

Problem: audit.py opened and closed the output file for every order.

Cause: Repeated file operations generated excessive system calls and kernel overhead.

Fix: Open the output file once and use buffered writes.

### Performance (8.4 million orders)

| Measurement | Before | After |
|---|---|---|
| Elapsed | 252.64 s | 49.04 s |
| User | 169.99 s | 46.96 s |
| System | 82.12 s | 2.53 s |
| Peak memory | 636060 KB | 635972 KB |

### System calls (100,000 orders)

| Call | Before | After |
|---|---|---|
| openat | 100691 | 691 |
| write | 100001 | 17 |
| close | 100677 | 677 |
| Total | 301369 | 1385 |

Result: Approximately 81% reduction in elapsed time and 99.54% fewer system calls.

Validation: PASS audit_2025.csv with 8,400,000 rows using tools/check.py.

## Section 6.2 - Segmenting the Orders

Problem: segments.py processed every order individually and repeatedly parsed dates using datetime.strptime.

Cause: Python-level loops and millions of individual date conversions created excessive processing overhead.

Fix: Use vectorized Pandas operations, NumPy classification, and chunked processing with 100,000 orders per chunk.

### Sample performance (100,000 orders)

| Measurement | Before | After |
|---|---|---|
| Elapsed | 3.42 s | 2.09 s |
| User | 3.26 s | 2.00 s |
| System | 0.51 s | 0.38 s |
| Peak memory | 133776 KB | 156692 KB |

### Full dataset (8.4 million orders)

- Elapsed: 23.21 s
- User: 21.32 s
- System: 2.24 s
- Peak memory: 188768 KB

Result: Approximately 39% faster on the sample dataset.

Validation: PASS segments.csv using tools/check.py.

## Section 6.3 - Computing Statistics

Problem: stats.sh launched 16 workers by default and did not properly clean up background processes.

Fix: Set the default to 4 workers, track worker PIDs, add signal handlers, and terminate child processes during cleanup.

### Worker comparison (100,000-order sample)

| Workers | Elapsed | User | System |
|---|---|---|---|
| 2 | 1.57 s | 3.45 s | 0.20 s |
| 4 | 1.39 s | 3.81 s | 0.32 s |
| 8 | 2.36 s | 6.18 s | 1.05 s |
| 16 | 2.18 s | 9.93 s | 1.90 s |

Four workers were fastest in these sample tests.

### Modified script - Sample

- Workers: 4
- Elapsed: 1.37 s
- User: 4.02 s
- System: 0.31 s
- Peak memory: 112956 KB

### Modified script - Full dataset

- Workers: 4
- Elapsed: 34.28 s
- User: 84.13 s
- System: 26.46 s
- Peak memory: 1006452 KB

Process cleanup: No matching statistics worker processes remained after interruption. The test did not conclusively establish whether workers had started before the interruption.

Validation: PASS stats.csv with 72 region-month groups using tools/check.py.

### Final Ctrl+C cleanup verification

Command: WORKERS=1 bash steps/stats.sh

Before interruption:
- Worker PID: 2172
- Parent PID: 2160
- Verified using ps -eo pid,ppid,stat,args

After Ctrl+C:
- The statistics script was interrupted.
- No matching stats_worker.py processes remained.
- Process cleanup verified.
