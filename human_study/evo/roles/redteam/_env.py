"""python -I drops the user site-packages (scipy etc. live there); add it back. Import this first."""
import site, sys, os
for p in [site.getusersitepackages()]:
    if os.path.isdir(p) and p not in sys.path: sys.path.append(p)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
sys.path.append(os.path.join(ROOT, 'scripts', 'common'))
