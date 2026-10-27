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
