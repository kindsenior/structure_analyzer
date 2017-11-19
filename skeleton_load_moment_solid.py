#!/usr/bin/python
# -*- coding: utf-8 -*-

from mpl_toolkits.mplot3d import Axes3D
import numpy as np
# from matplotlib import cm
import matplotlib.pyplot as plt
from scipy.spatial import Delaunay
from matplotlib.ticker import LinearLocator, FormatStrFormatter
import itertools as it

# import numpy
# from mpl_toolkits.mplot3d import Axes3D
# import matplotlib.pyplot as plt
from matplotlib import tri, cm

from scipy.spatial import ConvexHull
import scipy.linalg as linalg

import cdd

import pprint
import time

def plot_convex_hull(vertices):
    ax.clear()
    ax.set_xlim3d(-max_display_num,max_display_num)
    ax.set_ylim3d(-max_display_num,max_display_num)
    ax.set_zlim3d(-max_display_num,max_display_num)
    ax.set_xlabel("nx(roll) [Nm]")
    ax.set_ylabel("ny(pitch) [Nm]")
    ax.set_zlabel("nz(yaw) [Nm]")

    # hull = ConvexHull(vertices, incremental=True)
    hull = ConvexHull(vertices, incremental=True, qhull_options="QJ")

    for  idx, face_indices in enumerate(hull.simplices): # faces -> hull.simplices
        # print idx, " face: ", face_indices
        x,y,z = vertices[face_indices,0], vertices[face_indices,1], vertices[face_indices,2]

        # print "x: ", x
        # print "y: ", y
        # print "z: ", z
        # print ""

        x = x + z*0.0001
        y = y + z*0.0001

        # S = ax.plot_trisurf(x,y,z, cmap=cm.jet)

        triang = tri.Triangulation(x, y)
        refiner = tri.UniformTriRefiner(triang)
        new, new_z = refiner.refine_field(z, subdiv=2)

        # norm = plt.Normalize(vmax=abs(y).max(), vmin=-abs(y).max())
        norm = plt.Normalize(vmax=1500, vmin=-1500)
        kwargs = dict(triangles=new.triangles, cmap=cm.jet, norm=norm, linewidth=0.2)

        surf = ax.plot_trisurf(new.x, new.y, new_z, **kwargs)

    # plt.show()
    plt.pause(0.1)

def swipe_joint_range(division_num = None, dowait = None, tm = None):
    if division_num is None:
        division_num = 5

    if dowait is None:
        dowait = True

    if tm is None:
        tm = 0.5

    max_moment_vec = float("-inf")*np.ones(moment_dim)
    min_moment_vec = float("inf")*np.ones(moment_dim)
    swipe_joint_range_impl(joint_order, rot_list,  max_moment_vec, min_moment_vec, division_num = division_num, dowait = dowait ,tm = tm)


def swipe_joint_range_impl(child_joint_indices, rot_list, max_moment_vec, min_moment_vec, division_num = None, dowait = None, tm = None):
# def swipe_joint_range(child_joint_structure, rot_list, local_axis_list):
    # child_joint_indices = [idx for l in child_joint_structure for idx in l]
    print "swipe_joint_range()"
    # print "child_joint_indices="
    # print child_joint_indices
    print ""

    turn = A_theta.shape[0] - len(child_joint_indices)
    if len(child_joint_indices) > 1:
        child_joint_idx = child_joint_indices[1] # x/y/z = 0/1/2
        child_joint_range = joint_range_list[child_joint_idx]
        child_joint_axis = np.identity(3)[:,child_joint_idx]
        for child_joint_angle in np.linspace(child_joint_range[0], child_joint_range[1], division_num):
            print joint_name_list[child_joint_idx], " is ", child_joint_angle, " [deg]"
            rot_list[turn] = linalg.expm3( np.cross(np.identity(moment_dim), child_joint_axis*np.deg2rad(child_joint_angle) ) )
            max_moment_vec, min_moment_vec = swipe_joint_range_impl(child_joint_indices[1:], rot_list, max_moment_vec ,min_moment_vec, dowait = dowait, division_num = division_num, tm = tm)

        return max_moment_vec, min_moment_vec
    else:
        rot_list[-1] = np.identity(3) # turn = 3-1
        for i in range(A_theta.shape[0]):
            group_last_axis = [ joint_group for joint_group in joint_structure for joint_axis in joint_group if joint_axis == joint_order[i] ][0][-1]
            A_theta[i] = reduce(lambda x,y: np.dot(x,y), rot_list[joint_order.index(group_last_axis):]).dot(local_axis_list[i]).T[0]
            # A_theta[i] = reduce(lambda x,y: np.dot(x,y), rot_list[i:]).dot(local_axis_list[i]).T[0]
        B_theta = np.identity(moment_dim) - A_theta.dot(A_theta.T).dot(S)

        print "rot_list="
        pprint.pprint(rot_list)
        print "A_theta="
        print A_theta
        print "B_theta="
        print B_theta
        print ""

        # convert to tau_tilde V->H
        tau_tilde_vertices = tau_vertices.dot(B_theta.T) # u_k^~T
        b_tilde = np.ones(tau_vertices.shape[0])[:,np.newaxis] # only hull (no cone)
        mat = cdd.Matrix(np.hstack([b_tilde, tau_tilde_vertices]), number_type='float')
        mat.rep_type = cdd.RepType.GENERATOR
        poly = cdd.Polyhedron(mat)
        ext = poly.get_inequalities()
        print "tau_tilde"
        print ext
        C = -np.array(ext)[:,1:]
        d = np.array(ext)[:,0:1]
        print ""

        # H->V
        # for max value
        max_value = 2000
        A = np.vstack([C.dot(A_theta), np.identity(moment_dim), -np.identity(moment_dim)])
        b = np.vstack([d, max_value*np.ones(moment_dim)[:,np.newaxis], max_value*np.ones(moment_dim)[:,np.newaxis]])
        mat = cdd.Matrix(np.hstack([b,-A]), number_type='float')
        mat.rep_type = cdd.RepType.INEQUALITY
        poly = cdd.Polyhedron(mat)
        ext = poly.get_generators()
        print "final"
        print ext

        n_vertices = np.array(ext)[:,1:] # only hull (no cone)
        max_moment_vec = np.vstack([n_vertices, max_moment_vec]).max(axis=0)
        min_moment_vec = np.vstack([n_vertices, min_moment_vec]).min(axis=0)
        print "max: ", max_moment_vec
        print "min: ", min_moment_vec
        plot_convex_hull(n_vertices)

        if dowait:
            print "wait"
            raw_input()
        else:
            time.sleep(tm)

        return max_moment_vec, min_moment_vec

joint_name_list = ("hip-x", "hip-y", "hip-z")
# roll=x=0, pitch=y=1, yaw=z=2
joint_structure = [[2],[0],[1],[]] # z-x-y HD
# joint_structure = [[2],[0],[1]] # z-x-y wired
# joint_structure = [[2],[0,1]] # z-{x-y}
joint_order = [idx for l in joint_structure for idx in l]
num_joints = len(joint_order)
moment_dim = num_joints
joint_range_list = [(-30,60),(-120,55),(-90,90)] # roll, pitch, yaw
# joint_range_list = [(0,0),(0,0),(-90,90)] # roll, pitch, yaw
# joint_range_list = [(-30,30),(0,0),(0,0)] # roll, pitch, yaw
# joint_range_list = [(-90,90),(0,0),(0,0)] # roll, pitch, yaw
# joint_range_list = [(0,0),(45,45),(0,0)] # roll, pitch=45, yaw
# joint_range_list = [(45,45),(45,45),(0,0)] # roll, pitch=45, yaw
# joint_range_list = [(-30,30),(-45,45),(0,0)] # roll, pitch, yaw
# max_tau_list = [300,750,200] # roll, pitch, yaw
# max_tau_list = [350,700,120] # roll, pitch, yaw
max_tau_list = [330,700,120] # roll, pitch, yaw
assert len(joint_range_list) == num_joints
rot_list = [None for x in range(num_joints)]
# local_axis_list = [None for x in range(num_joints)]
local_axis_list = [np.identity(moment_dim)[:,idx:idx+1]for idx in joint_order]

A_theta = np.zeros([num_joints,moment_dim])
S = 0.99 * np.diag([1 if x in joint_structure[-1] else 0 for x in joint_order])

fig = plt.figure(figsize=(20.0,20.0))
# ax = fig.add_subplot(111, projection='3d')
ax = fig.gca(projection='3d')

# tau convex hull H->V
max_tau = np.array([max_tau_list[joint_idx] for joint_idx in joint_order])[:,np.newaxis] # from root order
assert len(max_tau) == num_joints
A = np.vstack([np.identity(num_joints),-np.identity(num_joints)])
b = np.vstack([max_tau,max_tau]) # min_tau = - max_tau -> -min_tau = max_tau
mat = cdd.Matrix(np.hstack([b,-A]), number_type='float')
mat.rep_type = cdd.RepType.INEQUALITY
poly = cdd.Polyhedron(mat)
print poly
ext = poly.get_generators()
print ext
tau_vertices = np.array(ext)[:,1:] # u_k^T

# ax.set_xlabel("Joint0[Nm]")
# ax.set_ylabel("Joint1[Nm]")
# ax.set_zlabel("Joint2[Nm]")
# plot_convex_hull(tau_vertices)


max_display_num = 1500
ax.set_xlim3d(-max_display_num,max_display_num)
ax.set_ylim3d(-max_display_num,max_display_num)
ax.set_zlim3d(-max_display_num,max_display_num)
# ax.set_aspect('equal')

# swipe_joint_range(joint_order, rot_list, division_num = 0)
swipe_joint_range(division_num = 0)