"""gpufe gate 2 with fine increments (dt 0.01): the JSON and log stay here, never in ../biocage-evo/results."""
import os, sys
GPUFE = '/raid/jupyter-alz.ee09/projects/claude-work/biocage-evo/gpufe'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GPUFE); os.chdir(GPUFE); sys.dont_write_bytecode = True
import gate2_fsu
gate2_fsu.OUT = HERE
sys.argv = ['gate2_fsu.py', sys.argv[1], '100']
gate2_fsu.main()
