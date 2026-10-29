\# Lab 1 - Measurements



GitHub user: ngherabieu2024-cell

Laptop: HP Laptop 15-fd0xxx, Windows 11 Pro

CPU: Intel Core i7-1355U, 10 cores, 12 threads

Container CPUs (nproc): 12

Container memory limit: 2 GiB



\## Section 5.1 - Script Permissions



Original Git file mode: 100644 (git pull showed: mode change 100644 => 100755 run\_report.sh)

Fixed Git file mode: 100755

ls -l run\_report.sh after the fix: -rwxr-xr-x

Explanation: without the x bit, ./run\_report.sh gives Permission denied, while bash run\_report.sh works because bash reads the file as data. Git on Windows does not see file modes, so the fix needs git update-index --chmod=+x.



\## Section 5.2 - Memory Measurements



| Orders | Table size | Elapsed | User | System | Peak memory |

|---|---|---|---|---|---|

| 1,000,000 | 106 MiB | 1.88 s | 2.71 s | 0.24 s | 521012 KB |

| 2,000,000 | 211 MiB | 3.13 s | 3.80 s | 0.32 s | 864732 KB |

| 4,000,000 | 423 MiB | 5.86 s | 6.24 s | 0.61 s | 1576236 KB |



Full dataset: 8,400,000 orders, reported table size 887 MiB.

Result: killed. Exit status 137 = 128 + 9 (SIGKILL). 11.76 s elapsed, 11.33 s user, 1.23 s system, 2091888 KB peak memory.

oom\_kill: 4 after the first kill, 5 after the timed run, 6 after the tee experiment.

Estimate for the whole file: about 3.0 GiB (about 170 MB fixed cost plus about 355 MB per million orders), above the 2 GiB limit.



\## Output Buffering Experiment



Command: python3 steps/report.py | tee /tmp/report.log

Result: the log was empty.

Explanation: with a pipe, Python buffers stdout and flushes only when the buffer is full or the program ends normally. SIGKILL gives no chance to flush, so the line was lost.



\## Section 5.3 - Extracts (old version)



Exit status: 0. All six files had 0 bytes.

Cause: the script does cd into \~/data/out/extracts and reads ../data/sales\_2025.csv, which means \~/data/out/data/sales\_2025.csv and does not exist. grep fails, 2>/dev/null hides the error, and the pipeline status is the one of its last command.

PIPESTATUS: 2 0 0. pwd: /home/analyst/data/out/extracts.



\## Section 5.4 - Auditing (old version)



| Orders | Elapsed | User | System | Peak memory |

|---|---|---|---|---|

| 100,000 | 1.30 s | 2.00 s | 0.37 s | 135348 KB |

| 8,400,000 | 59.79 s | 43.18 s | 17.54 s | 643688 KB |



System calls (100,000 orders): openat 100689, write 100001, close 100677, total 301367.

Kernel share on the full file: 17.54 / (43.18 + 17.54) = 29%.

Diagnosis: the script opens, writes and closes the output file for every order. close() does not guarantee data is on disk.



\## Section 6.1 - Fixes (after git pull)



Whole pipeline: 54.72 s elapsed, 217.35 s user, 61.88 s system, 643408 KB. oom\_kill 6 before and 6 after.

Extracts sizes: Benelux 35098463, DACH 64372814, France 46878336, Iberia 76086137, Italy 41064279, Nordics 29273498 bytes.



Audit, 8.4 million orders: 59.79 s -> 12.28 s elapsed; system 17.54 s -> 0.38 s; peak memory 643688 KB -> 641076 KB.

Audit, 100,000 orders, system calls: openat 100689 -> 689, write 100001 -> 17, close 100677 -> 677, total 301367 -> 1383.



Report step alone (new): ...

Extracts step alone (new): ...



\## Section 6.2 - Segmenting



| | Elapsed | User | System | Peak memory |

|---|---|---|---|---|

| Sample, old | ... | ... | ... | ... |

| Sample, new | ... | ... | ... | ... |

| Full file, old | ... | ... | ... | ... |

| Full file, new | ... | ... | ... | ... |



\## Section 6.3 - Statistics



Old version: 16 workers on a laptop with 12 threads. After Ctrl-C: ...

New version, full file: ...



\## Section 6.4 - Worker experiment (average of 3 runs, elapsed in seconds)



| Workers | Elapsed | Speed-up |

|---|---|---|

| 1 | 37.98 | 1.0x |

| 2 | 25.57 | 1.5x |

| 4 | 23.77 | 1.6x |

| 8 | 23.53 | 1.6x |

| 16 | 24.36 | 1.6x |



Reading: 2 workers help, 4 to 16 do not. User and system time keep rising (user 33 s to 176 s, system 5 s to 60 s), so the extra workers add overhead. My laptop has 10 cores and 12 threads.

