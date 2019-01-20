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

import os
import shutil
from argparse import Namespace
from configparser import ParsingError
import tempfile
from time import strftime

from macsypy.config import MacsyDefaults, Config

from tests import MacsyTest


class TestConfig(MacsyTest):

    def setUp(self):
        self.defaults = MacsyDefaults()
        self.parsed_args = Namespace()


    def test_str_2_tuple(self):
        s = 'Flagellum 12 t4ss 13'
        expected = [('Flagellum', '12'), ('t4ss', '13')]
        cfg = Config(self.defaults, self.parsed_args)
        self.assertListEqual(cfg._str_2_tuple(s), expected)

        with self.assertRaises(ValueError) as ctx:
            s = 'Flagellum 12 t4ss'
            cfg._str_2_tuple(s)
        self.assertEqual(str(ctx.exception),
                         "You must provide a list of model name and value separated by spaces: {}".format(s))


    def test_config_file_2_dict(self):
        cfg = Config(self.defaults, self.parsed_args)
        res = cfg._config_file_2_dict(self.defaults, ['nimportnaoik'])
        self.assertDictEqual({}, res)

        cfg_file = self.find_data(os.path.join('conf_files', 'macsy_test_conf.conf'))
        res = cfg._config_file_2_dict(self.defaults, [cfg_file])
        expected = {'db_type': 'gembase',
                    'inter_gene_max_space': 'T2SS 2 Flagellum 4',
                    'min_mandatory_genes_required': 'T2SS 5 Flagellum 9',
                    'replicon_topology': 'circular',
                    'sequence_db': '/path/to/sequence/bank/fasta_file',
                    'topology_file': '/the/path/to/the/topology/to/use'}
        self.assertDictEqual(expected, res)

        bad_cfg_file = self.find_data(os.path.join('conf_files', 'macsy_test_bad_conf.conf'))
        with self.assertRaises(ParsingError):
            cfg._config_file_2_dict(self.defaults, [bad_cfg_file])


    def test_Config(self):
        cfg = Config(self.defaults, self.parsed_args)
        methods_needing_args = {'inter_gene_max_space': None,
                                'max_nb_genes': None,
                                'min_genes_required': None,
                                'min_mandatory_genes_required': None,
                                'multi_loci': None
                                }

        for opt, val in self.defaults.items():
            if opt == 'out_dir':
                self.assertEqual(cfg.out_dir(),
                                 os.path.join(cfg.res_search_dir(), "macsyfinder-{}".format(strftime("%Y%m%d_%H-%M-%S")))
                                 )
            elif opt == 'multi_loci':
                self.assertFalse(cfg.multi_loci('whatever'))
            elif opt in methods_needing_args:
                self.assertEqual(getattr(cfg, opt)('whatever'), val,
                                 msg="test of '{}' failed : expected{} !=  got {}".format(opt,
                                                                                          getattr(cfg, opt)('whatever'),
                                                                                          val
                                                                                          ))
            else:
                self.assertEqual(getattr(cfg, opt)(), val,
                                 msg="test of '{}' failed : expected{} !=  got {}".format(opt,
                                                                                          getattr(cfg, opt)(),
                                                                                          val
                                                                                          ))


    def test_Config_file(self):
        methods_needing_args = {'inter_gene_max_space': [('Flagellum', 4), ('T2SS', 2)],
                                'max_nb_genes':  [('Flagellum', 6), ('T3SS', 3)],
                                'min_genes_required': [('Flagellum', 8), ('T4SS', 4)],
                                'min_mandatory_genes_required': [('Flagellum', 12), ('T6SS', 6)],
                                'multi_loci': {'Flagellum', 'T4SS'}
                                }

        self.parsed_args.cfg_file = self.find_data(os.path.join('conf_files', 'macsy_models.conf'))
        cfg = Config(self.defaults, self.parsed_args)

        expected_values = {k: v for k, v in self.defaults.items()}
        expected_values['cfg_file'] = self.parsed_args.cfg_file
        expected_values.update(methods_needing_args)

        for opt, val in expected_values.items():
            if opt == 'out_dir':
                self.assertEqual(cfg.out_dir(),
                                 os.path.join(cfg.res_search_dir(),
                                              "macsyfinder-{}".format(strftime("%Y%m%d_%H-%M-%S")))
                                 )
            elif opt == 'multi_loci':
                self.assertTrue(cfg.multi_loci('Flagellum'))
                self.assertTrue(cfg.multi_loci('T4SS'))
                self.assertFalse(cfg.multi_loci('T6SS'))
            elif opt in methods_needing_args:
                for model, genes in expected_values[opt]:
                    self.assertEqual(getattr(cfg, opt)(model), genes)
            else:
                self.assertEqual(getattr(cfg, opt)(), val)

    def test_Config_default_conf_file(self):
        methods_needing_args = {'inter_gene_max_space': [('Flagellum', 4), ('T2SS', 2)],
                                'max_nb_genes':  [('Flagellum', 6), ('T3SS', 3)],
                                'min_genes_required': [('Flagellum', 8), ('T4SS', 4)],
                                'min_mandatory_genes_required': [('Flagellum', 12), ('T6SS', 6)],
                                'multi_loci': {'Flagellum', 'T4SS'}
                                }
        with tempfile.TemporaryDirectory() as tmpdirname:
            ori_conf_file = self.find_data(os.path.join('conf_files', 'macsy_models.conf'))
            dest_conf_file = os.path.join(tmpdirname, 'macsyfinder.conf')
            shutil.copy(ori_conf_file, dest_conf_file)
            import macsypy.config
            macsyconf = macsypy.config.__MACSY_CONF__
            macsypy.config.__MACSY_CONF__ = tmpdirname
            try:
                cfg = Config(self.defaults, self.parsed_args)

                expected_values = {k: v for k, v in self.defaults.items()}
                expected_values.update(methods_needing_args)
                for opt, val in expected_values.items():
                    if opt == 'out_dir':
                        self.assertEqual(cfg.out_dir(),
                                         os.path.join(cfg.res_search_dir(),
                                                      "macsyfinder-{}".format(strftime("%Y%m%d_%H-%M-%S")))
                                         )
                    elif opt == 'multi_loci':
                        self.assertTrue(cfg.multi_loci('Flagellum'))
                        self.assertTrue(cfg.multi_loci('T4SS'))
                        self.assertFalse(cfg.multi_loci('T6SS'))
                    elif opt in methods_needing_args:
                        for model, genes in expected_values[opt]:
                            self.assertEqual(getattr(cfg, opt)(model), genes)
                    else:
                        self.assertEqual(getattr(cfg, opt)(), val)
            finally:
                macsypy.config.__MACSY_CONF__ = macsyconf


    def test_Config_args(self):
        methods_needing_args = {'inter_gene_max_space': [('Flagellum', '14'), ('T2SS', '12')],
                                'max_nb_genes': [('Flagellum', '16'), ('T3SS', '13')],
                                'min_genes_required': [('Flagellum', '18'), ('T4SS', '14')],
                                'min_mandatory_genes_required': [('Flagellum', '22'), ('T6SS', '16')],
                                'multi_loci': 'Flagellum, T4SS',
                                }
        for opt, value in methods_needing_args.items():
            setattr(self.parsed_args, opt, value)

        simple_opt = {'hmmer': 'foo',
                      'i_evalue_sel': 20,
                      'replicon_topology': 'linear',
                      'db_type': 'gembase',
                      'sequence_db': self.find_data(os.path.join('base', 'test_aesu.fa')),
                      'topology_file': __file__  # test only the existence of a file
                      }

        for opt, val in simple_opt.items():
            setattr(self.parsed_args, opt, val)

        cfg = Config(self.defaults, self.parsed_args)

        expected_values = {k: v for k, v in self.defaults.items()}
        expected_values.update(methods_needing_args)
        expected_values.update(simple_opt)
        for opt, val in expected_values.items():
            if opt == 'out_dir':
                self.assertEqual(cfg.out_dir(),
                                 os.path.join(cfg.res_search_dir(), "macsyfinder-{}".format(strftime("%Y%m%d_%H-%M-%S")))
                                 )
            elif opt == 'multi_loci':
                self.assertTrue(cfg.multi_loci('Flagellum'))
                self.assertTrue(cfg.multi_loci('T4SS'))
                self.assertFalse(cfg.multi_loci('T6SS'))
            elif opt in methods_needing_args:
                for model, genes in expected_values[opt]:
                    self.assertEqual(getattr(cfg, opt)(model), int(genes))

            else:
                self.assertEqual(getattr(cfg, opt)(), val,
                                 msg="{} failed: expected: val '{}' != got '{}'".format(opt, val, getattr(cfg, opt)()))

    def test_Config_file_n_args(self):
        cfg_needing_args = {'inter_gene_max_space': [('Flagellum', '4'), ('T2SS', '2')],
                                'max_nb_genes': [('Flagellum', '6'), ('T3SS', '3')],
                                'min_genes_required': [('Flagellum', '8'), ('T4SS', '4')],
                                'min_mandatory_genes_required': [('Flagellum', '12'), ('T6SS', '6')],
                                'multi_loci': 'Flagellum, T4SS',
                                }

        self.parsed_args.cfg_file = self.find_data(os.path.join('conf_files', 'macsy_models.conf'))
        expected_values = {k: v for k, v in self.defaults.items()}
        expected_values['cfg_file'] = self.parsed_args.cfg_file
        expected_values.update(cfg_needing_args)

        cmd_needing_args = {'min_genes_required': [('Flagellum', 18), ('T4SS', 14)],
                            'min_mandatory_genes_required': [('Flagellum', 22), ('T6SS', 16)],
                            }
        for opt, value in cmd_needing_args.items():
            setattr(self.parsed_args, opt, ' '.join(["{} {}".format(m, v) for m, v in value]))

        simple_opt = {'hmmer': 'foo',
                      'i_evalue_sel': 20,
                      'db_type': 'gembase'}
        for opt, val in simple_opt.items():
            setattr(self.parsed_args, opt, val)

        cfg = Config(self.defaults, self.parsed_args)

        expected_values.update(cmd_needing_args)
        expected_values.update(simple_opt)

        for opt, exp_val in expected_values.items():
            if opt == 'out_dir':
                self.assertEqual(cfg.out_dir(),
                                 os.path.join(cfg.res_search_dir(), "macsyfinder-{}".format(strftime("%Y%m%d_%H-%M-%S")))
                                 )
            elif opt == 'multi_loci':
                self.assertTrue(cfg.multi_loci('Flagellum'))
                self.assertTrue(cfg.multi_loci('T4SS'))
                self.assertFalse(cfg.multi_loci('T6SS'))
            elif opt in cfg_needing_args:
                for model, val in expected_values[opt]:
                    self.assertEqual(getattr(cfg, opt)(model), int(val))

            else:
                self.assertEqual(getattr(cfg, opt)(), exp_val)


    def test_bad_values(self):
        invalid_syntax = {'inter_gene_max_space': 'Flagellum 4 2',
                          'max_nb_genes': 'Flagellum T3SS 3',
                          'min_genes_required': 'Flagellum T4SS 4',
                          'min_mandatory_genes_required': '12 T6SS 6',
                          }

        for opt, val in invalid_syntax.items():
            args = Namespace()
            setattr(args, opt, val)
            with self.assertRaises(ValueError) as ctx:
                Config(self.defaults, args)
            self.assertEqual(str(ctx.exception), "Invalid syntax for '{}': You must provide a list of model name "
                                                 "and value separated by spaces: {}.".format(opt, val))

        int_error = {'inter_gene_max_space': 'Flagellum 4.2 T2SS 2',
                     'max_nb_genes': 'Flagellum 4 T3SS FOO',
                     'min_genes_required': 'Flagellum FOO T4SS 4',
                     'min_mandatory_genes_required': 'Flagellum 12 T6SS 6.4',
                     }

        for opt, val in int_error.items():
            args = Namespace()
            setattr(args, opt, val)
            with self.assertRaises(ValueError):
                Config(self.defaults, args)


    def test_bad_db_type(self):
        self.parsed_args.db_type = "FOO"
        with self.assertRaises(ValueError) as ctx:
            Config(self.defaults, self.parsed_args)
        self.assertEqual(str(ctx.exception),
                         "db_type as unauthorized value : 'FOO'.")

    def test_bad_topology(self):
        self.parsed_args.replicon_topology = "FOO"
        with self.assertRaises(ValueError) as ctx:
            Config(self.defaults, self.parsed_args)
        self.assertEqual(str(ctx.exception),
                         "replicon_topology as unauthorized value : 'FOO'.")

    def test_bad_topology_file(self):
        self.parsed_args.topology_file = "FOO"
        with self.assertRaises(ValueError) as ctx:
            Config(self.defaults, self.parsed_args)
        self.assertEqual(str(ctx.exception),
                         "topology_file 'FOO' does not exists or is not a file.")


    def test_bad_sequence_db(self):
        self.parsed_args.sequence_db = "FOO"
        with self.assertRaises(ValueError) as ctx:
            Config(self.defaults, self.parsed_args)
        self.assertEqual(str(ctx.exception),
                         "sequence_db 'FOO' does not exists or is not a file.")


    def test_bad_models_dir(self):
        self.parsed_args.models_dir = "FOO"
        with self.assertRaises(ValueError) as ctx:
            Config(self.defaults, self.parsed_args)
        self.assertEqual(str(ctx.exception),
                         "models_dir 'FOO' does not exists or is not a directory.")

    def test_save(self):
        self.parsed_args.max_nb_genes = [['T2SS', 5], ['Flagelum', 12]]
        self.parsed_args.multi_loci = 'T2SS,Flagelum'
        self.parsed_args.models = [['set_1', 'T9SS', 'T3SS', 'T4SS_typeI']]
        cfg = Config(self.defaults, self.parsed_args)
        expected = {k: v for k, v in cfg._options.items() if v}
        expected['max_nb_genes'] = 'T2SS 5 Flagelum 12'
        expected['multi_loci'] = {'T2SS', 'Flagelum'}
        expected['models'] = [('set_1', 'T9SS, T3SS, T4SS_typeI')]
        with tempfile.TemporaryDirectory() as tmpdirname:
            cfg_path = os.path.join(tmpdirname, 'macsyfinder.conf')
            cfg.save(path_or_buf=cfg_path)
            saved_opt = cfg._config_file_2_dict(self.defaults, [cfg_path])
            # the order of model_fqn is not guarantee
            saved_opt['multi_loci'] = {v for v in [v.strip() for v in saved_opt['multi_loci'].split(',')] if v}
            self.assertDictEqual(saved_opt, expected)

    def test_out_dir(self):
        cfg = Config(self.defaults, self.parsed_args)
        self.assertEqual(cfg.out_dir(),
                         os.path.join(cfg.res_search_dir(), "macsyfinder-{}".format(strftime("%Y%m%d_%H-%M-%S")))
                         )
        self.parsed_args.out_dir = 'foo'
        cfg = Config(self.defaults, self.parsed_args)
        self.assertEqual(cfg.out_dir(), 'foo')

    def test_working_dir(self):
        cfg = Config(self.defaults, self.parsed_args)
        self.assertEqual(cfg.out_dir(), cfg.working_dir())