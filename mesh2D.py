from collections import namedtuple
from mathparser import mathExpression
import numpy as np
Constraint = namedtuple('Constraint', ['expr', 'Limits'])
Axis = namedtuple('Axis', ['Label', 'Limits', 'Points'])

class mesh2D(object):
	def __init__(self, meshdict, func):
		x = meshdict['x']
		y = meshdict['y']
		self.x = Axis(x['label'], tuple(x['range']), x['points'] )
		self.y = Axis(y['label'], tuple(y['range']), y['points'] )
		self.constraints = []
		self.func = func
		self.params = meshdict['parameters']
		# self.mesh = self.generate_mesh()

		for keys in meshdict['Independent Variables']:
			lims = sorted(meshdict['Independent Variables'][keys]['limits'])
			constraint = {'expr':keys, 'min':lims[0], 'max':lims[1]}
			self.addConstraint(constraint)

		if 'MeshConstraints' in meshdict:
			for keys in meshdict['MeshConstraints']:
				self.addConstraint(meshdict['MeshConstraints'][keys])


	def addConstraint(self, constraint):
		"""
		parses a constraint dictionary of the form {'Expression': name, 'min':, 'max': }
		"""
		c = Constraint(constraint['expr'], (constraint['min'], constraint['max']))
		self.constraints.append(c)

	def setFunc(self, func):
		"""
		Sets the mesh generating function to either a passed external function func,
		or looks up the function by string name
		"""
		print func
		if isinstance(func, str):
			try:
				self.func = getattr(self, func)
			except AttributeError:
				try:
					self.func = getattr(self, "mfunc_"+func)
				except AttributeError:
					print("Mesh function not Found")
		elif callable(func):
			self.func = func

	def generate_mesh(self):
		self.mask = np.ones((self.y[2], self.x[2]), dtype=bool)  # to match the 'xy' indexing of meshgrids 
		x = np.linspace(*self.x[1], num=self.x[2])
		y = np.linspace(*self.y[1], num=self.y[2])
		x, y = np.meshgrid(x, y)
		self.mesh = {self.x[0]:x, self.y[0]:y}
		self.mesh.update(self.func(x, y, **self.params))
		return self.mesh

	def getMesh(self):
		return self.mesh

	def listConstraints(self):
		return self.constraints

	def filter(self):
		for c in self.constraints:
			if c[0] in self.mesh:
				mask = np.logical_and(self.mesh[c[0]] >= c[1][0], self.mesh[c[0]] <= c[1][1])
				self.mask = np.logical_and(self.mask, mask)
			else:
				try:
					tmp = self.parseConstraint(c[0], self.mesh)
					mask = np.logical_and(tmp >= c[1][0], tmp <= c[1][1])
					self.mask = np.logical_and(self.mask, mask)
				except:
					print("Couldn't parse constraint")

		return self.mask
    
	@staticmethod
	def parseConstraint(expression, variables):
		m = mathExpression(expression)
		return m.eval_rpn(variables)


class mesh2DMLGBLG(mesh2D):
	def __init__(self, meshdict):
		super(mesh2DMLGBLG, self).__init__(meshdict, None)

	@staticmethod
	def mfunc_vblg_fixed(pblg, nblg, n0mlg=0, delta1=0, delta2=0, vblg=0, **kwargs):
		"""
		Calculates the output voltages required to tune the BLG into (nblg, pblg) and MLG into nmlg
		at fixed MLG voltage.
		MLG/BLG Amplitude modulation code
		:param pblg: polarizing electric field in the BLG
		:param nblg: charge carrier density in the BLG
		:param nmlg: charge carrier density in the MLG
		:param delta1: Top gate and interlayer BN thickness imbalance
		:param delta2: Interlayer thickness and Bottom gate BN thickness imbalance
		"""
		vtop = vblg - (nblg + pblg)/(1.0 + delta1)/(1.0 + delta2) - n0mlg/(1.0 + delta1)
		vmlg = vblg - 0.5*(nblg + pblg)/(1.0 + delta2)
		vbot = vblg - 0.5*(nblg - pblg)/(1.0 - delta2)
		return {'Vtop':vtop, 'Vmlg':vmlg, 'Vbot':vbot}

	@staticmethod
	def mfunc_n0mlg():
		pass


				
