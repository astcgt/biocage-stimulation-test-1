import numpy as np,zlib,struct
def save_png(fn,img):
    img=np.asarray(img,dtype=np.uint8)
    if img.ndim==2: img=np.stack([img]*3,-1)
    h,w,_=img.shape
    raw=b''.join(b'\x00'+img[i].tobytes() for i in range(h))
    def chunk(t,d): return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    open(fn,'wb').write(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b''))
