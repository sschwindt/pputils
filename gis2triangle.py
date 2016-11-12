#
#+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!
#                                                                       #
#                                 gis2triangle.py                       # 
#                                                                       #
#+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!
#
# Author: Pat Prodanovic, Ph.D., P.Eng.
# 
# Date: June 29, 2015
#
# Purpose: Script takes in a text file of the geometry generated in qgis
# (or any other gis or cad package) and produces geometry files used by
# the triangle mesh generator program (i.e., it writes *.poly geometry 
# file for use in triangle mesh generator. This script parallels my 
# gis2gmsh.py script.
# 
# Revised: Feb 20, 2016
# Made it work for python 2 and 3
# 
# Revised: Nov 12, 2016
# Changed the format of the holes file from holesid,x,y to x,y.
# 
# Uses: Python 2 or 3, Numpy
#
# Example:
#
# python gis2triangle.py -n nodes.csv -b boundary.csv -l lines.csv -o out.poly
#
# where:
#       --> -n is the file listing of all nodes (incl. embedded nodes
#                        if any). The nodes file consist of x,y,z or x,y,z,size;
#                        The size parameter is an optional input, and is used 
#                        by gmsh as an extra parameter that forces element 
#                        size around a particular node. For triangle, it has
#                        no meaning. The nodes file must be comma separated, and
#                        have no header lines. 
#
#       --> -b is the node listing of the outer boundary for the mesh.
#                        The boundary file is generated by snapping lines
#                        to the nodes from the nodes.csv file. The boundary file 
#                        consists of shapeid,x,y of all the lines in the file.
#                        Boundary has to be a closed shape, where first and last 
#                        nodes are identical. Shapeid is a integer, where the
#                        boundary is defined with a distict id (i.e., shapeid 
#                        of 0). 
#
#       --> -l is the node listing of the constraint lines for the mesh.
#                        The lines file can include open or closed polylines.
#                        The file listing has shapeid,x,y, where x,y have to 
#                        reasonable match that of the nodes.csv file. Each distinct
#                        line has to have an individual (integer) shapeid. If no 
#                        constraint lines in the mesh, enter 'none' without the
#                        quotes.
#
#       --> -h is the listing of the holes in the mesh. The holes file is
#                        generated by placing a single node marker inside a
#                        closed line constraint. The holes file must include a 
#                        x,y within the hole. If no holes (islands) in the mesh, enter 
#                        'none' without the quotes. Note that for triangle, the
#                        format of the holes file is different than for gmsh!!!
#
#      --> -o is the output triangle geometry. To generate the mesh, run:
#                        $ ./triangle out.poly 
#                        or use any one of triangle's command line switches.
# 
#      --> -d is an optional flag to ignore removal of duplicate nodes in the 
#                        nodes file. By default, duplicate nodes are removed 
#                        from the nodes.csv file. 
#                         
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Global Imports
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import os,sys                              # system parameters
import numpy             as np             # numpy
from collections import OrderedDict        # for removal of duplicate nodes
from progressbar import ProgressBar, Bar, Percentage, ETA
curdir = os.getcwd()
#
#
# I/O
if len(sys.argv) == 11 :
	dummy1 =  sys.argv[1]
	nodes_file = sys.argv[2]
	dummy2 =  sys.argv[3]
	boundary_file = sys.argv[4]
	dummy3 =  sys.argv[5]
	lines_file = sys.argv[6]
	dummy4 =  sys.argv[7]
	holes_file = sys.argv[8]
	dummy5 =  sys.argv[9]
	output_file = sys.argv[10]
	dummy6 = ' '
	duplicates_flag = 1 # removal of duplicate nodes is on by default
elif (len(sys.argv) == 13):
	dummy1 =  sys.argv[1]
	nodes_file = sys.argv[2]
	dummy2 =  sys.argv[3]
	boundary_file = sys.argv[4]
	dummy3 =  sys.argv[5]
	lines_file = sys.argv[6]
	dummy4 =  sys.argv[7]
	holes_file = sys.argv[8]
	dummy5 =  sys.argv[9]
	output_file = sys.argv[10]
	dummy6 = sys.argv[11]
	duplicates_flag = sys.argv[12]
else:
	print('Wrong number of Arguments, stopping now...')
	print('Usage:')
	print('python gis2triangle.py -n nodes.csv -b boundary.csv -l lines.csv -h holes.csv -o out.poly')
	#print 'or, if wanting to turn off duplicate removal algorithm'
	#print 'python gis2triangle.py -n nodes.csv -b boundary.csv -l lines.csv -h holes.csv -o out.poly -d 0'
	sys.exit()

# find out if the nodes file is x,y,z or x,y,x,size
with open(nodes_file, 'r') as f:
    line = next(f) # read 1 line
    n_attr = len(line.split(','))

# to create the output file
fout = open(output_file,"w")

# use numpy to read the file
# each column in the file is a row in data read by no.loadtxt method
nodes_data = np.loadtxt(nodes_file, delimiter=',',skiprows=0,unpack=True)
boundary_data = np.loadtxt(boundary_file, delimiter=',',skiprows=0,unpack=True)
if (lines_file != 'none'):
	lines_data = np.loadtxt(lines_file, delimiter=',',skiprows=0,unpack=True)
if (holes_file != 'none'):
	holes_data = np.loadtxt(holes_file, delimiter=',',skiprows=0,unpack=True)

# master nodes in the file (from the nodes file)
# note, nodes can't have duplicates!!!
x = nodes_data[0,:]
y = nodes_data[1,:]
z = nodes_data[2,:]
if (n_attr == 4):
	size = nodes_data[3,:]
else:
	size = np.zeros(len(x))
		
# n is the number of nodes
n = len(x)
# creates node numbers from the nodes file
node = np.zeros(n,dtype=np.int32)

# to check for duplicate nodes
# crop all the points to three decimals only
x = np.around(x,decimals=3)
y = np.around(y,decimals=3)
z = np.around(z,decimals=3)
size = np.around(size,decimals=3)

# this piece of code uses OrderedDict to remove duplicate nodes
# source "http://stackoverflow.com/questions/12698987"
# ###################################################################
tmp = OrderedDict()
for point in zip(x, y, z, size):
  tmp.setdefault(point[:2], point)

# in python 3 tmp.values() is a view object that needs to be 
# converted to a list
mypoints = list(tmp.values()) 
# ###################################################################
n_rev = len(mypoints)

# replace x,y,z,size and n with their unique equivalents
if (duplicates_flag == 1):
	for i in range(n_rev):
		x[i] = mypoints[i][0]
		y[i] = mypoints[i][1]
		z[i] = mypoints[i][2]
		size[i] = mypoints[i][3]
	n = n_rev

# if node is part of boundary or lines, then it is not embedded
is_node_emb = np.zeros(n,dtype=np.int32)
for i in range(0,n):
	node[i] = i+1
	is_node_emb[i] = 1

# boundary data
shapeid_bnd = boundary_data[0,:]
x_bnd = boundary_data[1,:]
y_bnd = boundary_data[2,:]
# number of nodes in the boundary file
n_bnd = len(x_bnd)

# round boundary nodes to three decimals
x_bnd = np.around(x_bnd,decimals=3)
y_bnd = np.around(y_bnd,decimals=3)

# count lines from boundary lines
count_bnd = 0

# lines data
if (lines_file != 'none'):
	shapeid_lns = lines_data[0,:]
	x_lns = lines_data[1,:]
	y_lns = lines_data[2,:]
	# number of nodes in the lines file
	n_lns = len(x_lns)

count_lns = 0

# writes *.poly geometry file for use in triangle mesh generator
# writes the *.poly header data for nodes
fout.write(str(n) + " " + str("2 1 0") + "\n") 


# writes the nodes in triangle format 
for i in range(0,n):
	fout.write(str(i+1) + " " + str("{:.3f}".format(x[i])) +
		str(" ") + str("{:.3f}".format(y[i])) + str(" ") + 
		str("{:.3f}".format(z[i])) + "\n")

############################################################################
# BOUNDARY LINES
# index of the minimum, for each boundary node
minidx = np.zeros(n_bnd,dtype=np.int32)
# distance between each boundary node and node in the master nodes file

# write the boundary in gmsh format
for i in range(0,n_bnd-1):
	if (i == 0) :
		#fout.write("Line(" + str(i+1) + str(") = {") + str(node[minidx[0]])
		#	+ str(", ") + str(node[minidx[1]]) + str("};") + "\n")
		count_bnd =count_bnd +1
	else:
		#fout.write("Line(" + str(i+1) + str(") = {") + str(node[minidx[i]])
		#	+ str(", ") + str(node[minidx[i+1]]) + str("};") + "\n")
		count_bnd =count_bnd +1

# the lines numbering continues from the boundary numbering
count_lns = count_bnd + 1

# CONSTRAINT LINES
if (lines_file != 'none'):
	# index for the minimum, for each lines node
	minidx_lns = np.zeros(n_lns,dtype=np.int32)
	# distance between each lines node and node in the master nodes file
	dist_lns = np.zeros(n)
		
	cur_lns_shapeid = shapeid_lns[0]
	prev_lns_shapeid = shapeid_lns[0]	
	
	# write the constraint lines
	for i in range(0,n_lns-1):
		if (i>0):
			cur_lns_shapeid = shapeid_lns[i]
			prev_lns_shapeid = shapeid_lns[i-1]
			if (cur_lns_shapeid - prev_lns_shapeid < 0.001):
				#fout.write(str(cur_lns_shapeid) + " " + str(prev_lns_shapeid) + " ")
				#fout.write("Line(" + str(count_lns) + str(") = {") + 
				#	str(node[minidx_lns[i-1]]) + str(", ") + str(node[minidx_lns[i]]) + str("};") + "\n")
				count_lns = count_lns + 1
############################################################################

# this is really inefficient, but all of the loops above (between ####) are
# simply to count the number of lines in the file (boundary nodes and 
# constraint lines together.

# this is a cheating way to do this, but it will have to do for now.
# discovered through debug testing
if (lines_file == 'none'):
	fout.write(str(count_lns-1) + " 0" + "\n")
else:
	fout.write(str(count_lns) + " 0" + "\n")

# now repeat the loops between the #### are write the lines (boundary and 
# constraint)
count_bnd = 0
count_lns = 0
############################################################################
# BOUNDARY LINES
# index of the minimum, for each boundary node
minidx = np.zeros(n_bnd,dtype=np.int32)
# distance between each boundary node and node in the master nodes file
xdist = np.add(np.zeros(n),999.0)
ydist = np.add(np.zeros(n),999.0)
dist = np.add(np.zeros(n),999.0)
for i in range(0,n_bnd):
	xdist = np.subtract(x,x_bnd[i])
	ydist = np.subtract(y,y_bnd[i])
	dist = np.sqrt(np.power(xdist,2.0) + np.power(ydist,2.0))
	#for j in range(0,n):
	#	dist[j] = np.sqrt(abs(x_bnd[i] - x[j])**2 + abs (y_bnd[i] - y[j])**2 )
	
	# find the minimum of the dist array
	minidx[i] = np.argmin(dist)
	#fout.write(str(i) + " " + str(minidx[i]) + "\n")
	
	# fill in the is_node_emb array 
	is_node_emb[minidx[i]] = 0

# write the boundary in triangle format
for i in range(0,n_bnd-1):
	if (i == 0) :
		fout.write(str(i+1) + str(" ") + str(node[minidx[0]])
			+ str(" ") + str(node[minidx[1]]) + "\n")
		count_bnd =count_bnd +1
	else:
		fout.write(str(i+1) + str(" ") + str(node[minidx[i]])
			+ str(" ") + str(node[minidx[i+1]]) + "\n")
		count_bnd =count_bnd +1

# the lines numbering continues from the boundary numbering
count_lns = count_bnd + 1

# CONSTRAINT LINES
if (lines_file != 'none'):
	w = [Percentage(), Bar(), ETA()]
	pbar = ProgressBar(widgets=w, maxval=n_lns).start()
	# index for the minimum, for each lines node
	minidx_lns = np.zeros(n_lns,dtype=np.int32)
	# distance between each lines node and node in the master nodes file
	xdist_lns = np.add(np.zeros(n),999.0)
	ydist_lns = np.add(np.zeros(n),999.0)
	dist_lns = np.add(np.zeros(n),999.0)
	for i in range(0,n_lns):
		xdist_lns = np.subtract(x,x_lns[i])
		ydist_lns = np.subtract(y,y_lns[i])
		dist_lns = np.sqrt(np.power(xdist_lns,2.0) + np.power(ydist_lns,2.0))
		
		#for j in range(0,n):
		#	dist_lns[j] = np.sqrt(abs(x_lns[i] - x[j])**2 + abs (y_lns[i] - y[j])**2 )
		# find the minimum of the dist array
		minidx_lns[i] = np.argmin(dist_lns)
		#fout.write(str(i) + " " + str(minidx_lns[i]) + "\n")
		
		# fill in the is_node_emb array 
		is_node_emb[minidx_lns[i]] = 0
		
		# update the pbar
		pbar.update(i+1)
		
	cur_lns_shapeid = shapeid_lns[0]
	prev_lns_shapeid = shapeid_lns[0]	
	pbar.finish()
	
	# write the constraint lines
	for i in range(0,n_lns):
		if (i>0):
			cur_lns_shapeid = shapeid_lns[i]
			prev_lns_shapeid = shapeid_lns[i-1]
			if (cur_lns_shapeid - prev_lns_shapeid < 0.001):
				#fout.write(str(cur_lns_shapeid) + " " + str(prev_lns_shapeid) + " ")
				fout.write(str(count_lns) + str(" ") + 
					str(node[minidx_lns[i-1]]) + str(" ") + str(node[minidx_lns[i]])+"\n")
				count_lns = count_lns + 1
############################################################################

# lastly, write the holes
# holes data
if (holes_file != 'none'):
	# find out how many holes
	n_hls = len(open(holes_file).readlines())
	
	# counters for hole points
	shapeid_hls1 = -1
	shapeid_hls = -1
			
	if (n_hls == 1):
		master = list()
		with open(holes_file, 'r') as f:
			for line in f:
				master.append(line)
		tmp = master[0].split(',')
		shapeid_hls1 = shapeid_hls1 + 1
		x_hls1 = float(tmp[0])
		y_hls1 = float(tmp[1])
		fout.write(str(n_hls) + '\n')
		fout.write(str(shapeid_hls1) + ' ' + str(x_hls1) + ' ' + str(y_hls1) + '\n')
	else:

		#shapeid_hls = holes_data[0,:]
		#shapeid_hls =shapeid_hls.astype(np.int32)
		x_hls = holes_data[0,:]
		y_hls = holes_data[1,:]
	
		# round lines nodes to three decimals
		x_hls = np.around(x_hls,decimals=3)
		y_hls = np.around(y_hls,decimals=3)
	
		#n_hls = len(x_hls)
		fout.write(str(n_hls) + '\n')
		for i in range(n_hls):
			shapeid_hls = shapeid_hls + 1
			fout.write(str(shapeid_hls) + ' ' + str(x_hls[i]) + ' ' + str(y_hls[i]) + '\n')
else:
	fout.write(str(0))
