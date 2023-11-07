# -*- coding: utf-8 -*-
import os.path

from pynwb.spec import NWBNamespaceBuilder, NWBGroupSpec, NWBAttributeSpec, NWBLinkSpec, NWBDatasetSpec, NWBRefSpec, export_spec


def main():
    # these arguments were auto-generated from your cookiecutter inputs
    ns_builder = NWBNamespaceBuilder(
        doc="""holographic photostimulation extension to NWB standard""",
        name="""ndx-photostim""",
        version="""0.1.0""",
        author=list(map(str.strip, """Paul LaFosse,Carl Harris""".split(','))),
        contact=list(map(str.strip, """paul.lafosse@nih.gov,carlwharris1@gmail.com""".split(',')))
    )

    # as in which namespace they are found.
    # this is similar to specifying the Python modules that need to be imported
    # to use your new data types.
    # all types included or used by the types specified here will also be
    # included. 
    # ns_builder.include_type('ElectricalSeries', namespace='core')
    ns_builder.include_type("TimeSeries", namespace="core")
    ns_builder.include_type("NWBDataInterface", namespace="core")
    ns_builder.include_type("NWBContainer", namespace="core")
    ns_builder.include_type("Container", namespace="hdmf-common")
    ns_builder.include_type("DynamicTable", namespace="hdmf-common")
    ns_builder.include_type("DynamicTableRegion", namespace="hdmf-common")
    ns_builder.include_type("VectorData", namespace="hdmf-common")
    ns_builder.include_type("Data", namespace="hdmf-common")
    ns_builder.include_type("ElementIdentifiers", namespace="hdmf-common")
    ns_builder.include_type("Device", namespace="core")
    ns_builder.include_type("TimeIntervals", namespace="core")

    # see https://pynwb.readthedocs.io/en/latest/extensions.html#extending-nwb
    # for more information

    slm = NWBGroupSpec(
        neurodata_type_def='SpatialLightModulator',
        neurodata_type_inc='Device',
        name='slm',
        doc=("Spatial light modulator (SLM) used in the experiment."),
        quantity='?',
        attributes=[
            NWBAttributeSpec(
                name='model',
                doc=("Name of the SLM used in experiment."),
                dtype='text',
                required=False
            ),
            NWBAttributeSpec(
                name='size',
                doc=("Resolution of SpatialLightModulator (in pixels), "
                     "formatted as [width, height] or [width, height, depth]."),
                dtype='numeric',
                shape=((2,), (3,)),
                dims=(('width', 'height'), ('width', 'height', 'depth')),
                required=False
            )
        ]
    )

    lsr = NWBGroupSpec(
        neurodata_type_def='Laser',
        neurodata_type_inc='Device',
        name='laser',
        doc=("Laser used in the experiment."),
        quantity='?',
        attributes=[
            NWBAttributeSpec(
                name='model',
                doc=("Name of the laser used in experiment."),
                dtype='text',
                required=False
            ),
            NWBAttributeSpec(
                name='wavelength',
                doc=("Excitation wavelength of stimulation light (nanometers)."),
                dtype='numeric',
                required=False
            ),
            NWBAttributeSpec(
                name='power',
                doc=("Incident power of stimulation device (in milliwatts)."),
                dtype='numeric',
                required=False
            ),
            NWBAttributeSpec(
                name='peak_pulse_energy',
                doc=("If device is pulsed laser: pulse energy  (in microjoules)."),
                dtype='numeric',
                required=False
            ),
            NWBAttributeSpec(
                name='pulse_rate',
                doc=("If device is pulsed laser: pulse rate (in kHz) used for stimulation."),
                dtype='numeric',
                required=False
            ),
        ]
    )

    ########################################################################################################################
    psm = NWBGroupSpec(
        neurodata_type_def='PhotostimulationMethod',
        neurodata_type_inc='NWBContainer',
        doc=("Methods used to apply patterned photostimulation."),
        name='method',
        attributes=[
            NWBAttributeSpec(
                name='stimulus_method',
                doc=("Scanning or scanless method for shaping optogenetic light (e.g., "
                     "diffraction limited points, 3D shot, disks, etc.)."),
                dtype='text',
                required=False
            ),
            NWBAttributeSpec(
                name='sweep_pattern',
                doc=("Sweeping method, if spatially modulated during stimulation (none, or other)."),
                dtype='text',
                required=False
            ),
            NWBAttributeSpec(
                name='sweep_size',
                doc=("Size or diameter of the scanning sweep pattern (in micrometers) "
                     "if spatially modulated during stimulation."),
                dtype='numeric',
                required=False
            ),
            NWBAttributeSpec(
                name='time_per_sweep',
                doc=("Time to conduct a sweep (in milliseconds) "
                     "if spatially modulated during stimulation."),
                dtype='numeric',
                required=False
            ),
            NWBAttributeSpec(
                name='num_sweeps',
                doc=("Repetition of a sweep pattern for a single stimulation instance"
                     "if spatially modulated during stimulation."),
                dtype='numeric',
                required=False
            ),
            NWBAttributeSpec(
                name='power_per_target',
                doc=("Power (in milliwatts) applied to each target during patterned photostimulation."),
                dtype='numeric',
                required=False
            ),
            NWBAttributeSpec(
                name='opsin',
                doc=("Opsin used in photostimulation."),
                dtype='text',
                required=False
            ),
        ],
        groups=[
            slm,
            lsr
        ]
    )

    ########################################################################################################################
    # stim_duration attribute defined at top level to be used with HolographicPattern and PhotostimulationSeries classes
    stim_duration = NWBAttributeSpec(
        name='stim_duration',
        doc=("Duration (in sec) the stimulus is presented following onset."),
        dtype='numeric',
        required=False
    )

    # roi_size attribute defined at top to be used with HolographicPattern class and pixel_roi DataSpec within
    roi_size = NWBAttributeSpec(
        name='roi_size',
        doc=("Size of a single stimulation ROI in pixels. If a scalar is provided, the ROI is "
             "assumed to be a circle (for 2D patterns) or cylinder (for 3D patterns) centered at "
             "the corresponding coordinates, with diameter 'roi_size'. If 'roi_size' is a two or "
             "three dimensional array, the ROI is assumed to be a rectangle or cuboid, "
             "with dimensions [width, height] or [width, height, depth]. This parameter is "
             "required when using 'pixel_roi'."),
        dtype='numeric',
        required=False
    )

    hp = NWBGroupSpec(
        neurodata_type_def='HolographicPattern',
        neurodata_type_inc='NWBContainer',
        name='pattern',
        doc=("Container to store the pattern used in a photostimulation experiment."),
        attributes=[
            NWBAttributeSpec(
                name='dimension',
                doc=("Number of pixels on x, y, (and z) axes. Calculated automatically when ROI is input "
                     "using 'image_mask_roi.' Required when using 'pixel_roi.'"),
                dtype='numeric',
                shape=((2,), (3,)),
                dims=(('width', 'height'), ('width', 'height', 'depth')),
                required=False
            ),

            stim_duration,
            roi_size
        ],
        datasets=[
            NWBDatasetSpec(
                name='image_mask_roi',
                doc=("ROIs designated using a mask of size [width, height] (2D stimulation) or ["
                     "width, height, depth] (3D stimulation), where for a given pixel a value of 1 "
                     "indicates stimulation, and a value of 0 indicates no stimulation."),
                quantity='?',
                dims=(('num_rows', 'num_cols'), ('num_rows', 'num_cols', 'depth')),
                shape=([None] * 2, [None] * 3)
            ),
            NWBDatasetSpec(
                name='pixel_roi',
                doc=("ROIs designated as a list specifying the pixel ([x1, y1], [x2, y2], …) or voxel (["
                     "x1, y1, z1], [x2, y2, z2], …) of each ROI, where the items in the list are the "
                     "coordinates of the center of the ROI. The size of each ROI is specified via the "
                     "required 'roi_size' parameter."),
                shape=([None] * 2, [None] * 3),
                quantity='?',
                # attributes=[
                #     roi_size
                # ]
            )
        ],
        groups=[
            psm
        ]
    )

    ########################################################################################################################
    ps = NWBGroupSpec(
        neurodata_type_def='PhotostimulationSeries',
        neurodata_type_inc='TimeSeries',
        doc=("TimeSeries object for photostimulus presentation. "),
        quantity='*',
        attributes=[
            stim_duration,
            NWBAttributeSpec(
                name='format',
                doc=("Format of data denoting stimulus presentation. Can be either 'interval' or 'series'."),
                dtype='text',
                required=True
            ),
            NWBAttributeSpec(
                name='epoch_length',
                doc=("Length of each epoch (in seconds)."),
                dtype='numeric',
                required=False
            )
        ],
        groups=[
            hp
        ]
    )

    ########################################################################################################################
    pt = NWBGroupSpec(
        neurodata_type_def='PhotostimulationTable',
        neurodata_type_inc='DynamicTable',
        doc=("Table to hold all of an experiment's PhotostimulationSeries objects."),
        quantity='?',
        datasets=[
            NWBDatasetSpec(
                name='series',
                doc=("PhotostimulationSeries object corresponding to the row."),
                neurodata_type_inc='VectorData',
                dtype=NWBRefSpec(target_type='PhotostimulationSeries', reftype='object')
            )
        ]
    )

    new_data_types = [slm, lsr, psm, hp, ps, pt]

    # export the spec to yaml files in the spec folder
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'spec'))
    export_spec(ns_builder, new_data_types, output_dir)
    print('Spec files generated. Please make sure to rerun `pip install .` to load the changes.')


if __name__ == '__main__':
    # usage: python create_extension_spec.py
    main()
