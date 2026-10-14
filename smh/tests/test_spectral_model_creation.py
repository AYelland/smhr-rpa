from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import os

from smh import Session, LineList
import smh.spectral_models as sm

datadir = os.path.dirname(os.path.abspath(__file__))+'/test_data'
synth_ll_filenames = [datadir+'/linelists/'+fname for fname in ['masseron_linch.txt','lin4077new','lin4554new']]
synth_lls = [LineList.read(filename) for filename in synth_ll_filenames]
synth_elems = ["C", "Sr", "Ba"]
eqw_ll_fname = datadir+'/linelists/complete.list'
eqw_ll = LineList.read(eqw_ll_fname)

def test_create_profile():
    session = Session([datadir+'/spectra/hd122563.fits'])
    model = sm.ProfileFittingModel(session, eqw_ll[0])
    assert model.wavelength == float(eqw_ll[0]["wavelength"])

def test_create_synthesis():
    session = Session([datadir+'/spectra/hd122563.fits'])
    for ll,elem in zip(synth_lls,synth_elems):
        model = sm.SpectralSynthesisModel(session, ll, elem)
        assert len(model.transitions) == len(ll)

def test_import_models_into_session():
    session = Session([datadir+'/spectra/hd122563.fits'])
    session.import_linelist_as_profile_models(eqw_ll_fname)
    assert len(session.spectral_models) == len(eqw_ll)
    for fname, elem in zip(synth_ll_filenames, synth_elems):
        session.import_linelist_as_synthesis_model(fname, elem)
    assert len(session.spectral_models) == len(eqw_ll) + len(synth_lls)

def test_import_eqw_into_session():
    session = Session([datadir+'/spectra/hd122563.fits'])
    session.import_linelist_as_profile_models(datadir+"/linelists/frebel13_HD122563.moog2",
                                              import_equivalent_widths=True)
    assert session.spectral_models

if __name__=="__main__":
    test_create_profile()
    test_create_synthesis()
    test_import_models_into_session()
    test_import_eqw_into_session()
