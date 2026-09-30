import sys,os,time,numpy as np,torch
sys.path.insert(0,'scripts')
from params import MAT,CONTACT
from fem_core import VoxelContactModel
M=np.load('design/model_A_smooth.npz')
t=time.time()
m=VoxelContactModel(M['L'],float(M['h']),(float(M['x0']),float(M['y0']),float(M['z0'])),M['ref'],MAT,CONTACT)
print('build',time.time()-t)
for d in [0.01,0.02]:
    r=m.solve_increment({2:-d},np.zeros(6),verbose=True)
    m.commit_slip(m.x)
    print(d,r,'reaction',m.reaction().round(2),'q',m.x[-6:].cpu().numpy().round(5))
    vm,s1,s3,_=m.cage_stress();print('max vm',float(vm[m.is_plcl].max()),'slip',m.interface_slip()[:2])
print(torch.cuda.max_memory_allocated()/1e9,'GB')
