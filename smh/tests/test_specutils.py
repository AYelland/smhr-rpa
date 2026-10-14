from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import os

from smh import specutils

datadir = os.path.dirname(os.path.abspath(__file__))+'/test_data'

def test_load_and_write(tmp_path):
    spec = specutils.Spectrum1D.read(datadir+"/spectra/hd122563.fits")
    text_path = tmp_path / "spectrum.txt"
    spec.write(str(text_path))
    assert text_path.exists()
    assert text_path.stat().st_size > 0
    
