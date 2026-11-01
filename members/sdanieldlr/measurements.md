# Lab 1 Measurements

## 5.1 Warm-up: Generating the Report

- Execute permission (x) was missing on run_report.sh.
- bash reads the script as a text file and does not require execute permission.
- Some laptops were missing the execute bit or their Git was not recognizing it as executable (100644). Different systems preserved the Unix execute bit differently.

fixed both problems with chmod +x run_report and git update-index --chmod=+x run_report

## 5.2 Task 1: Report memory table

- Exit status 137: When a Linux process finishes normally, it returns an exit code between 0 (success) and 127 (error codes the process generates itself). Linux reserves codes 128 and above to indicate that the process was closed involuntarily. The signal used for killing applications is SIGKILL (which is assigned the number 9). The exit status is calculated at 128 + 9 = 137. The program was stopped by the kernel because the container ran out of memory. We can confirm that with oom_kill in memory.events (the oom_kill happened four times).

- Total memory usage was more than 2 GB. Python parses the CSV into objects (like strings, lists, etc.) which all need extra memory for metadata and pointers which costs extra Python overhead.

| Orders | Table size | Elapsed | User | System | Peak memory |
|---|---|---|---|---|---|
| 1,000,000 | 106 MiB | 7.59 s | 5.85 s | 2.21 s | 510812 KB |
| 2,000,000 | 211 MiB | 8.38 s | 6.65 s | 2.29 s | 855200 KB |
| 4,000,000 | 423 MiB | 15.85 s | 13.33 s | 3.30 s | 1571232 KB |
| 8,400,000 | 887 MiB | 28.66 s | 22.57 s | 6.46 s | 2087692 KB |

- The whole file needed 2087692 KB, which is about 2.0 GiB, much more than the size of the table itself. The container's memory limit is only 2147483648 bytes or 2.0 GiB, which shows why the process using the whole file was killed.

- “tee” shows the output on the terminal and writes it to a file at the same time. It only captures what gets flushed into stdout. SIGKILL killed the process before the output was written safely (which was buffered first by Python).

## 5.3 Task 2: Extracting Data

- The files were empty because extracts.sh pointed grep to a non-existent input. We're working in the directory ~/data/out/extracts, and so ~/data/sales_2025.csv points to a non-existent file.

- "echo" prints text to the terminal, so it printed that it was done.

- The script avoided checking if grep successfully found the input file (2>/dev/null). The script hid that grep failed, but it still ran.

- -e = errexit (exits when there’s an error). -u = unset variable (variable with no assigned value). -o = for activating a named shell option. pipefail = the shell option in question (fails the whole pipeline if any command fails). We put set -euo pipefail at the beginning of the script to set its behavior (before the rest of the commands).

## 5.4 Task 3: Auditing

Sample of 100,000 orders:
- audit: 100,000 lines written 
- 4.96 s elapsed
- 3.25 s user
- 2.38 s system
- 129388 KB peak memory

Full dataset:
- audit: 8,400,000 lines written 
- 255.21 s elapsed
- 125.21 s user
- 130.51 s system (spends a lot of time in kernel/syscalls)
- 635676 KB peak memory

Questions:

- 100,001 write (per output line). 100,677 close (open and close activity). 100,691 openat (file openings). 19 errors on openat (some attempts failed but script kept continuing). It seems like audit.py uses a lot of system calls as it writes one line per observation and has to repeatedly close and open.

- More time went into kernel processes than the user. The share of system time for running audit.py (51.14%) was higher than running report.py (22.54%).

- Opening and closing the file for every order does not guarantee the data is physically on disk immediately. write() writes into Python’s buffer, and close() flushes that buffer to the OS. The OS may still keep the data in its cache before writing it to the physical disk.

- Given the 1952269 bytes file size and the 131072 bytes buffer, it would take about 15 (14.9) write syscalls for Python to complete the file given its buffer limit.

## 6.1 Fixes

Extraction fix:
- set -euo pipefail # added this to set the behavior of the script if there is an error
- DATA=${DATA:-$HOME/data/sales_2025.csv} # if there is no value already, it sets DATA as ~/data/sales_2025.csv (and it always sends it to the home directory)
- grep ",$region," "$DATA"... # kept the variable as what was set in the beginning
- removed 2>/dev/null so that errors aren't hidden

| Measurement | Before | After |
|---|---|---|
| Elapsed | 0.08 s | 5.65 s |
| User | 0.01 s | 6.16 s |
| System | 0.04 s | 3.40 s |
| Peak memory | 7972 KB | 8096 KB |

OOM Killer fix:

The way the program is scripted uses up too much memory (it loads the whole file at once and then creates several extra DataFrames and temporary copies while converting dates, computing revenue, splitting by month, and grouping).

- for chunk in pd.read_csv(DATA, chunksize=100000) # reads the data in chunks instead of all at once
- creates a group by table "monthly" for each chunk that already has the total revenue
- adds the partial sum "monthly" table to the "totals" table (instead of creating 12 new tables and combining them)

| Measurement | Before | After |
|---|---|---|
| Elapsed | 28.66 s | 18.49 s |
| User | 22.57 s | 16.31 s |
| System | 6.46 s | 2.71 s |
| Peak memory | 2087692 KB | 204700 KB |

Syscall fix:

The system call being placed inside the for loop increases the kernel time. The for loop should be placed inside the system call instead.

- remove "open(path,"w").close()" # we don't need it if we're already doing it later in the script
- change "with open(path, "a") as f:" to "with open(path, "w") as f:"
- place the for loop inside "with open(path, "a") as f:" instead

| Measurement | Before | After |
|---|---|---|
| Elapsed | 255.21 s | 31.53 s |
| User | 125.21 s | 29.12 s |
| System | 130.51 s | 2.85 s |
| Peak memory | 635676 KB | 646020 KB |

## 6.2 segments.py

Fixed by teammate hyeranyanieu2024-png (see his commits and his measurements.md).

Problem:
- the entire dataset is loaded onto memory
- every thing is processed row by row (for loop goes through each order)
- the segment(order) function is done on each row
- counts stores the results in a dictionary adding extra overhead

Solution:
- file is read in chunks
- using vectors (pandas/numpy) to do calculations on multiple rows at once
- grouping each chunk
- adding partial counts together in the end

Measurement with 100,000 orders

| Measurement | Before | After |
|---|---|---|
| Elapsed | 1.84 s | 1.86 s |
| User | 2.56 s | 1.70 s |
| System | 0.27 s | 0.72 s |
| Peak memory | 133960 KB | 157376 KB |

## 6.3 stats.sh

Fixed by teammate hyeranyanieu2024-png (see his commits and his measurements.md).

"Worker" 
- a separate process that accomplishes one part of a job in parallel with others
- too many can also cause overhead/instability 

Problem:
- script keeps going even if stats_prepare.py fails
- wait does not show which worker failed
- Ctrl-C does not stop background worker processes from running
- uses fixed 16 workers
- child scripts may not see output
- didn't clean up properly on failure or interrupt

Solution:
- adds set -euo pipefail
- picks a sensible worker count based on the machine
- ensures child scripts see output
- keeps track of workers
- kills background workers if script exits
- cleans up child processes as well

## 6.4 Worker Experiment

| Workers | Elapsed | User | System | Speed-up |
|---|---|---|---|---|
| 1 | 91.93 s | 71.65 s | 22.25 s | 1.00x |
| 2 | 65.55 s | 84.90 s | 39.26 s | 1.40x |
| 4 | 39.28 s | 98.84 s | 47.86 s | 2.34x |
| 8 | 30.00 s | 149.80 s | 64.84 s | 3.06x |
| 16 | 26.34 s | 264.12 s | 110.27 s | 3.49x |

The best elapsed time came from 16 workers, but the extra workers also increased total user and system time, showing that parallelism helped until overhead started to dominate.