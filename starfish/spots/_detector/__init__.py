import argparse
import os

from starfish._stack import ImageStack
from starfish.pipeline.pipelinecomponent import PipelineComponent
from starfish.util.argparse import FsExistsType
from starfish.constants import Indices
from . import _base
from . import gaussian
from . import local_max_peak_finder
from . import pixel_spot_detector


class SpotFinder(PipelineComponent):

    spot_finder_group: argparse.ArgumentParser

    @classmethod
    def implementing_algorithms(cls):
        return _base.SpotFinderAlgorithmBase.__subclasses__()

    @classmethod
    def add_to_parser(cls, subparsers):
        """Adds the spot finder component to the CLI argument parser."""
        spot_finder_group = subparsers.add_parser("detect_spots")
        spot_finder_group.add_argument("-i", "--input", type=FsExistsType(), required=True)
        spot_finder_group.add_argument("-o", "--output", required=True)
        spot_finder_group.add_argument(
            "--blobs-stack", default=None, required=False,
            help=(
                'ImageStack that contains the blobs. Will be max-projected across imaging round '
                'and channel to produce the blobs_image'
            )
        )
        spot_finder_group.add_argument(
            "--reference-image-from-max-projection", default=False, action='store_true',
            help=(
                'Construct a reference image by max projecting imaging rounds and channels. Spots '
                'are found in this image and then measured across all images in the input stack.'
            )
        )
        spot_finder_group.set_defaults(starfish_command=SpotFinder._cli)
        spot_finder_subparsers = spot_finder_group.add_subparsers(
            dest="spot_finder_algorithm_class")

        for algorithm_cls in cls.algorithm_to_class_map().values():
            group_parser = spot_finder_subparsers.add_parser(algorithm_cls.get_algorithm_name())
            group_parser.set_defaults(spot_finder_algorithm_class=algorithm_cls)
            algorithm_cls.add_arguments(group_parser)

        cls.spot_finder_group = spot_finder_group

    @classmethod
    def _cli(cls, args, print_help=False):
        """Runs the spot finder component based on parsed arguments."""

        if args.spot_finder_algorithm_class is None or print_help:
            cls.spot_finder_group.print_help()
            cls.spot_finder_group.exit(status=2)

        print('Detecting Spots ...')
        image_stack = ImageStack.from_path_or_url(args.input)
        if args.blobs_stack is not None:
            blobs_stack = ImageStack.from_path_or_url(args.blobs_stack)  # type: ignore
            blobs_image = blobs_stack.max_proj(Indices.ROUND, Indices.CH)
        else:
            blobs_image = None
        instance = args.spot_finder_algorithm_class(**vars(args))
        intensities = instance.find(
            image_stack,
            blobs_image=blobs_image,
            reference_image_from_max_projection=args.reference_image_from_max_projection
        )
        intensities.save(os.path.join(args.output, 'spots.nc'))