import numpy as np


def tangents(vertices, normals, uv, triangles):
    i, j, k = np.asarray(triangles).T
    p, q = vertices[j]-vertices[i], vertices[k]-vertices[i]
    a, b = uv[j]-uv[i], uv[k]-uv[i]
    det = a[:,0]*b[:,1]-a[:,1]*b[:,0]
    inv = np.divide(1., det, out=np.zeros_like(det), where=np.abs(det)>1e-10)[:,None]
    tu=(p*b[:,1,None]-q*a[:,1,None])*inv
    tv=(q*a[:,0,None]-p*b[:,0,None])*inv
    t=np.zeros_like(vertices)
    bitangent=np.zeros_like(vertices)
    for index in (i,j,k):
        np.add.at(t,index,tu)
        np.add.at(bitangent,index,tv)
    t -= normals*np.sum(t*normals,axis=1)[:,None]
    length=np.linalg.norm(t,axis=1)
    bad=length<1e-8
    if bad.any():
        n=normals[bad]
        axis=np.eye(3)[np.argmin(abs(n),axis=1)]
        t[bad]=np.cross(n,axis)
    t/=np.maximum(np.linalg.norm(t,axis=1)[:,None],1e-10)
    sign=np.where(np.sum(np.cross(normals,t)*bitangent,axis=1)<0,-1.,1.)
    return np.column_stack((t,sign))
