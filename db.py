import numpy as np
#import pandas as pandas
from io import BytesIO
from threading import Lock
import pickle as pickle
import json as json
import math as math
from os import remove

adcpLock = Lock()
adcpDBPath = "data/adcp_db.pickle"
adcpDB = {}

def adcpGetDBKey(station, dataType, depth):
	return "adcp-{}-{}-{}".format(station, dataType, depth)

def adcpReadDB():
	global adcpDB
	try:
		adcpDB = pickle.load(open(adcpDBPath, "rb"))
	except:
		adcpDB = {}

adcpReadDB()

def adcpAcquireLock():
	global adcpLock
	while not adcpLock.acquire():
		pass

def adcpReleaseLock():
	global adcpLock
	adcpLock.release()

def adcpWriteDB(acquireLock=True):
	global adcpDB
	if acquireLock:
		adcpAcquireLock()
	try:
		pickle.dump(adcpDB, open(adcpDBPath, "wb"))
	except:
		pass
	if acquireLock:
		adcpReleaseLock()
		

#TODO: UPDATEEE
def adcpUpdateDB(station, nBins, startDepth, firstBinHeight, binHeight):
	global adcpDB
	if not (station in adcpDB):
		adcpDB[station] = {}
	adcpDB[station]["nBins"] = nBins
	adcpDB[station]["startDepth"] = startDepth
	adcpDB[station]["firstBinHeight"] = firstBinHeight
	adcpDB[station]["binHeight"] = binHeight
	adcpWriteDB()

def adcpIsInDB(station):
	return (station in adcpDB)

def adcpDeleteFromDB(station, acquireLock=True):
	global adcpDB
	if not adcpIsInDB(station):
		return False
	if acquireLock:
		adcpAcquireLock()
	del adcpDB[station]
	adcpWriteDB(False)
	if acquireLock:
		adcpReleaseLock()
	


def adcpGetFileName(station, dataType, depth):
	return "data/adcp-{}-{}-{}.npy".format(station, dataType, depth)
	
def adcpStore(metadata, dataSet):
	#TODO: Error handling, return True/False
	dataSet.tofile(adcpGetFileName(metadata["station"], "dirmag", metadata["depth"]))
	return True

def adcpDelete(station):
	adcpAcquireLock()
	adcpDeleteFromDB(station, False)
	try:
		remove(adcpGetFileName(station))
	except:
		pass
	adcpReleaseLock()
	return True

# import dirmag
def adcpImport(csvFile, metadata):
	#TODO: Error handling
	header = ""
	while True:
		header = csvFile.readline().decode("utf-8")
		if len(header) <= 0 or header[0]!='#':
			break
	print(header)
	dataSet = np.genfromtxt(csvFile, delimiter=",", comments="#", dtype=float)
	#print(dataSet)
	print(dataSet.shape)
	if len(dataSet.shape) <= 1:
		return False
	nCols = dataSet.shape[1]
	#print(nCols)
	if nCols < 3 or nCols%2 != 1:
		return False
	nBins = (nCols-1)/2
	metadata["nBins"] = nBins 
	if adcpStore(metadata, dataSet):
		adcpUpdateDB(metadata)
		return True
	return False
	

	
def adcpLoad(station, nCols):
	#TODO: Error handling
	fileName = adcpGetFileName(station)
	return np.fromfile(fileName).reshape((-1, nCols))
	

def adcpGetJSONSeries(station, depth):
	global adcpDB
	if not (station in adcpDB):
		return json.dumps({"data":[]})
	
	distance = adcpDB[station]["startDepth"] - depth
	iBin = math.ceil(max(distance - adcpDB[station]["firstBinHeight"], 0.0) / adcpDB[station]["binHeight"])
	if iBin >= adcpDB[station]["nBins"] or distance < 0.0:
		return json.dumps({"data":[]})
	
	dataSet = adcpLoad(station, 1 + 2*adcpDB[station]["nBins"])
	result = np.empty((dataSet.shape[0], 4))
	result[:,[0,2,3]] = dataSet[:, [0, 1+iBin, 1+adcpDB[station]["nBins"]+iBin]]
	result[:,1] = depth 
	return json.dumps({"data": result.tolist()})


def getStationsDB():
	return {}
