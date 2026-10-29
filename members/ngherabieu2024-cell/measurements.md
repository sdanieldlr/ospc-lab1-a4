# Lab 1 - Measurements

GitHub user: ngherabieu2024-cell
Laptop: HP Laptop 15-fd0xxx, Windows 11 Pro
CPU: Intel Core i7-1355U (10 cores, 12 threads)
Container CPUs: 12
Container memory limit: 2 GiB
Old version (before fixes): commit c6e2d79
Fixed version used for "after" measurements: commit b2af5b1 (stats.sh still started 16 workers)

(Sections 6.2 and 6.3 were fixed by a teammate; the numbers below were measured on my own laptop.)

## Section 5.1 - Script Permissions

Original Git file mode: 100644
Fixed Git file mode: 100755
ls -l after fix: -rwxr-xr-x 1 analyst analyst 402 Oct 28 16:15 run_report.sh

Docker permissions before the fix (ls -l run_report.sh): -rwxrwxrwx 1 analyst analyst 402 Oct 29 13:46 run_report.sh
./run_report.sh before the fix: it ran (started 13:50:15, finished 13:52:34; report.py was Killed, the other steps still ran, stats used 16 workers).
bash run_report.sh before the fix: same result (13:53:05 to 13:55:23).

Explanation: In Docker on Windows the mounted file shows rwxrwxrwx, so the script ran. But Git on Windows does not track file modes, so the repository recorded it as 100644 (no executable bit). On Linux/macOS or a fresh clone, ./run_report.sh would fail with "Permission denied", while bash run_report.sh would work because bash only reads the file. Fixed using git update-index --chmod=+x run_report.sh, which records mode 100755.

Also visible in this run: the pipeline printed "Nightly report finished" even though report.py was Killed, because the script does not stop on errors.

## Section 5.2 - Memory Measurements

| Orders | Table size | Elapsed | User | System | Peak memory |
|---|---|---|---|---|---|
| 1,000,000 | 106 MiB | 1.88 s | 2.71 s | 0.24 s | 521012 KB |
| 2,000,000 | 211 MiB | 3.13 s | 3.80 s | 0.32 s | 864732 KB |
| 4,000,000 | 423 MiB | 5.86 s | 6.24 s | 0.61 s | 1576236 KB |

Full dataset: 8,400,000 orders
Reported table size: 887 MiB
Result: Process killed, exit code 137 (128 + 9 = SIGKILL, sent by the OOM killer).
Full run before the kill: 11.76 s elapsed, 11.33 s user, 1.23 s system, peak 2091888 KB

Memory event observations (cat /sys/fs/cgroup/memory.events):
- oom_kill: 4 -> 5 -> 6 (it increased after each killed run)
- memory.peak: 38723 -> 42394 -> 60031

Why was it killed although the table is only 887 MiB? The table is not the only memory used: loading and parsing the CSV, the temporary copies made during processing and the Python objects all add to it. From the measurements, about 355752 KB per million orders, so the whole file needs about 3.0 GiB, which is more than the 2 GiB container limit (no swap).

## Output Buffering Experiment

Command: python3 steps/report.py | tee /tmp/report.log

Result: The log was empty.
Explanation: When stdout goes to a pipe, Python buffers it. The process was killed with SIGKILL before the buffer could be flushed, so nothing reached the log.

## Section 5.3 - Extracting Data

Before the fix:
- Exit code: 0 (looked successful)
- All six regional files were 0 bytes
- Error hidden by 2>/dev/null: ../data/sales_2025.csv: No such file or directory
- PIPESTATUS: 2 0 0 (grep failed, cut and the redirect succeeded)
- pwd inside the script: /home/analyst/data/out/extracts

Cause: The script does cd into out/extracts, so the relative path ../data/sales_2025.csv points to a folder that does not exist. grep failed, but 2>/dev/null hid the error, and in a pipeline the exit code is the one of the last command (cut), which succeeded. Without set -euo pipefail the script continued as if nothing happened.

After the fix (file sizes in bytes):
- Benelux: 35098463
- DACH: 64372814
- France: 46878336
- Iberia: 76086137
- Italy: 41064279
- Nordics: 29273498

| Measurement | Before | After |
|---|---|---|
| Elapsed | 0.03 s | 3.13 s |
| User | 0.01 s | 3.45 s |
| System | 0.02 s | 1.45 s |
| Peak memory | 8004 KB | 8076 KB |

The "before" run is fast only because it does no work: grep fails at once and every file stays empty. The "after" run is slower because it really reads and filters the 8.4 million orders.

Fix: use the correct path of the data file (the DATA variable, not a relative path that breaks after cd), remove 2>/dev/null so errors are visible, and add set -euo pipefail so the script stops when a command in the pipeline fails.

## Section 5.4 - Auditing

### Performance measurements (old version)

| Orders | Elapsed | User | System | Peak memory |
|---|---|---|---|---|
| 100,000 | 1.30 s | 2.00 s | 0.37 s | 135348 KB |
| 8,400,000 | 59.79 s | 43.18 s | 17.54 s | 643688 KB |

### System calls (100,000 orders, strace -c -e trace=openat,write,close)

openat: 100689
write: 100001
close: 100677
Total: 301367

Kernel (system) share of the time: 29% for audit (9% for report.py)

Sample output file size: 1952269 bytes (ls -l audit_2025.csv)

Estimated writes with 128 KiB buffering: 1952269 / 131072 = 14.9, so about 15 writes (instead of 100,001).

Diagnosis: audit.py opens the file, writes one line and closes it for every order (100,000 times). Each open/write/close is a system call, so the kernel does most of the work. The comment in the code says it is "saved on disk even if the job crashes", but close() does not guarantee the data is on disk.

## Section 6.1 - Fixes

### Extraction Fix

Problem: All six regional CSV files were empty although the script reported success.
Cause: Wrong relative path after cd, hidden grep error, no pipeline error handling.
Fix: use the correct data path, remove the hidden error output, and enable set -euo pipefail (see the table in Section 5.3).
Validation: tools/check.py PASS for the six extracts.

### Revenue Report Memory Fix

Problem: report.py was killed (exit 137) on the full 8.4 million orders.
Cause: The whole dataset was loaded at once and exceeded the 2 GiB limit.
Fix: read and process the orders in chunks instead of loading the whole file, and keep only the running monthly totals, so memory stays small.

| Measurement | Before | After |
|---|---|---|
| Result | killed (exit 137) | completed, 8,400,000 orders processed |
| Elapsed | 11.76 s (killed) | 8.24 s |
| User | 11.33 s | 8.55 s |
| System | 1.23 s | 0.62 s |
| Peak memory | 2091888 KB | 217236 KB |

Whole pipeline after the fixes (run_report.sh): 54.72 s elapsed, 217.35 s user, 61.88 s system, peak 643408 KB; oom_kill stayed at 6 before and after.

### Audit Performance Fix

Problem: audit.py opened, wrote and closed the output file for every order.
Cause: Hundreds of thousands of system calls, so the kernel overhead dominates.
Fix: Open the output file once and write through the buffer.

| Measurement (8.4 million orders) | Before | After |
|---|---|---|
| Elapsed | 59.79 s | 12.28 s |
| User | 43.18 s | 12.74 s |
| System | 17.54 s | 0.38 s |
| Peak memory | 643688 KB | 641076 KB |

| System calls (100,000 orders) | Before | After |
|---|---|---|
| openat | 100689 | 689 |
| write | 100001 | 17 |
| close | 100677 | 677 |
| Total | 301367 | 1383 |

Result: about 79.5% less elapsed time, 99.54% fewer system calls, kernel share 29% -> 3%.
Validation: tools/check.py PASS for audit_2025.csv (after running on the full data).

## Section 6.2 - Segmenting the Orders

Fixed by teammate hyeranyanieu2024-png (see his commits and his measurements.md).
Problem: segments.py handled every order one by one and parsed each date with datetime.strptime, millions of slow Python-level calls.
Fix (by him): vectorized Pandas and NumPy operations, in chunks of 100,000 orders.

## Section 6.3 - Computing Statistics

Fixed by teammate hyeranyanieu2024-png (see his commits and his measurements.md).
Problems: stats.sh started 16 workers by default (more than the 12 threads of this laptop, so no speed-up), and after Ctrl+C the background workers kept running.
Fix (by him): a sensible default number of workers, and signal handlers that stop the worker processes on interruption.
My own measurements for the effect of the number of workers are in Section 6.4 below.

## Section 6.4 - Worker Experiment (average of 3 runs, 8.4 million orders)

| Workers | Elapsed | User | System | Speed-up |
|---|---|---|---|---|
| 1 | 37.98 s | 34.61 s | 5.75 s | 1.0x |
| 2 | 25.57 s | 40.36 s | 10.50 s | 1.5x |
| 4 | 23.77 s | 69.40 s | 21.55 s | 1.6x |
| 8 | 23.53 s | 129.86 s | 41.81 s | 1.6x |
| 16 | 24.36 s | 199.72 s | 67.75 s | 1.6x |

Reading: Going from 1 to 2 workers helps a lot. From 4 to 16 workers the elapsed time stays flat (about 24 s) while user and system time keep growing, so extra workers only add overhead (scheduling, context switches, memory). 16 workers is more than the 12 threads of the CPU, so they compete for the same cores. Raw data: sweep.csv.
