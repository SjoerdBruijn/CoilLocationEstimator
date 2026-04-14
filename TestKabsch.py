#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  5 11:08:59 2024

@author: sjoerdbruijn
"""
from CoilLocationFcns import rigidbodytransform
import numpy as np

np.random.seed(1235)
n_time=2

P = np.random.randn(3, 10)
P = np.tile(P, (n_time, 1, 1))

alpha = np.random.rand(n_time) * 2 * np.pi
R = np.stack([np.array([[np.cos(a), -np.sin(a), 0],
                        [np.sin(a), np.cos(a), 0],
                        [0, 0, 1]]) for a in alpha], axis=0)
t = np.random.randn(3,1) * 10
t = np.tile(t, (n_time, 1, 1))
Q = np.matmul(R,P)+t


print("values when all markers are used")
# virt_marker= np.full((n_time,3, 1), np.nan)
R_opt, _,t_opt,rmsd = rigidbodytransform(P,Q )

print('RMSD: {}'.format(rmsd.mean()))

l2_t = np.linalg.norm(t.squeeze() - t_opt, axis=1)
l2_R = np.linalg.norm(R - R_opt, axis=(1, 2))
print('l2_t: {}'.format(l2_t.mean()))
print('l2_R: {}'.format(l2_R.mean()))




Q[0,0:3,0]=np.nan
Q[0,0:3,1:7]=np.nan


print("values when one marker is nan at one moment ")
# virt_marker= np.full((n_time,3, 1), np.nan)
R_opt, _,t_opt,rmsd = rigidbodytransform(P[:,:,1:11],Q[:,:,1:11] )

print('RMSD: {}'.format(rmsd.mean()))

l2_t = np.linalg.norm(t.squeeze() - t_opt, axis=1)
l2_R = np.linalg.norm(R - R_opt, axis=(1, 2))
print('l2_t: {}'.format(l2_t.mean()))
print('l2_R: {}'.format(l2_R.mean()))


print("values when one marker is nan at one moment andis used ")
# virt_marker= np.full((n_time,3, 1), np.nan)
R_opt, _,t_opt,rmsd = rigidbodytransform(P,Q )

print('RMSD: {}'.format(rmsd.mean()))

l2_t = np.linalg.norm(t.squeeze() - t_opt, axis=1)
l2_R = np.linalg.norm(R - R_opt, axis=(1, 2))
print('l2_t: {}'.format(l2_t.mean()))
print('l2_R: {}'.format(l2_R.mean()))