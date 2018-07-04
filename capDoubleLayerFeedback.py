import sys, yaml
import numpy as np
import mathparser, CapacitanceBridge
import time, labrad

from mesh2D import mesh2DMLGBLG

def create_DV_file(dv, cfg, **kwargs):
	try:
		# create datavault dir if it doest exist already
		dv.mkdir(cfg['file']['data_dir'])
		print "Created folder {}".format(cfg['file']['data_dir'])
		dv.cd(cfg['file']['data_dir'])
	except Exception:  # replace with correct exception
		dv.cd(cfg['file']['data_dir'])

def loadConfig(cfg_file):
	default_config = 'config.yaml'
	# Load the config file, either passed as an argument from CL or using the default
	try:
		# cfg_file = sys.argv[1]
		with open(cfg_file, 'r') as ymlfile:
			cfg = yaml.load(ymlfile)
	except IndexError as e:
		print("No config file provided, using the default {}".format(default_config))
		with open(default_config, 'r') as ymlfile:
			cfg = yaml.load(ymlfile)
	except IOError as e:
		print("Config file {} not found".format(cfg_file))
		sys.exit(0)
	return cfg

def initialize_capbridge(lck, acbox, cfg):
	acbox.select_device()
	stngs = cfg['Bridge Settings']
	s1 = np.array((0.5, 0.5)).reshape(2, 1)
	s2 = np.array((-0.5, -0.5)).reshape(2, 1)

	acbox.initialize(5) # this specifies the internal clock multiplier. 5 - is safe from overheating
	acbox.set_voltage("X1", 1.0)
	acbox.set_voltage("X2", 1.0)
	acbox.set_voltage("Y1", 0.75)  # sample excitation is 0.75 of full scale
	acbox.set_voltage("Y2", 0.75)  # initial reference excitation. Adjusted by balancing
	acbox.set_frequency(stngs['frequency'])
	time.sleep(1)

	ac_scale = 10**(-(stngs['ref_atten'] - stngs['sample_atten'])/20.0)/0.75

	bridge = CapacitanceBridge.CapacitanceBridgeSR830Lockin
	cb = bridge(lck=lck, acbox=acbox, time_const=stngs['balance_tc'], iterations=stngs['iter'],
				tolerance=stngs['tolerance'], s_in1=s1, s_in2=s2, excitation_channel="Y2")
	return cb, ac_scale

def setupMesh(cfg):
	mesh = mesh2DMLGBLG(cfg['Mesh'])
	mesh.setFunc(cfg['Mesh']['parameters']['function'])
	mesh.generate_mesh()
	mesh.filter()

	voltageChannels = cfg['Mesh']['Independent Variables']
	return mesh, voltageChannels

def set_voltages(dc, voltages, voltageChannels, ramp=False, ramptime=1.0, rampsteps=1000):
	"""
	Set voltages with optional ramp.
	<dc> labrad server: dc - dc voltage source
	<voltages> dict: {'channel label': value}
	<voltageChannels> dict: {'channel label': {'limits':(a, b), 'channel': c}}
	<ramp> boolean: do ramp if True
	<ramptime> float: overall ramptime in seconds
	<rampsteps> int: number of steps to divide the ramp range into
	"""
	if ramp:
		pass
	else:
		for key in voltageChannels: ## Crosscheck the voltage values with the channel settings
			v = voltages[key]
			ch = voltageChannels[key]
			if v <= max(ch['limits']) and (v>=min(ch['limits'])):
				dc.set_voltage(ch['channel'], v)

def rtheta(vec):
	"""
	Calculate magnitude and phase from vector quadratures
	"""
	magnitude = np.sqrt(vec[0]**2+vec[1]**2)
	phase = -1.0*(np.degrees(np.arctan2(vec[1], vec[0])))
	if phase < 0: phase = 360+phase
	return float(magnitude), float(phase)

def rowRampParams(i, voltageChannels, mesh):
	ch, vStart, vStop =[], [], []  # initiailze varaiables
	tmpMask = mesh.mask[i,:].nonzero()[0]  # indicies of non masked value
	idx0, idx1 = tmpMask[0], tmpMask[-1]  # index of first and last value in row to measure
	pnts = np.sum(tmpMask)  # number of points to ramp over 

	for v in voltageChannels:  # iterate though all channels
    	ch.append(voltageChannels[v]['channel'])    	
    	vStart.append(mesh.mesh[v][i,idx0])  # starting ramp voltage
    	vStop.append(mesh.mesh[v][i,idx1])  # ending ramp voltage

    return ch, start, stop, pnts

def main(): 
	cfg = loadConfig(sys.argv[1])
	cxn = labrad.connect()

	reg = cxn.registry()
	lck = cxn.sr860; lck.select_device()
	dc = cxn.dac_adc; dc.select_device()

	capBridge, ac_scale = initialize_capbridge(lck, cxn.acbox, cfg)
	mesh, voltageChannels = setupMesh(cfg)


	reg.cd(['Measurements', 'Capacitance'])
	if cfg['Bridge Settings']['rebalance']:  # balance capacitance bridge
		bpoint = cfg['Bridge Settings']['Balance Point']
		balanceVoltages = mesh.func(bpoint['x'], bpoint['y'])
		lck.time_constant(cfg['Bridge Settings']['balance_tc'])
		set_voltages(dc, balanceVoltages, voltageChannels)

		balance = capBridge.balance()
		cs, ds = capBridge.capacitance(ac_scale)
		c_, d_ = capBridge.offBalance(ac_scale)
		balance_params = {'Capacitance':cs, 'Dissipation':ds, 'Cscaling':c_, 'Dscaling':d_ }
		reg.set('Measured capacitance', [('Capacitance', cs), ('Dissipation', ds), ('Cscaling', c_),('Dscaling', d_)])
		reg.set('Balance point', (rtheta(capBridge.vb)))
	else:  # load previously measured balance point from registry
		r,th = reg.get('Balance point')
		cxn.acbox.set_voltage("Y2", r)
		cxn.acbox.set_phase(th)
		balance_params = dict(reg.get('Measured capacitance'))


	readCh = cfg['Bridge Settings']['DAC Read Channels'].values()  # channels to read
	dwell = 3 * cfg['Bridge Settings']['timeconstant'] * 1e6  # dwell time per points in microseconds
	for i in range(mesh.y.Points):  # iterate over all rows
		writeCh, start, stop, points = rowRampParams(i, voltageChannels, mesh)
		tmp = dc.buffer_ramp(writeCh, readCh, start, stop, points, dwell, conversiontime)





if __name__ == '__main__':
    main()