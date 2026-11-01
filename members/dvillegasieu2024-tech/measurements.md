# Lab 1 - Measurements

GitHub user: dvillegasieu2024-tech
Laptop: HP OmniBook 7 Laptop 16-ay0xxx, Windows 11 Home
CPU: Intel Core Ultra 7 255H (16 cores, 16 threads)
Container CPUs: 16
Container memory limit: 2 GiB (no swap)
Old version (before fixes): commit d5226cd (initial commit), run from copies saved outside the repository
Fixed version used for "after" measurements: current main (fixes by teammates)

(The fixes were committed by teammates; all the numbers below were measured on my own laptop.)

## Section 5.1 - Script Permissions

ls -l run_report.sh in the container: -rwxrwxrwx 1 root root 402 run_report.sh
./run_report.sh ran on my laptop (report.py was Killed, the other steps still ran).

Explanation: the work folder is on Windows (NTFS), which cannot store Unix permissions, so Docker shows every file as rwxrwxrwx, owned by root. Git on Windows does not track file modes, so the repository kept mode 100644 (no execute bit). On macOS/Linux, ./run_report.sh fails with "Permission denied" because the execute (x) permission is missing for everyone; bash run_report.sh works because bash is the program being run and only needs to read the script. Fixed by a teammate with git update-index --chmod=+x (mode 100644 -> 100755).

## Section 5.2 - Memory Measurements (report.py)

Before the fix (original report.py):

| Orders | Table size | Elapsed | User | System | Peak memory |
|---|---|---|---|---|---|
| 1,000,000 | 106 MiB | 3.19 s | 3.24 s | 0.54 s | 508728 KB |
| 2,000,000 | 211 MiB | 4.19 s | 4.25 s | 0.83 s | 854208 KB |
| 4,000,000 | 423 MiB | 7.60 s | 7.01 s | 1.36 s | 1567104 KB |
| 8,400,000 | 887 MiB | killed | | | |

Full dataset: Killed, exit status 137 (128 + 9 = SIGKILL).
memory.events after three runs: max 5356, oom 3, oom_kill 3 -> the out-of-memory killer, one kill per run.

Why killed although the table is only 887 MiB: the peak is several times the table. read_csv needs parsing buffers, and the script then made 12 filtered monthly copies and concatenated them into a third full copy (pd.concat) while the original table was still in memory. Peak is about 150 MiB fixed + about 345 MiB per million orders, so the whole file needs about 150 + 345 x 8.4 = about 3 GiB, above the 2 GiB limit.

After the fix (read in chunks of 100,000 orders, keep running totals):

| Orders | Elapsed | User | System | Peak memory |
|---|---|---|---|---|
| 1,000,000 | 3.33 s | 3.17 s | 0.43 s | 214296 KB |
| 2,000,000 | 2.67 s | 3.20 s | 0.47 s | 205136 KB |
| 4,000,000 | 4.07 s | 4.46 s | 0.51 s | 205188 KB |
| 8,400,000 | 9.86 s | 8.84 s | 1.25 s | 205332 KB |

Peak memory is now constant (about 200 MB) whatever the size of the file.

### Output buffering experiment

python3 report_old.py | tee /tmp/report.log -> the log was empty.
python3 -u report_old.py | tee /tmp/report.log -> the line "report: loaded 8,400,000 orders (887 MiB)" is in the log; echo ${PIPESTATUS[@]} printed 137 0.

Explanation: when stdout is a pipe, Python uses block buffering instead of line buffering. The process was killed with SIGKILL before the buffer was flushed, so the line was lost. -u (unbuffered) writes it immediately. The pipeline's exit status is tee's (0), which hides python's 137.

## Section 5.3 - Extracting Data (extracts.sh)

Before the fix: "extracts: done", exit status 0, all six files 0 bytes.
Pipeline run by hand from ~/data/out/extracts without 2>/dev/null:
grep: ../data/sales_2025.csv: No such file or directory -> 0 rows, PIPESTATUS 2 0 0.

Explanation: the script does cd "$OUT/extracts", so the relative path ../data/sales_2025.csv means ~/data/out/data/sales_2025.csv, which does not exist. 2>/dev/null hid grep's error, the status of the pipeline is cut's (0), and nothing checks errors, so the script printed done and exited 0.

After the fix (set -euo pipefail, absolute path from DATA, no 2>/dev/null):
2.87 s elapsed, 3.49 s user, 1.01 s system, 8008 KB peak memory, exit status 0.
Files: Benelux 35098463 B, DACH 64372814 B, France 46878336 B, Iberia 76086137 B, Italy 41064279 B, Nordics 29273498 B.
User + system > elapsed because grep and cut run at the same time on different CPUs.

## Section 5.4 - Auditing (audit.py)

| Measurement (8.4 million orders) | Before | After |
|---|---|---|
| Elapsed | 56.26 s | 11.86 s |
| User | 39.27 s | 12.25 s |
| System | 17.12 s | 0.73 s |
| Peak memory | 635528 KB | 635116 KB |

Sample (100,000 orders) before the fix: 1.32 s elapsed, 1.98 s user, 0.35 s system.

| System calls (100,000 orders) | Before | After |
|---|---|---|
| openat | 100689 | 689 |
| write | 100001 | 17 |
| close | 100677 | 677 |
| Total | 301367 | 1383 |

Kernel share of CPU time: 17.12 / 56.39 = about 30% before, 0.73 / 12.98 = about 6% after.
The original opened, wrote and closed the file once per order. The fix opens it once and writes through Python's 128 KiB buffer: the sample file is 1952269 bytes, about 15 buffer flushes. On the full file (180634390 bytes), about 1,380 writes instead of 8.4 million.
The comment "so that each line is saved on disk" is wrong: close() only hands the data to the kernel's page cache; only fsync() forces it to disk.

## Section 6.2 - Segmenting the Orders (segments.py)

| Measurement (8.4 million orders) | Before | After |
|---|---|---|
| Elapsed | 34.97 s | 9.05 s |
| User | 35.26 s | 8.61 s |
| System | 0.63 s | 1.06 s |
| Peak memory | 743868 KB | 193024 KB |

Almost all user time, so the cost is in the program's own Python code.
cProfile on the sample (100,000 orders): 3,646,592 function calls in 1.997 s. segment() called 100,000 times (cumtime 0.970 s); datetime.strptime called 100,000 times (cumtime 0.917 s, of which _strptime 0.798 s).
Fix (by a teammate): vectorized pandas/NumPy operations on whole columns (pd.to_datetime(...).dt.quarter, np.where, groupby().size()), in chunks of 100,000 orders.

## Section 6.3 - Computing Statistics (stats.sh)

Before the fix: WORKERS=1 bash stats_old.sh, Ctrl-C after "input ready". ps -ef showed python3 steps/stats_worker.py 0 1 still running (99% CPU) with parent PID 1: the bash script died, but the background workers started with & ignore SIGINT and were adopted by init. Removed with kill (SIGTERM).
After the fix: Ctrl-C -> exit status 130 (128 + 2, SIGINT), no worker left in ps -ef. The script saves each worker's PID ($!) and a trap on EXIT kills them; the default number of workers now follows the CPUs available.

## Section 6.4 - Worker Experiment (average of 3 runs, 8.4 million orders)

| Workers | Elapsed | User | System | Speed-up |
|---|---|---|---|---|
| 1 | 33.32 s | 28.21 s | 7.24 s | 1.0x |
| 2 | 21.45 s | 29.96 s | 11.85 s | 1.6x |
| 4 | 11.95 s | 31.96 s | 13.65 s | 2.8x |
| 8 | 9.15 s | 40.64 s | 22.01 s | 3.6x |
| 16 | 8.87 s | 70.24 s | 49.08 s | 3.8x |

Reading: good speed-up up to 4 workers, small from 4 to 8, almost none from 8 to 16, while user + system time grows from about 35 s to about 119 s. Extra workers add overhead (process start-up, scheduling, context switches, contention for memory and caches), and the Core Ultra 7 255H mixes 6 fast P-cores with slower E-cores, so the last workers run on slower cores. The serial parts (preparing the input, the final sort) do not speed up (Amdahl's law). Raw data: sweep.csv.
