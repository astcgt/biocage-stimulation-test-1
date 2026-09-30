# GPU parallelisation benchmark (2026-09-30)
Strategy: independent-job parallelism (one FEM case per GPU worker, no domain decomposition).
Parent launched with CUDA_VISIBLE_DEVICES=3,4,7; worker i -> torch.cuda.set_device(i) (cuda:i). GPUs 0,1,2,5,6 belong to another user and were not used.
Workload: 6 linear compression solves (2 designs x 3 displacements), ~2.4 M DOF each, PCG tol 1e-8.

| | 1 GPU (phys 3) | 3 GPUs (phys 3,4,7) |
|---|---|---|
| wall-clock | 106.7 s | 38.9 s |
| speedup | 1.00 | 2.74 |
| SM util (nvidia-smi pmon) | 97 % | 97-98 % each |
| VRAM per process | 2.83 GB (torch peak 1.62 GB) | 2.83 GB each |
| results | reference | bit-identical Fz, max von Mises, PCG iterations |
