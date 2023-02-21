from collections.abc import Iterable
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from hdmf.utils import docval, getargs, popargs, popargs_to_dict, get_docval
from pynwb import register_class, load_namespaces, register_map
from pynwb.base import TimeSeries
from pynwb.core import DynamicTable, MultiContainerInterface
from pynwb.device import Device
from pynwb.file import NWBContainer
from pynwb.ophys import PlaneSegmentation, ImagingPlane

from pynwb.io.base import TimeSeriesMap
from pynwb.io.core import NWBContainerMapper

ns_path = "test.namespace.yaml"
load_namespaces(ns_path)

namespace = 'test'

@register_class('SpatialLightModulator', namespace)
class SpatialLightModulator(Device):
    """
    Spatial light monitor used in the experiment.
    """

    __nwbfields__ = ('size',)

    @docval({'name': 'name', 'type': str, 'doc': ("Name of SpatialLightMonitor.")},
            *get_docval(Device.__init__, 'description', 'manufacturer'),
            {'name': 'size', 'type': Iterable,
             'doc': ("Resolution of SpatialLightModulator (in pixels), formatted as [width, height] or [width, height, "
                     "depth]."),
             'default': None,
             'shape': ((2,), (3,))}
            )
    def __init__(self, **kwargs):
        size = popargs('size', kwargs)
        super().__init__(**kwargs)
        self.size = size


@register_class('PhotostimulationDevice', namespace)
class PhotostimulationDevice(Device):
    """
    Device used to generate photostimulation.
    """

    __nwbfields__ = (
        {'name': 'slm', 'child': True}, 'type', 'wavelength', 'opsin', 'peak_pulse_energy', 'power', 'pulse_rate')

    @docval({'name': 'name', 'type': str, 'doc': ("Name of PhotostimulationDevice.")},
            *get_docval(Device.__init__, 'description', 'manufacturer'),
            {'name': 'type', 'type': str, 'doc': ("Device used for optogenetic stimulation ('laser' or 'LED').")},
            {'name': 'wavelength', 'type': (int, float),
             'doc': ("Excitation wavelength of stimulation light (nanometers)."), 'default': None},
            {'name': 'opsin', 'type': str, 'doc': ("Type of opsin used for photoactivation."), 'default': None},
            {'name': 'power', 'type': (int, float), 'doc': ("Incident power of stimulation device (in milliwatts)."),
             'default': None},
            {'name': 'peak_pulse_energy', 'type': (int, float),
             'doc': ("If device is pulsed laser: pulse energy  (in microjoules)."), 'default': None},
            {'name': 'pulse_rate', 'type': (int, float),
             'doc': ("If device is pulsed laser: pulse rate (in kHz) used for stimulation."), 'default': None},
            {'name': 'slm', 'type': SpatialLightModulator,
             'doc': ("SpatialLightModulator used to generate holographic patterns with the PhotostimulationDevice."),
             'default': None},
            )
    def __init__(self, **kwargs):
        keys_to_set = ('slm', 'type', 'wavelength', 'opsin', 'peak_pulse_energy', 'power', 'pulse_rate')
        args_to_set = popargs_to_dict(keys_to_set, kwargs)
        super().__init__(**kwargs)

        for key, val in args_to_set.items():
            setattr(self, key, val)

    @docval({'name': 'slm', 'type': SpatialLightModulator,
             'doc': ("SpatialLightModulator used to generate holographic patterns with the PhotostimulationDevice")})
    def add_slm(self, slm):
        '''
        Add a spatial light modulator to the photostimulation device.
        '''

        if self.slm is not None:
            raise ValueError("SpatialLightMonitor already exists in this device")
        else:
            self.slm = slm



@register_class('HolographicPattern', namespace)
class HolographicPattern(NWBContainer):
    '''
    Container to store the pattern used in a photostimulation experiment.
    '''

    __nwbfields__ = ('pixel_roi', 'image_mask_roi', 'roi_size', 'dimension')

    @docval(*get_docval(NWBContainer.__init__) + (
            {'name': 'image_mask_roi', 'type': 'array_data',
             'doc': ("ROIs designated using a mask of size [width, height] (2D stimulation) or [width, height, "
                     "depth] (3D stimulation), where for a given pixel a value of 1 indicates stimulation, "
                     "and a value of 0 indicates no stimulation. "),
             'default': None, 'shape': ([None] * 2, [None] * 3)},
            {'name': 'pixel_roi', 'type': 'array_data',
             'doc': ("ROIs designated as a list specifying the pixel ([x1, y1], [x2, y2], …) or voxel ([x1, y1, z1], "
                     "[x2, y2, z2], …) of each ROI, where the items in the list are the coordinates of the center of "
                     "the ROI. The size of each ROI is specified via the required 'roi_size' parameter."),
             'default': None, 'shape': ((None, 2), (None, 3))},
            {'name': 'roi_size', 'type': (int, float, Iterable),
             'doc': ("Size of a single stimulation ROI in pixels. If a scalar is provided, the ROI is assumed to be a "
                     "circle (for 2D patterns) or cylinder (for 3D patterns) centered at the corresponding "
                     "coordinates, with diameter 'roi_size'. If 'roi_size' is a two or three dimensional array, "
                     "the ROI is assumed to be a rectangle or cuboid, with dimensions [width, height] or [width, "
                     "height, depth]. This parameter is required when using 'pixel_roi'."),
             'default': None},
            {'name': 'dimension', 'type': Iterable,
             'doc': ("Number of pixels on x, y, (and z) axes. Calculated automatically when ROI is input using "
                     "'image_mask_roi.' Required when using 'pixel_roi.'"),
             'default': None, 'shape': ((2,), (3,))}
    ))
    def __init__(self, **kwargs):
        keys_to_set = ("pixel_roi", "image_mask_roi", "roi_size", "dimension")
        args_to_set = popargs_to_dict(keys_to_set, kwargs)

        roi_size = args_to_set['roi_size']
        if isinstance(roi_size, Iterable):
            if len(roi_size) != 2 and len(roi_size) != 3:
                raise ValueError("roi_size must be a scalar, a 2D iterable, or a 3D iterable")

        super().__init__(**kwargs)

        if args_to_set['pixel_roi'] is None and args_to_set['image_mask_roi'] is None:
            raise TypeError("Must provide 'pixel_roi' or 'image_mask_roi' when constructing HolographicPattern")

        if args_to_set['dimension'] is not None and isinstance(args_to_set['dimension'], list):
            args_to_set['dimension'] = tuple(args_to_set['dimension'])

        if args_to_set['pixel_roi'] is not None:
            if args_to_set['roi_size'] is None:
                raise TypeError("'roi_size' must be specified when using a pixel mask")

            if args_to_set['dimension'] is None:
                raise TypeError("'dimension' must be specified when using a pixel mask")

        if args_to_set['image_mask_roi'] is not None:
            mask_dim = args_to_set['image_mask_roi'].shape

            if args_to_set['dimension'] is None:
                args_to_set['dimension'] = mask_dim

            if len(np.setdiff1d(np.unique(args_to_set['image_mask_roi']), np.array([0, 1]))) > 0:
                if len(np.setdiff1d(np.unique(args_to_set['image_mask_roi']), np.array([0., 1.]))) > 0:
                    raise ValueError("'image_mask_roi' data must be either 0 (off) or 1 (on)")

        for key, val in args_to_set.items():
            setattr(self, key, val)



    def show_mask(self):
        '''
        Display a plot with a 2D mask of the holographic pattern (white regions denote ROIs, black regions the background).
        '''

        if len(self.dimension) == 3:
            raise ValueError("Cannot display 3D masks")

        if self.pixel_roi is not None:
            center_points = [[roi[0], roi[1]] for roi in self.pixel_roi]
            center_points = np.array(center_points)
            image_mask_roi = self.pixel_to_image_mask_roi()
            plt.imshow(image_mask_roi, 'gray', interpolation='none')
            plt.scatter(center_points[:, 0], center_points[:, 1], color='red', s=10)

        if self.image_mask_roi is not None:
            image_mask_roi = self.image_mask_roi
            plt.imshow(image_mask_roi, 'gray', interpolation='none')

        plt.axis('off')
        plt.show()

    @staticmethod
    def _create_circular_mask(dimensions, center, diameter):
        '''

        '''
        Y, X = np.ogrid[:dimensions[1], :dimensions[0]]
        dist_from_center = np.sqrt((X - center[0]) ** 2 + (Y - center[1]) ** 2)

        mask = dist_from_center <= diameter / 2
        return mask

    @staticmethod
    def _create_rectangular_mask(dimensions, center, roi_size, img_depth=None):
        '''

        '''

        if img_depth is None:
            Y, X = np.ogrid[:dimensions[1], :dimensions[0]]
            X_dist_from_center = (X - center[0])
            Y_dist_from_center = (Y - center[1])
            mask = (np.abs(X_dist_from_center) <= roi_size[0] / 2) & (np.abs(Y_dist_from_center) <= roi_size[1] / 2)
        return mask

    def pixel_to_image_mask_roi(self):
        '''
        Convert a pixel_roi to an image_mask_roi. Returns a 2D array containing the mask, where ROIs are encoded with a value of 1.
        '''
        if len(self.dimension) == 3:
            raise ValueError("Cannot convert 3D pixel_roi to image_mask_roi")

        mask = np.zeros(shape=self.dimension)
        for roi in self.pixel_roi:

            if not isinstance(self.roi_size, Iterable):
                tmp_mask = self._create_circular_mask(self.dimension, roi, self.roi_size)
            else:
                tmp_mask = self._create_rectangular_mask(self.dimension, roi, self.roi_size)
            mask[tmp_mask] = 1

        return mask

    @staticmethod
    def image_to_pixel(image_mask):
        """Converts an image_mask_roi into a pixel_mask_roi."""
        pixel_mask = []
        it = np.nditer(image_mask, flags=['multi_index'])
        while not it.finished:
            weight = it[0][()]
            if weight > 0:
                x = it.multi_index[0]
                y = it.multi_index[1]
                pixel_mask.append([x, y, 1])
            it.iternext()
        return pixel_mask


@register_class('HolographicPattern2', namespace)
class HolographicPattern2(PlaneSegmentation):
    '''
    Container to store the pattern used in a photostimulation experiment.
    '''

    @docval(*get_docval(PlaneSegmentation.__init__),
            {'name': 'dimension', 'type': Iterable,
             'doc': ("Number of pixels on x, y, (and z) axes. Calculated automatically when ROI is input using "
                     "'image_mask_roi.' Required when using 'pixel_roi.'"),
             'default': None, 'shape': ((2,), (3,))}
    )
    def __init__(self, **kwargs):
        keys_to_set = ("dimension",)
        args_to_set = popargs_to_dict(keys_to_set, kwargs)
        super().__init__(**kwargs)

        for key, val in args_to_set.items():
            setattr(self, key, val)

        if self.dimension is not None and isinstance(self.dimension, list):
            self.dimension = tuple(self.dimension)



    @docval(
            {'name': 'image_mask', 'type': 'array_data',
             'doc': ("ROIs designated using a mask of size [width, height] (2D stimulation) or [width, height, "
                     "depth] (3D stimulation), where for a given pixel a value of 1 indicates stimulation, "
                     "and a value of 0 indicates no stimulation."),
             'default': None, 'shape': ([None] * 2, [None] * 3)},
            {'name': 'pixel_mask', 'type': 'array_data',
             'doc': ("ROIs designated as a list specifying the pixel ([x1, y1], [x2, y2], …) of each ROI, where the "
                     "items in the list are the coordinates of the center of the ROI. The size of each ROI is specified "
                     "via the required 'roi_size' parameter."),
             'default': None, 'shape': (None, 2)},
            {'name': 'voxel_mask', 'type': 'array_data',
             'doc': ("ROIs designated as a list specifying the voxel ([x1, y1, z1], "
                 "[x2, y2, z2], …) of each ROI, where the items in the list are the coordinates of the center of "
                 "the ROI. The size of each ROI is specified via the required 'roi_size' parameter."),
             'default': None, 'shape': (None, 3)},
            {'name': 'roi_size', 'type': (int, float, Iterable),
             'doc': ("Size of a single stimulation ROI in pixels. If a scalar is provided, the ROI is assumed to be a "
                     "circle (for 2D patterns) or cylinder (for 3D patterns) centered at the corresponding "
                     "coordinates, with diameter 'roi_size'. If 'roi_size' is a two or three dimensional array, "
                     "the ROI is assumed to be a rectangle or cuboid, with dimensions [width, height] or [width, "
                     "height, depth]. This parameter is required when using 'pixel_roi'."),
             'default': None}
    )
    def add_roi(self, **kwargs):
        keys_to_set = ("roi_size",)
        args_to_set = popargs_to_dict(keys_to_set, kwargs)

        roi_size = args_to_set['roi_size']
        if isinstance(roi_size, Iterable):
            if len(roi_size) != 2 and len(roi_size) != 3:
                raise ValueError("roi_size must be a scalar, a 2D iterable, or a 3D iterable")
        #
        # if args_to_set['image_mask'] is None and args_to_set['pixel_mask'] is None:
        #     raise TypeError("Must provide 'pixel_roi' or 'image_mask_roi' when constructing HolographicPattern")


        if kwargs['pixel_mask'] is not None or kwargs['voxel_mask'] is not None:
            if args_to_set['roi_size'] is None:
                raise TypeError("'roi_size' must be specified when using a pixel or voxel mask")

            if self.dimension is None:
                raise TypeError("'dimension' must be specified in 'create_holographic_segmentation' when using a pixel or voxel mask")

        if kwargs['image_mask'] is not None:
            mask_dim = kwargs['image_mask'].shape

            if self.dimension is None:
                self.dimension = mask_dim

            if len(np.setdiff1d(np.unique(kwargs['image_mask']), np.array([0, 1]))) > 0:
                if len(np.setdiff1d(np.unique(kwargs['image_mask']), np.array([0., 1.]))) > 0:
                    raise ValueError("'image_mask' data must be either 0 (off) or 1 (on)")

        if kwargs['pixel_mask'] is not None:
            kwargs['pixel_mask'] = [[el[0], el[1], 1] for el in kwargs['pixel_mask']]

        if kwargs['voxel_mask'] is not None:
            kwargs['voxel_mask'] = [[el[0], el[1], el[2], 1] for el in kwargs['voxel_mask']]

        super().add_roi(**kwargs)

        for key, val in args_to_set.items():
            setattr(self, key, val)

    def show_mask(self):
        '''
        Display a plot with a 2D mask of the holographic pattern (white regions denote ROIs, black regions the background).
        '''

        if self.voxel_mask is not None:
            raise ValueError("Cannot display 3D masks")

        if self.pixel_mask is not None:
            center_points = [[roi[0], roi[1]] for roi in self.pixel_mask]
            center_points = np.array(center_points)
            image_mask_roi = self.pixel_to_image_mask_roi()
            plt.imshow(image_mask_roi, 'gray', interpolation='none')
            plt.scatter(center_points[:, 0], center_points[:, 1], color='red', s=3)

        if self.image_mask is not None:
            plt.imshow(np.sum(self.image_mask, axis=0), 'gray', interpolation='none')

        plt.axis('off')
        plt.show()


    @staticmethod
    def _create_circular_mask(dimensions, center, diameter):
        '''

        '''
        Y, X = np.ogrid[:dimensions[1], :dimensions[0]]
        dist_from_center = np.sqrt((X - center[0]) ** 2 + (Y - center[1]) ** 2)

        mask = dist_from_center <= diameter / 2
        return mask

    @staticmethod
    def _create_rectangular_mask(dimensions, center, roi_size, img_depth=None):
        '''

        '''

        if img_depth is None:
            Y, X = np.ogrid[:dimensions[1], :dimensions[0]]
            X_dist_from_center = (X - center[0])
            Y_dist_from_center = (Y - center[1])
            mask = (np.abs(X_dist_from_center) <= roi_size[0] / 2) & (np.abs(Y_dist_from_center) <= roi_size[1] / 2)
        return mask

    def pixel_to_image_mask_roi(self):
        '''
        Convert a pixel_roi to an image_mask_roi. Returns a 2D array containing the mask, where ROIs are encoded with a value of 1.
        '''
        if len(self.dimension) == 3:
            raise ValueError("Cannot convert 3D pixel_roi to image_mask_roi")

        mask = np.zeros(shape=self.dimension)
        for roi in self.pixel_mask:

            if not isinstance(self.roi_size, Iterable):
                tmp_mask = self._create_circular_mask(self.dimension, roi, self.roi_size)
            else:
                tmp_mask = self._create_rectangular_mask(self.dimension, roi, self.roi_size)
            mask[tmp_mask] = 1

        return mask


@register_class('HolographicSegmentation', namespace)
class HolographicSegmentation(MultiContainerInterface):
    """
    Stores pixels in an image that represent different regions of interest (ROIs) or masks. All
    segmentation for a given imaging plane is stored together, with storage for multiple imaging
    planes (masks) supported. Each ROI is stored in its own subgroup, with the ROI group
    containing both a 2D mask and a list of pixels that make up this mask. Segments can also be
    used for masking neuropil. If segmentation is allowed to change with time, a new imaging plane
    (or module) is required and ROI names should remain consistent between them.
    """
    __clsconf__ = {
        'attr': 'holographic_segmentations',
        'type': HolographicPattern2,
        'add': 'add_holographic_segmentation',
        'get': 'get_holographic_segmentation',
        'create': 'create_holographic_segmentation'
    }

    @docval({'name': 'imaging_plane', 'type': ImagingPlane, 'doc': 'the ImagingPlane this ROI applies to'},
            {'name': 'description', 'type': str,
             'doc': 'Description of image plane, recording wavelength, depth, etc.', 'default': None},
            {'name': 'name', 'type': str, 'doc': 'name of PlaneSegmentation.', 'default': None})
    def add_segmentation(self, **kwargs):
        kwargs.setdefault('description', kwargs['imaging_plane'].description)
        return self.create_holographic_segmentation(**kwargs)




@register_class('PhotostimulationSeries', namespace)
class PhotostimulationSeries(TimeSeries):
    '''
    TimeSeries object for photostimulus presentation.
    '''

    __nwbfields__ = ({'name': 'pattern', 'child': True}, 'format', 'stimulus_duration',
                     "stimulus_method", "sweep_pattern", "time_per_sweep", "num_sweeps",
                     {'name': 'unit', 'settable': False})

    @docval(*get_docval(TimeSeries.__init__, 'name'),
            {'name': 'format', 'type': str,
             'doc': ("Format of data denoting stimulus presentation. Can be either 'interval' or 'series' (see "
                     "description for the 'data' parameter for details)"), 'enum': ["interval", "series"]},
            {'name': 'data', 'type': ('array_data', 'data', TimeSeries), 'shape': (None,),
             'doc': ("1D list containing information about stimulus presentation. If format is 'interval', the onset "
                     "and offset of the stimulus is stored using a 1D array consisting of the values 1 (stimulus on) "
                     "and -1 (stimulus off). The corresponding times for the start and stop of the stimulus are "
                     "specified via the 'timestamp' property, where 'data[i]==1' denotes the onset of the stimulus at "
                     "time 'timestamps[i]', and 'data[i+1]==-1' denotes its offset at time 'timestamps[i+1]' (time is "
                     "specified in seconds). If format is 'series', data consists of binary (0 or 1) values, to "
                     "indicate whether the stimulus was presented at a given time. A value of 'data[i]==1' at time "
                     "'timestamps[i]', for example, indicates the stimulus was presented at time 'timestamps[i]' for "
                     "'timestamps[i]'+'stimulus_duration' seconds. Alternatively, 'rate' can be specified instead of "
                     "'timestamps', when data are sampled uniformly. Either 'timestamps' or 'rate' must be specified "
                     "when using the series format."), 'default': list()},
            {'name': 'timestamps', 'type': ('array_data', 'data', TimeSeries, Iterable),
             'doc': ("Timestamps corresponding to stimulus presentation values contained in 'data'."),
             'default': None, 'shape': (None,)},
            {'name': 'rate', 'type': (int, float), 'doc': ("Sampling rate of the data in Hz."), 'default': None},
            {'name': 'stimulus_duration', 'type': (int, float),
             'doc': ("Duration (in sec) the stimulus is presented following onset. Must be specified if format is "
                     "'series'. "), 'default': None},
            {'name': 'pattern', 'type': HolographicPattern, 'doc': ("HolographicPattern used as stimulation pattern.")},
            {'name': 'stimulus_method', 'type': str,
             'doc': ("Scanning or scanless method for shaping optogenetic light (e.g., diffraction limited points, "
                     "3D shot, disks, etc.)."), 'default': None},
            {'name': 'sweep_pattern', 'type': str,
             'doc': ("Sweeping pattern, if spatially modulated during stimulation (none, or other). Requires "
                     "'stim_method' is specified. (ex. logspiral)"), 'default': None},
            {'name': 'time_per_sweep', 'type': (int, float),
             'doc': ("Time to conduct a sweep (in milliseconds)."), 'default': None},
            {'name': 'num_sweeps', 'type': (int, float),
             'doc': ("Repetition of a sweep pattern for a single stimulation instance. "), 'default': None},
            {'name': 'unit', 'type': str, 'doc': ("Timestamps unit (default: seconds)."), 'default': 'seconds'},
            *get_docval(TimeSeries.__init__, 'resolution', 'conversion', 'starting_time',
                        'comments', 'description', 'control', 'control_description', 'offset')
            )
    def __init__(self, **kwargs):
        # Convert data to np array
        if isinstance(kwargs['data'], np.ndarray):
            kwargs['data'] = list(kwargs['data'])
        #
        if isinstance(kwargs['timestamps'], (list, tuple)):
            kwargs['timestamps'] = list(kwargs['timestamps'])

        if kwargs['sweep_pattern'] is not None:
            if kwargs['stimulus_method'] is None:
                raise ValueError("If 'sweep_pattern' must be defined to use 'stimulus_method''")

        # If using interval format...
        if kwargs['format'] == 'interval':
            if len(kwargs['data']) == 0:
                # kwargs['data'] = np.array([])

                if kwargs['timestamps'] is not None:
                    raise ValueError("'timestamps' can't be specified without corresponding 'data'")
                kwargs['timestamps'] = []
                # kwargs['timestamps'] = np.array([])
            # if intervals are input, check that formatted correctly
            else:
                # check that timestamps are also input
                if kwargs['timestamps'] is None:
                    raise ValueError("Need to specify corresponding 'timestamps' for each entry in 'data'")

                # print(kwargs['data'], kwargs['timestamps'])

                # check data and timestamps are same length
                if len(kwargs['data']) != len(kwargs['timestamps']):
                    raise ValueError("'data' and 'timestamps' need to be the same length")

                if len(np.setdiff1d(np.unique(kwargs['data']), np.array([-1, 1]))) > 0:
                    if len(np.setdiff1d(np.unique(kwargs['data']), np.array([-1., 1.]))) > 0:
                        raise ValueError("'interval' data must be either -1 (offset) or 1 (onset)")

        # if using series format
        if kwargs['format'] == 'series':
            if kwargs['stimulus_duration'] is None:
                raise ValueError("if 'format' is 'series', 'stimulus_duration' must be specified")

            if len(kwargs['data']) == 0:
                # kwargs['data'] = np.array([])

                if kwargs['timestamps'] is not None:
                    raise ValueError("'timestamps' can't be specified without corresponding 'data'")

                if kwargs['rate'] is None:
                    kwargs['timestamps'] = []
                # kwargs['timestamps'] = np.array([])
            else:
                if kwargs['timestamps'] is None and kwargs['rate'] is None:
                    raise ValueError("either 'timestamps' or 'rate' must be specified")

            if kwargs['timestamps'] is not None:
                # check data and timestamps are same length
                if len(kwargs['data']) != len(kwargs['timestamps']):
                    raise ValueError("'data' and 'timestamps' need to be the same length")

                if len(np.setdiff1d(np.unique(kwargs['data']), np.array([0, 1]))) > 0:
                    if len(np.setdiff1d(np.unique(kwargs['data']), np.array([0., 1.]))) > 0:
                        raise ValueError("'series' data must be either 0 or 1")

        keys_to_set = ('pattern', 'format', 'stimulus_duration',
                       'stimulus_method', 'sweep_pattern', 'time_per_sweep', 'num_sweeps')
        args_to_set = popargs_to_dict(keys_to_set, kwargs)

        data, timestamps = popargs('data', 'timestamps', kwargs)
        self.__interval_data = data
        self.__interval_timestamps = timestamps
        kwargs['unit'] = 'seconds'

        super().__init__(data=data, timestamps=timestamps, **kwargs)

        for key, val in args_to_set.items():
            setattr(self, key, val)

    @docval({'name': 'start', 'type': (int, float), 'doc': ("Start of the interval (in seconds).")},
            {'name': 'stop', 'type': (int, float), 'doc': ("End of the interval (in seconds).")})
    def add_interval(self, **kwargs):
        '''Function to indicate stimulus was presented from time 'start' to time 'end.' Requires format is
        'interval'. '''
        start, stop = getargs('start', 'stop', kwargs)
        if self.format == 'series':
            raise ValueError("Cannot add interval to PhotostimulationSeries with 'format' of 'series'")

        self.__interval_data.append(1)
        self.__interval_data.append(-1)
        self.__interval_timestamps.append(start)
        self.__interval_timestamps.append(stop)

    @docval({'name': 'timestamp', 'type': (int, float, Iterable), 'doc': ("")})
    def add_onset(self, **kwargs):
        '''
        Denote stimulation at time 'time', where time is a number or list of numbers. If type is 'series', add 1 to
        'data' and 'time' to 'timestamps'. If format is 'interval', call 'add_interval' for the interval from 'time'
        to 'time+stimulus_duration'.
        '''
        if self.stimulus_duration is None:
            raise ValueError("Cannot add presentation to PhotostimulationSeries without 'stimulus_duration'")

        timestamps = getargs('timestamp', kwargs)

        if not isinstance(timestamps, Iterable):
            timestamps = [timestamps]

        for ts in timestamps:
            if self.format == 'interval':
                self.add_interval(ts, ts + self.stimulus_duration)
            else:
                self.__interval_data.append(1)
                self.__interval_timestamps.append(ts)

    def to_dataframe(self):
        '''Display 'data' and 'timestamps' side by side as a pandas dataframe. If 'timestamps' is not specified, calculate it using 'rate'.'''
        data = np.array(self.data)
        ts = np.array(self.timestamps)

        if len(data) == 0:
            raise ValueError("No data")

        if self.timestamps is None:
            # end = self.starting_time + self.stimulus_duration * (len(data)-1)
            end = self.starting_time + (1 / self.rate) * (len(data) - 1)
            ts = np.linspace(self.starting_time, end, num=len(data), endpoint=True)

        df_dict = {'data': data, 'timestamps': ts}
        df = pd.DataFrame(df_dict)
        return df

    def _get_start_stop_list(self):
        '''Get list of tuples with format (start_time, stop_time) for the onset/offset of stimulus over timeseries.'''
        df = self.to_dataframe()

        start_stop = []
        if self.format == 'interval':
            start_times = list(df[df['data'] == 1]['timestamps'])
            end_times = list(df[df['data'] == -1]['timestamps'])

            if len(start_times) != len(end_times):
                raise ValueError("Number of starts does not equal number of stops!")

            for start, end in zip(start_times, end_times):
                start_stop.append((start, end))

        if self.format == 'series':
            start_times = list(df[df['data'] == 1]['timestamps'])

            for start in start_times:
                start_stop.append((start, start + self.stimulus_duration))
        return start_stop

    def _get_start_time(self):
        '''Returns 'starting_time' property if it exists, otherwise returns the first timestamp value if 'timestamps'
        exists. If both are none, assume the starting time is 0. '''
        if self.starting_time is not None:
            return self.starting_time

        if self.timestamps is None:
            return self.timestamps[0]

        if len(self.data) != 0:
            return 0

        return np.nan

    def _get_end_time(self):
        '''Returns the final time step value, if it exists.'''
        if len(self.data) == 0:
            return np.nan

        if self.timestamps is None:
            end = self._get_start_time() + self.stimulus_duration * (len(self.data) - 1)
            return end

        return self.timestamps[-1]

    @property
    def data(self):
        return self.__interval_data

    @property
    def timestamps(self):
        return self.__interval_timestamps

@register_class('PhotostimulationTable', namespace)
class PhotostimulationTable(DynamicTable):
    """
    Table of to hold all of an experiment's PhotostimulationSeries objects. Each PhotostimulationSeries, and associated data and metadata, is contained in its own row.
    """

    __fields__ = ('device',)
    # __fields__ = ({'name': 'photostimulation_device', 'child': True}, "stimulus_method", "sweeping_method", "time_per_sweep", "num_sweeps")

    __columns__ = (
        {'name': 'row_name', 'description': ("Name for the row of the table, and the data it corresponds to. "),
         'required': True},
        {'name': 'series', 'description': ("The PhotostimulationSeries container referenced in the row."),
         'required': True},
        {'name': 'series_name', 'description': ("Name of the PhotostimulationSeries contained in the row."),
         'required': True},
        {'name': 'series_format', 'description': ("Format of the PhotostimulationSeries ('interval' or 'series')."),
         'required': True},
        {'name': 'num_samples', 'description': ("Number of data points in the series."), 'required': True},
        {'name': 'start_time', 'description': ("Start time of the series."), 'required': True},
        {'name': 'stop_time', 'description': ("Stop time of the series."), 'required': True},
        {'name': 'pattern_name', 'description': ("Name of the HolographicPattern associated with the series."),
         'required': True},
    )

    @docval(*get_docval(DynamicTable.__init__, 'name', 'description'),
            {'name': 'device', 'type': PhotostimulationDevice,
             'doc': ("PhotostimulationDevice used in the table's PhotostimulationSeries containers."), 'default': None},
            *get_docval(DynamicTable.__init__, 'id', 'columns', 'colnames')
            )
    def __init__(self, **kwargs):

        keys_to_set = ("device",)
        # keys_to_set = ( "stimulus_method", "sweeping_method", "time_per_sweep", "num_sweeps")
        args_to_set = popargs_to_dict(keys_to_set, kwargs)

        super().__init__(**kwargs)

        for key, val in args_to_set.items():
            setattr(self, key, val)

    @docval({'name': 'series', 'type': (PhotostimulationSeries, Iterable),
             'doc': ("Single PhotostimulationSeries, or list of PhotostimulationSeries, to add to the table.")},
            {'name': 'row_name', 'type': (str, Iterable),
             'doc': ("Name of the row. Can be optionally specified, or automatically assigned as 'series_i', "
                     "where 'i' denotes the row number.\nIf adding a single PhotostimulationSeries, 'row_name' must "
                     "be a string. If adding multiple series, 'row_name' must be a list of strings with the same "
                     "length as the number of series being added. "), 'default': None},
            allow_extra=True)
    def add_series(self, **kwargs):
        """Add PhotostimulationSeries, or list of PhotostimulationSeries, to PhotostimulationTable."""

        series_list = kwargs['series']
        if not isinstance(series_list, Iterable):
            series_list = [series_list]

        row_names_list = kwargs['row_name']
        if row_names_list is None:
            row_names_list = []

            for i in range(len(series_list)):
                row_names_list.append(f"series_{i}")
        else:
            if not isinstance(row_names_list, Iterable):
                row_names_list = [row_names_list]

            if len(row_names_list) != len(series_list):
                raise ValueError("'series' and 'row_name' must be the same length")

        for series, name in zip(series_list, row_names_list):
            if len(series.data) == 0:
                raise ValueError(f"Series {series.name} has no data! Cannot add to PhotostimulationTable")

            new_args = {}
            new_args['row_name'] = name
            new_args['series'] = series
            new_args['series_name'] = series.name

            new_args['series_format'] = series.format
            new_args['num_samples'] = series.num_samples
            new_args['start_time'] = float(series._get_start_time())
            new_args['stop_time'] = float(series._get_end_time())
            new_args['pattern_name'] = series.pattern.name

            super().add_row(**new_args)

    def plot_presentation_times(self):
        '''Show a plot with each photostimulation series (y-axis), and the timestamp(s) at which that pattern was presented (x-axis).'''
        fig, ax = plt.subplots()

        y_ticks = []
        for i, series in enumerate(self.series):
            start_stop_list = series._get_start_stop_list()
            ax.broken_barh(start_stop_list, ((i + 1) * 10, 8))
            y_ticks.append((i + 1) * 10 + 4)

        ax.set_yticks(y_ticks, labels=self.series_name)
        ax.set_xlabel('Timestamp (seconds)')
        ax.set_title(f"Presentation timestamps for PhotostimulationTable '{self.name}'")
        ax.xaxis.grid()
        plt.show()
