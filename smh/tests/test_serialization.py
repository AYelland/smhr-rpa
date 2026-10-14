from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import os
import time

from smh import Session, LineList
import smh.spectral_models as sm
import pickle

datadir = os.path.dirname(os.path.abspath(__file__))+'/test_data'

def test_serialize_linelist(tmp_path):
    ll = LineList.read(datadir+"/linelists/complete.list")
    file_to_write_to = tmp_path / "serialize.linelist.pkl"
    with open(file_to_write_to, "wb") as fp:
        pickle.dump(ll, fp)
    with open(file_to_write_to, "rb") as fp:
        loaded_ll = pickle.load(fp)
    assert len(loaded_ll) == len(ll)
    
def test_load_serialized_linelist():
    ## previously dumped complete.list to this file
    file_to_load = datadir+"/test_load_serialized_linelist.pkl" 
    with open(file_to_load, "rb") as fp:
        ll = pickle.load(fp, encoding="latin1")
    assert len(ll) > 0
    
if __name__=="__main__":
    test_serialize_linelist()
    test_load_serialized_linelist()
    
    fmt = "{} {}: {:.3f}/{} = {:.3f}"

    # Time loading/writing
    Niter = 20
    ll = LineList.read(datadir+"/linelists/complete.list")
    ll = LineList.read(datadir+"/linelists/complete.list")[0:1]
    print ("N lines = {}".format(len(ll)))

    # Time pkl save
    start = time.time()
    fname = "./complete.pkl"
    for i in range(Niter):
        with open(fname, "wb") as fp:
            pickle.dump(ll, fp)
    end = time.time()-start
    print( fmt.format("pkl", "save", end, Niter, end/Niter) )
    # Time pkl load
    start = time.time()
    fname = "./complete.pkl"
    for i in range(Niter):
        with open(fname, "rb") as fp:
            _ll = pickle.load(fp)
    end = time.time()-start
    print( fmt.format("pkl", "load", end, Niter, end/Niter) )
    # Time fits save
    start = time.time()
    fname = "./complete.fits"
    for i in range(Niter):
        ll.write(fname, format='fits', overwrite=True)
    end = time.time()-start
    print( fmt.format("fits", "save", end, Niter, end/Niter) )
    # Time fits save
    start = time.time()
    fname = "./complete.fits"
    for i in range(Niter):
        _ll = LineList.read(fname, format='fits')
    end = time.time()-start
    print( fmt.format("fits", "load", end, Niter, end/Niter) )

    print ( "File size: pkl={}, fits={}".format(os.path.getsize("complete.pkl"), os.path.getsize("complete.fits")))
