from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import os
import time

from smh import Session, LineList
import smh.spectral_models as sm

datadir = os.path.dirname(os.path.abspath(__file__))+'/test_data'

def test_create_session_and_analyze():
    session = Session([datadir+'/spectra/hd122563.fits'])
    session.import_linelist_as_profile_models(datadir+'/linelists/complete.list')
    #rv, e_rv = session.rv_measure()
    #print( rv, e_rv )
    session.rv_correct(0.0)

    # TODO put this in somewhere nice, as well as the rest of the normalization tab
    session.metadata["normalization"] = {
        "continuum": [1.0],
        "normalization_kwargs": [{}]
    }
    session.stitch_and_stack()
    
    start = time.time()
    num_fit = 0
    for model in session.spectral_models:
        try:
            res = model.fit()
        except (ValueError, RuntimeError, TypeError) as e:
            print("Fitting error", model)
            print(e)
        else:
            num_fit += 1
    print("Time to fit {}/{} models: {:.1f}".format(num_fit, len(session.spectral_models), time.time()-start))
    assert num_fit > 0
    session.measure_abundances()

    file_to_write_to = os.path.join(datadir, ".test_create_session.smh")
    try:
        session.save(file_to_write_to, overwrite=True)
        loaded_session = Session.load(file_to_write_to)
        assert len(loaded_session.spectral_models) == len(session.spectral_models)
    finally:
        if os.path.exists(file_to_write_to):
            os.remove(file_to_write_to)
    
