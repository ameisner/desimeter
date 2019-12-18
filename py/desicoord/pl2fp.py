"""
Utility functions to fit and apply coordinates transformation from PL (petal local) to FP (focal plane ~ CS5)
"""

import numpy as np
from desiutil.log import get_logger
from astropy.table import Table,Column
from pkg_resources import resource_filename


# %% rotation matrices
def Rx(angle):  # all in radians
    Rx = np.array([
        [1.0,           0.0,            0.0],
        [0.0,           np.cos(angle),  -np.sin(angle)],
	[0.0,           np.sin(angle),  np.cos(angle)]
    ])
    return Rx

	
def Ry(angle):  # all in radians
    Ry = np.array([
	[np.cos(angle),  0.0,            np.sin(angle)],
	[0.0,            1.0,            0.0],
	[-np.sin(angle), 0.0,            np.cos(angle)]
    ])
    return Ry
	
	
def Rz(angle):  # all in radians
    Rz = np.array([
	[np.cos(angle), -np.sin(angle), 0.0],
    [np.sin(angle), np.cos(angle),  0.0],
	[0.0,           0.0,            1.0]
    ])
    return Rz

	
def Rxyz(alpha, beta, gamma):  # yaw-pitch-roll system, all in radians
    return Rz(gamma) @ Ry(beta) @ Rx(alpha)  # @ is matrix multiplication
	
def apply_pl2fp(spots,petal_alignment_dict) :

    log = get_logger()
    
    nspot = spots['Petal Loc ID'].size

    # local petal coordinates 'pl'
    xyzpl = np.zeros((3,nspot))

    # rename the columns if needed
    if 'X FCL' in spots.dtype.names :
        spots.rename_column('X FCL', 'XLP')
        log.warning("rename_column('X FCL', 'XLP')")
    if 'Y FCL' in spots.dtype.names :
        spots.rename_column('Y FCL', 'YLP')
        log.warning("rename_column('Y FCL', 'YLP')")
    if 'Z FCL' in spots.dtype.names :
        spots.rename_column('Z FCL', 'ZLP')
        log.warning("rename_column('Z FCL', 'ZLP')")
    
        
    xyzpl[0] = spots['XLP']
    xyzpl[1] = spots['YLP']
    xyzpl[2] = spots['ZLP']
    
    # global focal plane coordinates 'fp'
    xyzfp = np.zeros((3,nspot))
    
    for petal in np.unique(spots['Petal Loc ID']) :
        ii = np.where(spots['Petal Loc ID']==petal)[0]
        params = petal_alignment_dict[petal]
        Rotation = Rxyz(params["alpha"],params["beta"],params["gamma"])
        Translation = np.array([params["Tx"],params["Ty"],params["Tz"]])
        xyzfp[:,ii] = Rotation.dot(xyzpl[:,ii]) + Translation[:,None]
    
    if 'XFP' not in spots.dtype.names : spots.add_column(Column(np.zeros(nspot,dtype=float)),name='XFP')
    if 'YFP' not in spots.dtype.names : spots.add_column(Column(np.zeros(nspot,dtype=float)),name='YFP')
    if 'ZFP' not in spots.dtype.names : spots.add_column(Column(np.zeros(nspot,dtype=float)),name='ZFP')
    spots['XFP'] = xyzfp[0]
    spots['YFP'] = xyzfp[1]
    spots['ZFP'] = xyzfp[2]

    return spots
    
    