#!/usr/bin/env python
# -*- coding: utf-8 -*-

################################################################################
# MacSyFinder - Detection of macromolecular systems in protein datasets        #
#               using systems modelling and similarity search.                 #
# Authors: Sophie Abby, Bertrand Néron                                         #
# Copyright © 2014  Institut Pasteur, Paris.                                   #
# See the COPYRIGHT file for details                                           #
#                                                                              #
# MacsyFinder is distributed under the terms of the GNU General Public License #
# (GPLv3). See the COPYING file for details.                                   #
################################################################################


import sys
import os
import argparse
import logging

try:
    from macsypy.config import Config, ConfigLight
except ImportError as err:
    msg = "Cannot import macsypy, check your installation or your MACSY_HOME variable : {0!s}".format(err)
    sys.exit(msg)

from operator import attrgetter # To be used with "sorted"
from textwrap import dedent

from macsypy.registries import ModelRegistry
from macsypy.system_parser import SystemParser
from macsypy.search_genes import search_genes
from macsypy.database import Indexes
from macsypy.search_systems import search_systems
from macsypy.system import system_bank
from macsypy.gene import gene_bank


def models_to_detect(cmd_args, cfg, model_registry):
    """
    :param cmd_args: the result of commandline parsing.
    :type cmd_args: class:`argparse.Namespace` object.
    :param cfg: the configuration of this run.
    :type cfg: :class:`macsypy.config.Config object.
    :param model_registry: the models registry for this run.
    :type model_registry: :class:`macsypy.registries.ModelRegistry` object.
    :return: list of system to launch a detection on.
    :rtype: list of :class:`macsypy.system.System` objects
    :raise KeyError: if a model name provided in cmd_args is not in model_registry.
    """
    if cfg.old_data_organization():
        if 'all' in [m.lower() for m in args.systems]:
            model = model_registry.models()[0]
            model_name = model.name
            models_name_to_detect = ['{}/{}'.format(model_name, d.name) for d in model.get_all_definitions()]
        else:
            model_name = os.path.basename(os.path.normpath(cfg.def_dir))
            models_name_to_detect = ['{}/{}'.format(model_name, d) for d in cmd_args.systems]
    else:
        models_name_to_detect = []
        for group_of_defs in cmd_args.models:
            root = group_of_defs[0]
            definitions = group_of_defs[1:]

            model = model_registry[root.split('/')[0]]
            if 'all' in [d.lower() for d in definitions]:
                if root == model.name:
                    root = None
                def_loc = model.get_all_definitions(root_def_name=root)
                models_name_to_detect.extend([d.fqn for d in def_loc])
            else:
                models_name_to_detect.extend(['{}/{}'.format(root, one_def) for one_def in definitions])
    return models_name_to_detect


def get_version_message():
    import macsypy
    version = macsypy.__version__
    vers_msg = """Macsyfinder {0}
Python {1}

MacsyFinder is distributed under the terms of the GNU General Public License (GPLv3).
See the COPYING file for details.

If you use this software please cite:
Abby SS, Néron B, Ménager H, Touchon M, Rocha EPC (2014)
MacSyFinder: A Program to Mine Genomes for Molecular Systems with an Application to CRISPR-Cas Systems.
PLoS ONE 9(10): e110726. doi:10.1371/journal.pone.0110726""".format(version, sys.version)
    return vers_msg


def parse_args(args):
    parser = argparse.ArgumentParser(
        epilog="For more details, visit the MacSyFinder website and see the MacSyFinder documentation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=dedent('''



         *            *               *                   *
    *           *               *   *   *  *    **                *   *
      **     *    *   *  *     *                    *               *
        __  __  *              ____ *        *  *  *    **     *
    || |  \/  | __ _  ___  || / ___| _   _  ||   ___ _         _        *
    || | |\/| |/ _` |/ __| || \___ \| | | | ||  | __(_)_ _  __| |___ _ _
    || | |  | | (_| | (__  ||  ___) | |_| | ||  | _|| | ' \/ _` / -_) '_|
    || |_|  |_|\__,_|\___| || |____/ \__, | ||  |_| |_|_||_\__,_\___|_|
               *             *       |___/         *                   *
     *      *   * *     *   **         *   *  *           *
      *      *         *        *    *              *
                 *                           *  *           *     *


    MacSyFinder - Detection of macromolecular systems in protein datasets 
    using systems modelling and similarity search.  
    '''))

    # , formatter_class=argparse.RawDescriptionHelpFormatter)
    # , formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("systems",
                        nargs='*',
                        help="The list (separated by spaces) of models to detect  \
                             To detect all the protein secretion systems and related appendages:\
                             set to \"all\" (case insensitive).\
                             Otherwise, a single or multiple models can be specified. For example: \"T2SS T4P\". \
                             This the old way to specified systems to detect. It is better to install models in macsyfinder \
                             or use the --models-dir dir_options (for more information about data organization see \
                             (http://macsyfinder.readthedocs.org/en/latest/#) ")

    parser.add_argument("-m", "--models",
                        action='append',
                        dest='models',
                        nargs='*',
                        default=None,
                        help='TODO bla-bla')

    genome_options = parser.add_argument_group(title="Input dataset options")
    genome_options.add_argument("--sequence-db",
                                action='store',
                                dest='sequence_db',
                                default=None,
                                help="Path to the sequence dataset in fasta format.")

    genome_options.add_argument("--db-type",
                                choices=['unordered_replicon', 'ordered_replicon', 'gembase', 'unordered'],
                                dest="db_type",
                                default=None,
                                help="The type of dataset to deal with. \"unordered_replicon\" corresponds\
                                     to a non-assembled genome,\"unordered\" to a metagenomic dataset,\
                                      \"ordered_replicon\" to an assembled genome, \
                                     and \"gembase\" to a set of replicons where sequence identifiers\
                                      follow this convention: \">RepliconName SequenceID\".")

    genome_options.add_argument("--replicon-topology",
                                choices=['linear', 'circular'],
                                dest="replicon_topology",
                                default=None,
                                help="The topology of the replicons \
                                (this option is meaningful only if the db_type is 'ordered_replicon' or 'gembase'. ")

    genome_options.add_argument("--topology-file",
                                dest="topology_file",
                                default=None,
                                help="Topology file path. The topology file allows to specify a topology \
                                     (linear or circular) for each replicon (this option is meaningful only if\
                                     the db_type is 'ordered_replicon' or 'gembase'.\
                                     A topology file is a tabular file with two columns: the 1st is the replicon name,\
                                     and the 2nd the corresponding topology:\n\"RepliconA\tlinear\" ")

    genome_options.add_argument("--idx",
                                action='store_true',
                                dest="build_indexes",
                                default=False,
                                help="Forces to build the indexes for the sequence dataset even \
                                     if they were previously computed and present at the dataset location (default = False)"
                                )

    system_options = parser.add_argument_group(title="Systems detection options")
    system_options.add_argument("--inter-gene-max-space",
                                action='append',
                                nargs=2,
                                dest='inter_gene_max_space',
                                default=None,
                                help="Co-localization criterion: maximum number of components non-matched by a\
                                     profile allowed between two matched components for them to be considered contiguous.\
                                     Option only meaningful for 'ordered' datasets.\
                                     The first value must match to a system, the second to a number of components.\
                                     This option can be repeated several times:\
                                     \n \"--inter-gene-max-space T2SS 12 --inter-gene-max-space Flagellum 20\""
                                )
    system_options.add_argument("--min-mandatory-genes-required",
                                action='append',
                                nargs=2,
                                dest='min_mandatory_genes_required',
                                default=None,
                                help="The minimal number of mandatory genes required for system assessment.\
                                     The first value must correspond to a system name, the second value to an integer.\
                                     This option can be repeated several times:\n\
                                     \"--min-mandatory-genes-required T2SS 15 --min-mandatory-genes-required Flagellum 10\""
                                )
    system_options.add_argument("--min-genes-required",
                                action='append',
                                nargs=2,
                                dest='min_genes_required',
                                default=None,
                                help="The minimal number of genes required for system assessment\
                                     (includes both 'mandatory' and 'accessory' components).\
                                     The first value must correspond to a system name, the second value to an integer.\
                                     This option can be repeated several times:\
                                     \n \"--min-genes-required T2SS 15 --min-genes-required Flagellum 10\""
                                )
    system_options.add_argument("--max-nb-genes",
                                action='append',
                                nargs=2,
                                dest='max_nb_genes',
                                default=None,
                                help="The maximal number of genes required for system assessment.\
                                     The first value must correspond to a system name, the second value to an integer.\
                                     This option can be repeated several times:\
                                     \n \"--max-nb-genes T2SS 5 --max-nb-genes Flagellum 10"
                                )
    system_options.add_argument("--multi-loci",
                                action='store',
                                dest='multi_loci',
                                default=None,
                                help="Allow the storage of multi-loci systems for the specified systems.\
                                The systems are specified as a comma separated list \
                                (--multi-loci sys1,sys2) default is False"
                                )

    hmmer_options = parser.add_argument_group(title="Options for Hmmer execution and hits filtering")
    hmmer_options.add_argument('--hmmer',
                               action='store',
                               dest='hmmer_exe',
                               default=None,
                               help='Path to the Hmmer program.')
    hmmer_options.add_argument('--index-db',
                               action='store',
                               dest='index_db_exe',
                               default=None,
                               help="The indexer to be used for Hmmer.\
                                    The value can be either 'makeblastdb' or 'formatdb' or the path to one of these binary\
                                    (default = makeblastb)")
    hmmer_options.add_argument('--e-value-search',
                               action='store',
                               dest='e_value_res',
                               type=float,
                               default=None,
                               help='Maximal e-value for hits to be reported during Hmmer search. (default = 1)')
    hmmer_options.add_argument('--i-evalue-select',
                               action='store',
                               dest='i_evalue_sel',
                               type=float,
                               default=None,
                               help='Maximal independent e-value for Hmmer hits to be selected for system detection.\
                                     (default = 0.001)')
    hmmer_options.add_argument('--coverage-profile',
                               action='store',
                               dest='coverage_profile',
                               type=float,
                               default=None,
                               help='Minimal profile coverage required in the hit alignment to allow\
                                    the hit selection for system detection. (default = 0.5)')

    dir_options = parser.add_argument_group(title="Path options", description=None)
    dir_options.add_argument('--models-dir',
                             action='store',
                             dest='models_dir',
                             default=None,
                             help='specify the path to the models if the models are not installed in the canonical place.\
                              It gather definitions (xml files) and hmm profiles in a specific\
                              structure. A directory with the name of the system with at least two directories\
                              "profiles" which contains all hmm profile for gene describe in definitions and\
                              "models" which contains either xml file of definitions or subdirectories\
                              to organize the system in subsystems.')
    dir_options.add_argument('-d', '--def-dir',
                             action='store',
                             dest='def_dir',
                             default=None,
                             help='Path to the systems definition files. (DEPRECATED see --models and --models-path options)')
    dir_options.add_argument('-p', '--profile-dir',
                             action='store',
                             dest='profile_dir',
                             default=None,
                             help='Path to the profiles directory. (DEPRECATED see --models and --models-path options)')

    dir_options.add_argument('-o', '--out-dir',
                             action='store',
                             dest='out_dir',
                             default=None,
                             help='Path to the directory where to store results.\
                             if out-dir is specified res-search-dir will be ignored.')
    dir_options.add_argument('-r', '--res-search-dir',
                             action='store',
                             dest='res_search_dir',
                             default=None,
                             help='Path to the directory where to store MacSyFinder search results directories\
                             (default current working directory).')
    dir_options.add_argument('--res-search-suffix',
                             action='store',
                             dest='res_search_suffix',
                             default=None,
                             help='The suffix to give to Hmmer raw output files.')
    dir_options.add_argument('--res-extract-suffix',
                             action='store',
                             dest='res_extract_suffix',
                             default=None,
                             help='The suffix to give to filtered hits output files.')
    dir_options.add_argument('--profile-suffix',
                             action='store',
                             dest='profile_suffix',
                             default=None,
                             help="The suffix of profile files. For each 'Gene' element, the corresponding profile is \
                                  searched in the 'profile_dir', in a file which name is based on the \
                                  Gene name + the profile suffix.\
                                  For instance, if the Gene is named 'gspG' and the suffix is '.hmm3',\
                                  then the profile should be placed at the specified location and be named 'gspG.hmm3'")

    general_options = parser.add_argument_group(title="General options", description=None)
    general_options.add_argument("-w", "--worker",
                                 action='store',
                                 dest='worker_nb',
                                 type=int,
                                 default=None,
                                 help="Number of workers to be used by MacSyFinder.\
                                      In the case the user wants to run MacSyFinder in a multi-thread mode.\
                                      (0 mean all cores will be used, default 1)")
    general_options.add_argument("-v", "--verbosity",
                                 action="count",
                                 dest="verbosity",
                                 default=0,
                                 help="Increases the verbosity level. There are 4 levels:\
                                       Error messages (default), Warning (-v), Info (-vv) and Debug.(-vvv)")
    general_options.add_argument("--version",
                                 action="version",
                                 dest="version",
                                 version=get_version_message()),
    general_options.add_argument("-l", "--list-models",
                                 action="store_true",
                                 dest="list_models",
                                 default=False,
                                 help="display the all models installed in generic location and quit.")
    general_options.add_argument("--log",
                                 action='store',
                                 dest='log_file',
                                 default=None,
                                 help="Path to the directory where to store the 'macsyfinder.log' log file.")
    general_options.add_argument("--config",
                                 action='store',
                                 dest='cfg_file',
                                 default=None,
                                 help="Path to a putative MacSyFinder configuration file to be used.")
    general_options.add_argument("--previous-run",
                                 action='store',
                                 dest='previous_run',
                                 default=None,
                                 help="""Path to a previous MacSyFinder run directory.
                                         It allows to skip the Hmmer search step on same dataset,
                                         as it uses previous run results and thus parameters regarding Hmmer detection.
                                         The configuration file from this previous run will be used.
                                         (conflict with options  --config, --sequence-db, --profile-suffix,
                                         --res-extract-suffix, --e-value-res, --db-type, --hmmer)""")
    general_options.add_argument("--relative-path",
                                 action='store_true',
                                 dest='relative_path',
                                 default=False,
                                 help=argparse.SUPPRESS)
    # 'relative-path' option help message (currently hidden)
    """
    Use relative paths instead of absolute paths. This option is used
    by developers to generate portable data set, as for example test 
    data set, which are used on many different machines (using
    previous-run option).
    """
    parsed_args = parser.parse_args()

    old_options = (args.def_dir, args.profile_dir, args.systems)
    new_options = (args.models_dir, args.models)

    if not args.systems and not args.models:
        parser.error("you MUST provided systems to search.")

    if not args.previous_run and not args.sequence_db:
        parser.error("argument --sequence-db is required.")

    if not args.previous_run and not args.db_type:
        parser.error("argument --db-type is required.")

    if args.systems and args.models:
        parser.error("""--models option is the new way to specify models to search.
        models as arguments is the old and DEPRECATED way to specify models.
        You cannot use the two ways in the same time.
        """)

    if any(old_options) and any(new_options):
        parser.error("""--models --models-dir options are the new way to specify models to search.
        --def-dir and --profile-dir is the old and DEPRECATED way to specify models.
        You cannot use the two ways in the same time.
        """)


    return parsed_args


def list_models(args):
    config = ConfigLight(previous_run=args.previous_run,
                         cfg_file=args.cfg_file,
                         profile_suffix=args.profile_suffix,
                         )
    registry = ModelRegistry(config)
    return str(registry)


def search_systems(args, logger, log_level):

    config = Config(previous_run=args.previous_run,
                    cfg_file=args.cfg_file,
                    sequence_db=args.sequence_db,
                    db_type=args.db_type,
                    build_indexes=args.build_indexes,
                    replicon_topology=args.replicon_topology,
                    topology_file=args.topology_file,
                    inter_gene_max_space=args.inter_gene_max_space,
                    min_mandatory_genes_required=args.min_mandatory_genes_required,
                    min_genes_required=args.min_genes_required,
                    max_nb_genes=args.max_nb_genes,
                    multi_loci=args.multi_loci,
                    hmmer_exe=args.hmmer_exe,
                    index_db_exe=args.index_db_exe,
                    e_value_res=args.e_value_res,
                    i_evalue_sel=args.i_evalue_sel,
                    coverage_profile=args.coverage_profile,
                    def_dir=args.def_dir,
                    models_dir=args.models_dir,
                    res_search_dir=args.res_search_dir,
                    out_dir=args.out_dir,
                    res_search_suffix=args.res_search_suffix,
                    profile_dir=args.profile_dir,
                    profile_suffix=args.profile_suffix,
                    res_extract_suffix=args.res_extract_suffix,
                    log_level=log_level,
                    log_file=args.log_file,
                    worker_nb=args.worker_nb,
                    relative_path=args.relative_path
                    )

    config.save(config.working_dir)

    registry = ModelRegistry(config)
    # build indexes
    idx = Indexes(config)
    idx.build(force=config.build_indexes)

    # create models
    parser = SystemParser(config, system_bank, gene_bank)
    try:
        models_name_to_detect = models_to_detect(args, config, registry)
    except KeyError as err:
        sys.exit("macsyfinder: {}".format(str(err).strip('"')))

    parser.parse(models_name_to_detect)

    out_logger = logging.getLogger('macsyfinder.out')
    out_logger.info("MacSyFinder's results will be stored in {0}".format(config.working_dir))
    out_logger.info("Analysis launched on {0} for system(s):".format(config.sequence_db))

    for s in models_name_to_detect:
        out_logger.info("\t- {}".format(s))

    models_to_detect = [system_bank[model_fqn] for model_fqn in models_name_to_detect]
    all_genes = []
    for system in models_to_detect:
        genes = system.mandatory_genes + system.accessory_genes + system.forbidden_genes
        # Exchangeable homologs/analogs are also added cause they can "replace" an important gene...
        ex_genes = []

        for g in genes:
            if g.exchangeable:
                h_s = g.get_homologs()
                ex_genes += h_s
                a_s = g.get_analogs()
                ex_genes += a_s
        all_genes += (genes + ex_genes)
    #############################################
    # this part of code is executed in parallel
    #############################################
    try:
        all_reports = search_genes(all_genes, config)
    except Exception as err:
        sys.exit(str(err))
    #############################################
    # end of parallel code
    #############################################
    all_hits = [hit for subl in [report.hits for report in all_reports] for hit in subl]

    if len(all_hits) > 0:
        # It's important to keep this sorting to have in last  all_hits version
        # the hits with the same replicon_name and position sorted by score
        # the best score in first
        all_hits = sorted(all_hits, key=attrgetter('score'), reverse=True)
        all_hits = sorted(all_hits, key=attrgetter('replicon_name', 'position'))
        models_to_detect = sorted(models_to_detect, key=attrgetter('name'))
        search_systems(all_hits, models_to_detect, config)
    else:
        logger.info("No hits found in this dataset.")



def main(args=None, loglevel=None):
    """
    main entry point to integron_finder

    :param str args: the arguments passed on the command line
    :param loglevel: the output verbosity
    :type loglevel: a positive int or a string among 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    """
    args = sys.argv[1:] if args is None else args
    parsed_args = parse_args(args)

    sh_formatter = logging.Formatter("%(levelname)-8s : L %(lineno)d : %(message)s")
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(sh_formatter)

    if args.verbosity == 0:
        log_level = None
    elif args.verbosity == 1:
        log_level = logging.WARNING
    elif args.verbosity == 2:
        log_level = logging.INFO
    elif args.verbosity == 3:
        log_level = logging.DEBUG
    else:
        log_level = logging.NOTSET

    logger = logging.getLogger('macsyfinder')

    if args.list_models:
        print(list_models(parsed_args), file=sys.stderr)
        sys.exit(0)
    else:
        search_systems(parsed_args, logger, log_level)
    logger.debug("END")

if __name__ == "__main__":

    main()












