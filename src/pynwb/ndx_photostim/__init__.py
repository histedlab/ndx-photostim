import os
from pynwb import load_namespaces

# Set path of the namespace.yaml file to the expected install location
ndx_photostim_specpath = os.path.join(
    os.path.dirname(__file__),
    'spec',
    'ndx-photostim.namespace.yaml'
)

# If the extension has not been installed yet but we are running directly from
# the git repo
if not os.path.exists(ndx_photostim_specpath):
    ndx_photostim_specpath = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        '..', '..', '..',
        'spec',
        'ndx-photostim.namespace.yaml'
    ))

# Load the namespace
load_namespaces(ndx_photostim_specpath)

# them accessible at the package level
# SpatialLightModulator = get_class('SpatialLightModulator', 'ndx-photostim')

from .photostim import SpatialLightModulator, Laser, PhotostimulationMethod, HolographicPattern, \
                             PhotostimulationSeries, PhotostimulationTable
