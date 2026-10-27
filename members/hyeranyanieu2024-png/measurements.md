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
