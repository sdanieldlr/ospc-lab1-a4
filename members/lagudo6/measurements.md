# Lab 1 - Measurements

GitHub user: lagudo6  
Laptop: MacBook Pro 14-inch 2023, macOS Sonoma 14.3  
CPU: Apple Silicon  
Container CPUs: 14  
Container memory limit: 2 GiB

## Section 6.4 - Worker Experiment

Sweep results are saved in `members/lagudo6/sweep.csv`.

Average elapsed time by worker count:

| Workers | Avg elapsed |
|---:|---:|
| 1 | 29.57 s |
| 2 | 15.58 s |
| 4 | 8.28 s |
| 8 | 4.80 s |
| 16 | 4.04 s |

Conclusion: 16 workers was the fastest setting on my laptop.
