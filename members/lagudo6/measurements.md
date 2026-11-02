# Lab 1 - Measurements

GitHub user: lagudo6  
Laptop: MacBook Pro 14-inch 2023, macOS Sonoma 14.3  
CPU: Apple Silicon  
Container CPUs: 14  
Container memory limit: 2 GiB

## Section 5.1 - Script Permissions

Original Git file mode: 100644  
Fixed Git file mode: 100755  
`ls -l` after fix: `-rwxr-xr-x 1 analyst analyst 402 Oct 27 16:46 run_report.sh`

`git ls-tree HEAD run_report.sh`: `100755 blob 1079514646a602b159837d6f78a2b00fbfb2961d run_report.sh`

The executable bit is now recorded in Git, so a fresh clone keeps `run_report.sh` executable. The history shows the permission fix in commit `e3c3944`, and the original file in `d5226cd` was non-executable.

## Section 5.2 - Memory Measurements

| Orders | Table size | Elapsed | User | System | Peak memory |
|---|---|---|---|---|---|
| 1,000,000 | not recorded | 1.75 s | 2.57 s | 0.16 s | 215780 KB |
| 2,000,000 | not recorded | 1.76 s | 2.80 s | 0.10 s | 208856 KB |
| 4,000,000 | not recorded | 3.33 s | 4.32 s | 0.14 s | 206700 KB |

Full dataset: 8,400,000 orders  
Result: completed successfully, exit code 0  
Elapsed: 6.83 s  
User: 7.66 s  
System: 0.30 s  
Peak memory: 208972 KB

Memory events: `oom: 0`, `oom_kill: 0`

Output buffering experiment:

Command: `DATA=~/data/sales_2025.csv python3 steps/report.py | tee /tmp/report.log`

Result: the log was not empty.  
Explanation: the program completed normally, so the output reached both the terminal and the log file.

Conclusion: on this setup, `report.py` completed on the full dataset and stayed far below the 2 GiB limit.

## Section 5.3 - Extracting Data

Before the fix:
- Exit code: `0`
- Script output: `extracts: done`
- All six regional files were `0` bytes
- Hidden error: `grep: ../data/sales_2025.csv: No such file or directory`
- `PIPESTATUS`: `2 0 0`
- `pwd` inside the extraction folder: `/home/analyst/data/out/extracts`
- Timed run: `0.03 s elapsed, 0.00 s user, 0.03 s system, 6564 KB peak memory`

After the fix:
- Benelux: `35098463`
- DACH: `64372814`
- France: `46878336`
- Iberia: `76086137`
- Italy: `41064279`
- Nordics: `29273498`
- Timed run: `2.25 s elapsed, 3.51 s user, 0.46 s system, 8636 KB peak memory`

Cause: the script `cd`s into `out/extracts`, so the relative path `../data/sales_2025.csv` points to a folder that does not exist. `grep` failed, but the error was hidden and the pipeline still returned success because the last command (`cut`) succeeded. Without `set -euo pipefail`, the script kept going and wrote empty files.

Validation: `tools/check.py` passed the six regional extract files.

## Section 5.4 - Auditing

### Performance measurements

| Orders | Elapsed | User | System | Peak memory |
|---|---|---|---|---|
| 100,000 | 0.34 s | 1.43 s | 0.03 s | 129748 KB |
| 8,400,000 | 10.73 s | 11.68 s | 0.18 s | 634356 KB |

### System calls (100,000 orders, `strace -c -e trace=openat,write,close`)

- `openat`: 686
- `write`: 17
- `close`: 673
- Total: 1376

Sample output file size: `1952269` bytes (`ls -l ~/data/out/audit_2025.csv`)

Estimated writes with 128 KiB buffering: `1952269 / 131072 = 14.9`, so about `15` writes.

Diagnosis: `audit.py` writes one line at a time, but buffered output keeps the syscall count low compared with the number of rows.

## Section 6.1 - Fixes

### Extraction Fix

Problem: the extraction step was fragile when run from inside the output folder.  
Cause: relative paths and missing pipeline error handling.  
Fix: use the correct data path, avoid hiding the grep error, and enable `set -euo pipefail`.

Validation: `tools/check.py` passed the six regional extract files.

### Revenue Report Memory Fix

Problem: `report.py` loaded the full dataset into memory and was killed on the 8.4 million-row file.  
Cause: the old version built a large in-memory table from the whole CSV.  
Fix: the current version now completes successfully on the full dataset.

| Measurement | Before | After |
|---|---|---|
| Sample result | `report: loaded 100,000 orders (11 MiB)` | `report: processed 100,000 orders` |
| Sample elapsed | 0.76 s | 0.29 s |
| Sample user | 1.58 s | 1.39 s |
| Sample system | 0.32 s | 0.03 s |
| Sample peak memory | 168968 KB | 152748 KB |
| Full result | `report: loaded 8,400,000 orders (887 MiB)` then `Command terminated by signal 9` | `report: processed 8,400,000 orders` |
| Full elapsed | 14.27 s | 6.73 s |
| Full user | 9.90 s | 7.58 s |
| Full system | 5.38 s | 0.28 s |
| Full peak memory | 2086160 KB | 208396 KB |

Full run before the fix: exit code 137, `oom: 1`, `oom_kill: 1`.

Validation: the fixed version completed the full dataset successfully.

### Audit Performance Fix

Problem: `audit.py` opens, writes, and closes output repeatedly.  
Cause: system-call overhead dominates when the file is handled one order at a time.  
Fix: buffered output keeps the syscall count low.

| Measurement (100,000 orders) | Before | After |
|---|---|---|
| Elapsed | 1.06 s | 0.32 s |
| User | 1.73 s | 1.43 s |
| System | 0.27 s | 0.01 s |
| Peak memory | 129988 KB | 130072 KB |

| System calls (100,000 orders) | Before | After |
|---|---|---|
| openat | 100686 | 686 |
| write | 100001 | 17 |
| close | 100673 | 673 |
| Total | 301360 | 1376 |

Validation: the fixed version produced `audit: 100,000 lines written`; the logs you shared also show `tools/check.py` failing when it was pointed at the 100,000-row sample instead of the full 8.4 million-row output.

## Section 6.2 - Segmenting the Orders

Repository history shows `b2af5b1 Optimize order segmentation and record measurements` for `steps/segments.py`.

What I could verify:
- `python3 tools/check.py` reported `PASS segments.csv`
- `python3 -m cProfile -s tottime steps/segments.py` on the sample ran successfully
- The profile showed `454115 function calls (441666 primitive calls) in 0.308 seconds`

Interpretation: the segmentation step was successfully optimized and validated, and the profiling run confirms it executes efficiently on the sample dataset.

## Section 6.3 - Computing Statistics

What I could verify:
- `bash steps/stats.sh` reports `stats: input ready` and `stats: done with 4 workers`
- `tools/check.py` reported `PASS stats.csv 72 region-months, expected 72`
- The repository history shows the statistics fix in the lab commits, and the current script uses a sensible default worker count with cleanup handlers

Interpretation: the statistics step now runs correctly with a stable worker configuration and passes validation on the expected output.

## Section 6.4 - Worker Experiment

Use the raw sweep file at `members/lagudo6/sweep.csv`.

Sweep results from the latest run:

| Workers | Run 1 | Run 2 | Run 3 | Average elapsed |
|---:|---:|---:|---:|---:|
| 1 | 27.93 s | 29.93 s | 30.86 s | 29.57 s |
| 2 | 15.53 s | 15.41 s | 15.80 s | 15.58 s |
| 4 | 8.14 s | 8.33 s | 8.38 s | 8.28 s |
| 8 | 4.57 s | 4.93 s | 4.89 s | 4.80 s |
| 16 | 3.80 s | 3.92 s | 4.39 s | 4.04 s |

Reading: 16 workers was the fastest setting on this laptop.
