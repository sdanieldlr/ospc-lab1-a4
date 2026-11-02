# Lab 1 - Personal Measurements

GitHub user: JasonZhao223
Laptop: HP laptop, Windows 11
CPU: Intel Core Ultra 7 155H
Physical cores: 11
Logical CPUs: 22
Container CPUs: 22
Container memory limit: 2 GiB
Environment: Docker on WSL2, x86_64

## Task 4 - Segmentation

Commands used:
- /usr/bin/time to measure elapsed, user, system and peak memory.
- Compared the generated segments.csv files before and after the change.

| Measurement | Before | After |
|---|---:|---:|
| Elapsed | 8.11 s | 5.98 s |
| User | 8.65 s | 6.64 s |
| System | 0.96 s | 0.83 s |
| Peak memory | 193,152 KB | 165,268 KB |

The revised version was approximately 26% faster and used approximately 14% less peak memory.

## Task 5 - Worker experiment

Three runs for each worker count:

| Workers | Run 1 elapsed | Run 2 elapsed | Run 3 elapsed |
|---|---:|---:|---:|
| 1 | 36.66 s | 35.84 s | 36.53 s |
| 2 | 21.99 s | 22.20 s | 22.45 s |
| 4 | 13.92 s | 14.40 s | 13.66 s |
| 8 | 10.91 s | 11.25 s | 10.84 s |
| 16 | 10.04 s | 10.70 s | 10.38 s |

Average elapsed times:
- 1 worker: 36.34 s
- 2 workers: 22.21 s
- 4 workers: 13.99 s
- 8 workers: 11.00 s
- 16 workers: 10.37 s

## Statistics process cleanup

Commands tested:
- bash steps/stats.sh
- WORKERS=16 bash steps/stats.sh
- timeout --preserve-status -s INT 3s env WORKERS=16 bash steps/stats.sh
- ps -ef | grep -E 'stats_worker|stats.sh' | grep -v grep

The completed statistics runs returned status 0. The interrupt test returned status 130, and no matching worker processes remained afterwards.

## Full pipeline and validation

On 2 November 2026, the complete pipeline ran from 16:21:32 to 16:22:15.

- 8,400,000 orders processed.
- 8,400,000 audit lines written.
- Segmentation completed.
- Statistics completed with four workers.
- The official tools/check.py checker reported PASS for all outputs and all team members.

Tasks 1 to 3 also have measurements recorded in teammate measurement files. Those are team reference measurements and are not represented here as measurements from my own laptop.
EOFwc -l REPORT.md members/JasonZhao223/measurements.md
