#########################################################################
# MacSyFinder - Detection of macromolecular systems in protein dataset  #
#               using systems modelling and similarity search.          #
# Authors: Sophie Abby, Bertrand Neron                                  #
# Copyright (c) 2014-2020  Institut Pasteur (Paris) and CNRS.           #
# See the COPYRIGHT file for details                                    #
#                                                                       #
# This file is part of MacSyFinder package.                             #
#                                                                       #
# MacSyFinder is free software: you can redistribute it and/or modify   #
# it under the terms of the GNU General Public License as published by  #
# the Free Software Foundation, either version 3 of the License, or     #
# (at your option) any later version.                                   #
#                                                                       #
# MacSyFinder is distributed in the hope that it will be useful,        #
# but WITHOUT ANY WARRANTY; without even the implied warranty of        #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the          #
# GNU General Public License for more details .                         #
#                                                                       #
# You should have received a copy of the GNU General Public License     #
# along with MacSyFinder (COPYING).                                     #
# If not, see <https://www.gnu.org/licenses/>.                          #
#########################################################################


import os
import shutil
import tempfile
import argparse

from macsypy.profile import ProfileFactory, Profile
from macsypy.gene import Gene
from macsypy.model import Model
from macsypy.config import Config, MacsyDefaults
from macsypy.registries import ModelLocation
from macsypy.error import MacsypyError
from tests import MacsyTest


class TestProfileFactory(MacsyTest):

    def setUp(self):
        args = argparse.Namespace()
        args.sequence_db = self.find_data("base", "test_base.fa")
        args.db_type = 'gembase'
        args.models_dir = self.find_data('models')
        args.res_search_dir = tempfile.gettempdir()
        args.log_level = 30
        self.cfg = Config(MacsyDefaults(), args)

        self.model_name = 'foo'
        self.models_location = ModelLocation(path=os.path.join(args.models_dir, self.model_name))
        self.profile_factory = ProfileFactory(self.cfg)

    def tearDown(self):
        try:
            shutil.rmtree(self.cfg.working_dir)
        except:
            pass


    def test_get_profile(self):
        system_foo = Model("foo", 10)
        gene_name = 'sctJ_FLG'
        gene = Gene(self.profile_factory, gene_name, system_foo, self.models_location)
        profile = self.profile_factory.get_profile(gene, self.models_location)
        self.assertTrue(isinstance(profile, Profile))
        self.assertEqual(profile.gene.name, gene_name)


    def test_get_uniq_object(self):
        system_foo = Model("foo", 10)
        gene = Gene(self.profile_factory, 'sctJ_FLG', system_foo, self.models_location)
        profile1 = self.profile_factory.get_profile(gene, self.models_location)
        profile2 = self.profile_factory.get_profile(gene, self.models_location)
        self.assertEqual(profile1, profile2)


    def test_unknow_profile(self):
        system_foo = Model("foo", 10)
        gene = Gene(self.profile_factory, 'sctJ_FLG', system_foo, self.models_location)
        gene.name = "foo"
        self.assertRaises(MacsypyError, self.profile_factory.get_profile, gene, self.models_location)