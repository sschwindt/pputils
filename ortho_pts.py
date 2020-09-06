#!/usr/bin/env python3
#
#+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!
#                                                                       #
#                           ortho_pts.py                                # 
#                                                                       #
#+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!
#
# Author: Pat Prodanovic, Ph.D., P.Eng.
# 
# Date: April 19, 2020
#
# Purpose: The script takes a polygon (with upstream and downstream as
# straight lines), an edge node file, the number of n x m grid points.
# It uses a pre-compiled version of Pavel Sakov's gridgen-c to create
# an orthogonal set of points (n x m in size) for the domain inside a
# polygon.
#
# Uses: Python 2 or 3, Numpy
#
# Example:
#
# python ortho_pts.py -p poly.csv -e edge_nodes.csv -n 10 -m 50 -o out.csv
#
# where:
# -p --> closed polygon (PPUTILS polygon file) of the river channel, 
#        where the upstream and the downstream sections are straight lines
# -e --> edge nodes (as PPUTILS points file) at upstream and downstream
#        sections; must be x,y or x,y,z file
# -n --> number of points along n direction
# -m --> number of points along m direction
# -o --> output nodes file (PPUTILS csv points file)
#
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Global Imports
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import os,sys,shutil                       # system parameters
import numpy             as np             # numpy
from scipy import spatial                  # kd tree for searching coords
import struct                              # to determine sys architecture
import subprocess                          # to execute binaries
#
# deals with the paths
try:
  # this only works when the paths are sourced!
  pputils_path = os.environ['PPUTILS']
except:
  pputils_path = os.getcwd()

#
if len(sys.argv) == 11 :
  poly_file = sys.argv[2]
  edges_file = sys.argv[4]
  n = int(sys.argv[6])
  m = int(sys.argv[8])
  output_file = sys.argv[10]
else:
  print('Wrong number of Arguments, stopping now...')
  print('Usage:')
  print('python gen_ortho_pts.py -p poly.csv -e edge_nodes.csv -n 10 -m 50 -o out.csv')
  sys.exit()

# to determine if the system is 32 or 64 bit
archtype = struct.calcsize("P") * 8

# to read the input data using numpy
poly_data = np.loadtxt(poly_file, delimiter=',',skiprows=0,unpack=True)
edges_data = np.loadtxt(edges_file, delimiter=',',skiprows=0,unpack=True)

# note that I have a duplicate points at start and end of a closed polygon!!!
# this has an impact on how the kd tree searches for the points.

# poly coords
x = poly_data[1,:]
y = poly_data[2,:]
z = poly_data[3,:]

# edges coords
x_e = edges_data[0,:]
y_e = edges_data[1,:]
if (len(edges_data) < 3):
  z_e = np.zeros(len(x_e))
else:
  z_e = edges_data[2,:]

# index where the edge node is within the poly
poly_idx = np.zeros(len(x))

# construct kd tree using the poly coords
points = np.column_stack((x,y))
tree = spatial.cKDTree(points)

# now we must go though each edge point, and find the corresponding poly cords
for i in range(len(x_e)):
  d,idx = tree.query( (x_e[i],y_e[i]), k = 1)
  poly_idx[idx] = 1

# construct the poly.xy file for gridgen-c
# open a temp file
tmp = open('poly.xy', 'w')

for i in range(len(x)):
  if (poly_idx[i] == 1):
    tmp.write(str(x[i]) + ' ' + str(y[i]) + ' ' + str(1) + '\n')
  else:
    tmp.write(str(x[i]) + ' ' + str(y[i]) + '\n')

tmp.close()

# now we construct a gridgen-c parameter file
tmp2 = open('gridgen.prm', 'w')

tmp2.write('input poly.xy' + '\n')
tmp2.write('output poly.0' + '\n')
tmp2.write('nx ' + str(n) + '\n')
tmp2.write('ny ' + str(m) + '\n')
tmp2.write('nnodes 10' + '\n')
tmp2.write('precision 1.0e-12' + '\n')
tmp2.write('newton 1' + '\n')
tmp2.write('rectangle poly_rect.0' + '\n')
tmp2.write('sigmas poly_sigmas.0' + '\n')

# this must be done before the subprocess is called
tmp2.close()

# now run gridgen (to generate points)

if (os.name == 'posix'):
  # determines processor type
  proctype = os.uname()[4][:]
  
  if (proctype == 'i686'):
    print('Support for 32 bit Linux is not provided! Upgrade system!')
    sys.exit(0)
  elif (proctype == 'x86_64'):
    callstr = pputils_path + '/gridgen/bin/gridgen'
  elif (proctype == 'armv7l'):
    print('Support for 32 bit Raspberry Pi is not provided! Sorry!')
    sys.exit(0)

  # make sure the binary is allowed to be executed
  subprocess.call(['chmod', '+x', callstr])

  # call gridgen
  subprocess.call( [callstr, 'gridgen.prm', '-vv'] )
    
elif (os.name == 'nt'):
    print('Gridgen-c is not compiled for Windows yet. Sorry!')
else:
  print('OS not supported!')
  print('Exiting!')
  sys.exit()

# the last step is to format pts.0 file generated by gridgen-c to a 
# PPUTILS points format

# use numpy to read the file (I might have to change this if I choose to
# deal with multi block gridgen output!)
pts_data = np.loadtxt('poly.0', delimiter=' ',skiprows=1,unpack=True)

pts_x = pts_data[0,:]
pts_y = pts_data[1,:]
pts_z = np.zeros(len(pts_x))

# now we write the final output
fout = open(output_file, 'w')

for i in range(len(pts_x)):
  fout.write(str(pts_x[i]) + ',' + str(pts_y[i]) + ',' + str(pts_z[i]) + '\n')

fout.close()

# convert the output to a WKT file as well
wkt_file = output_file.rsplit('.',1)[0] + 'WKT.csv'

wkt = open(wkt_file, 'w')

wkt.write('WKT,node' + '\n')

for i in range(len(pts_x)):
  wkt.write('"POINT (')
  wkt.write(str('{:.3f}'.format(pts_x[i] )) + ' ' + 
    str('{:.3f}'.format(pts_y[i] )) + ' ' + 
    str('{:.3f}'.format(pts_z[i] )) + ')",' + 
    str(i+1) + '\n')

# remove the temp files
os.remove('gridgen.prm')
os.remove('poly_sigmas.0')
os.remove('poly_rect.0')
os.remove('poly.xy')
os.remove('poly.0')

print('All done!')



  
