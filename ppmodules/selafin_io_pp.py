#
#+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!
#                                                                       #
#                                 selafin_io_pp.py                      # 
#                                                                       #
#+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!
#
# Author: Pat Prodanovic, Ph.D., P.Eng.
# 
# Date: Feb 13, 2015
#
# Purpose: Class that reads and writes TELEMAC's SELAFIN files. Based on
# HRW's class under the same name. Made it so that it works under Python 2
# and Python 3. TODO: test double precision.
#
# Uses: Python, Numpy
#
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Global Imports
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
from struct import unpack,pack
import sys
import numpy as np
#
class ppSELAFIN:

	# object's properties
	def __init__(self, slf_file):
		
		# determine which version of python the user is running
		if (sys.version_info > (3, 0)):
			self.version = 3
		elif (sys.version_info > (2, 7)):
			self.version = 2
		
		self.slf_file = slf_file

		self.endian = '>' # always assume big endian
		
		# For C float type use size 4
		# For C double type use size 8
		# defaults are single precision selafin
		# for double precision, use setPrecision, and change it to 'd', 8
		self.float_type = 'f' 
		self.float_size = 4
		
		self.title = ''
		self.precision = ''
		self.NBV1 = 0
		self.NBV2 = 0
		
		# variables and units
		self.vars = []
		
		self.vnames = []
		self.vunits = []
		
		self.IPARAM = []
		
		# Aug 29, 1997 2:15 am EST (date when skynet became self-aware)
		self.DATE = [1997, 8, 29, 2, 15, 0] 
		
		self.NELEM = 0
		self.NPOIN = 0
		self.NDP = 0
		
		self.IKLE = np.zeros((self.NELEM,self.NPOIN), dtype=np.int32)
		
		self.IPOBO = np.zeros(self.NPOIN, dtype=np.int32)
		
		self.x = np.zeros(self.NPOIN)
		self.y = np.zeros(self.NPOIN)
		
		self.time = []
		
		# temporary array that hold results read for a single time step
		# for each variable in the file
		self.temp = np.zeros((self.NBV1,self.NPOIN))
		
	# methods start here
	def setPrecision(self,ftype, fsize):
		self.float_type = ftype
		self.float_size = fsize
		
	def readHeader(self):
		self.f = open(self.slf_file, 'rb')
		garbage = unpack('>i', self.f.read(4))[0]
		
		if (self.version == 2):
			self.title = unpack('>72s', self.f.read(72))[0]
			self.precision = unpack('>8s', self.f.read(8))[0]
		else:
			self.title = unpack('>72s', self.f.read(72))[0].decode()
			self.precision = unpack('>8s', self.f.read(8))[0].decode()
		garbage = unpack('>i', self.f.read(4))[0]
		
		garbage = unpack('>i', self.f.read(4))[0]
		self.NBV1 = unpack('>i', self.f.read(4))[0] # variables
		self.NBV2 = unpack('>i', self.f.read(4))[0] # quad variables, not used
		garbage = unpack('>i', self.f.read(4))[0]
		
		# each item in the vars list has 32 characters; 16 for name, and 16 for unit
		for i in range(self.NBV1):
			garbage = unpack('>i', self.f.read(4))[0]
			if (self.version ==2):
				self.vars.append(unpack('>32s', self.f.read(32))[0])
			else:
				self.vars.append(unpack('>32s', self.f.read(32))[0].decode())
			garbage = unpack('>i', self.f.read(4))[0]	
			
		for i in range(self.NBV1):
			self.vnames.append(self.vars[i][0:15])
			self.vunits.append(self.vars[i][16:31])
			
		garbage = unpack('>i', self.f.read(4))[0]
		self.IPARAM = unpack('>10i', self.f.read(10*4))
		garbage = unpack('>i', self.f.read(4))[0]
		
		if (self.IPARAM[-1] == 1):
			garbage = unpack('>i', self.f.read(4))[0]
			# date is 6 integers stored as a list
			self.DATE = unpack('>6i', self.f.read(6*4))
			garbage = unpack('>i', self.f.read(4))[0]
		
		# uses python's long instead of integer 
		garbage = unpack('>i', self.f.read(4))[0]
		self.NELEM = unpack('>l', self.f.read(4))[0]
		self.NPOIN = unpack('>l', self.f.read(4))[0]
		self.NDP = unpack('>i', self.f.read(4))[0]
		dummy = unpack('>i', self.f.read(4))[0]
		garbage = unpack('>i', self.f.read(4))[0]
		
		self.IKLE = np.zeros((self.NELEM, self.NDP), dtype=np.int32)
		
		garbage = unpack('>i', self.f.read(4))[0]
		for i in range(self.NELEM):
			self.IKLE[i,0] = unpack('>l', self.f.read(4))[0]
			self.IKLE[i,1] = unpack('>l', self.f.read(4))[0]
			self.IKLE[i,2] = unpack('>l', self.f.read(4))[0]
		garbage = unpack('>i', self.f.read(4))[0]		
		
		self.IPOBO = np.zeros(self.NPOIN, dtype=np.int32)
		
		garbage = unpack('>i', self.f.read(4))[0]
		for i in range(self.NPOIN):
			self.IPOBO[i] = unpack('>l', self.f.read(4))[0]
		garbage = unpack('>i', self.f.read(4))[0]
			
		# reads x
		self.x = np.zeros(self.NPOIN)
		garbage = unpack('>i', self.f.read(4))[0]
		for i in range(self.NPOIN):
			self.x[i] = unpack('>' + self.float_type, self.f.read(self.float_size))[0]
		garbage = unpack('>i', self.f.read(4))[0]
		
		# reads y 
		self.y = np.zeros(self.NPOIN)
		garbage = unpack('>i', self.f.read(4))[0]
		for i in range(self.NPOIN):
			self.y[i] = unpack('>' + self.float_type, self.f.read(self.float_size))[0]
		garbage = unpack('>i', self.f.read(4))[0]
		
	def readTimes(self):
		pos_prior_to_time_reading = self.f.tell()
		
		while True:
			try:
				# get the times
				self.f.seek(4,1)
				self.time.append( unpack('>'+self.float_type, self.f.read(self.float_size))[0] )
				self.f.seek(4,1)
				
				# skip through the variables
				self.f.seek(self.NBV1*(4+self.float_size*self.NPOIN+4), 1)
				
				# skip the variables
				# 4 at begining and end are garbage
				# 4*NPOIN assumes each times step there are NPOIN nodes of 
				# size 4 bytes (i.e., single precision)
				# f.seek(NBV1*(4+4*NPOIN+4), 1)
			except:
				break
		self.f.seek(pos_prior_to_time_reading)
		
	def readVariables(self,t_des):
		# reads data for all variables in the *.slf file at desired time t_des
		self.temp = np.zeros((self.NBV1,self.NPOIN))
		
		# it reads the time again, but this it is not used
		time2 = []
		
		# time index
		t = -1
		
		while True:
			try:
				self.f.seek(4,1)
				time2.append( unpack('>'+self.float_type, self.f.read(self.float_size))[0] )
				self.f.seek(4,1)
				
				t = t + 1
				
				if ((t_des - t) < 0.1):
					for i in range(self.NBV1):
						self.f.seek(4,1)
						for j in range(self.NPOIN):
							self.temp[i,j] = unpack('>'+self.float_type, self.f.read(self.float_size))[0]
						self.f.seek(4,1)
				else:
					self.f.seek(self.NBV1*(4+self.float_size*self.NPOIN+4), 1)
			except:
				break
				
	# get methods start here			
	def getTimes(self):
		return self.time
		
	def getVariables(self):
		return self.vnames
		
	def getUnits(self):
		return self.vunits		

