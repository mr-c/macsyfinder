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
import itertools
from macsypy.error import MacsypyError


class ComposedScore:

    def __init__(self, system, hit_tracker):
        self._system = system
        self._hit_tracker = hit_tracker
        self._sys_score = self._system.score
        self._overlapping_genes = None
        self._overlapping_length = None
        self._overlap()

    def _overlap(self):
        used_in_systems = {}
        for vh in self._system.hits:
            used_in_systems[vh] = [s.id for s in self._hit_tracker[vh.hit] if s.model.fqn != self._system.model.fqn]
        self._overlapping_genes = len(used_in_systems)
        self._overlapping_length = sum([1 for used_in in used_in_systems.values() for h in used_in])

    @property
    def system(self):
        return self._system

    @property
    def sys_score(self):
        return self.sys_score()


    @property
    def overlapping_genes(self):
        return self._overlapping_genes

    @property
    def overlapping_length(self):
        return self._overlapping_length


class BestSystemSelector:

    def __init__(self, systems, hit_tracker):
        models = {sys.model.fqn for sys in systems}
        if len(models) != 1:
            raise MacsypyError(f"Cannot build Score with system from different models: {','.join(models)}")
        self. systems = systems
        self.hit_tracker = hit_tracker

    def best_system(self):
        systems = sorted(self.systems, key=lambda s: - s.score)
        grouped = itertools.groupby(systems, key=lambda s: s.score)
        score, best_systems = next(grouped)
        best_systems = list(best_systems)
        if len(best_systems) > 1:
            best_score = [ComposedScore(sys, self.hit_tracker) for sys in best_systems]
            criterion = lambda cs: cs.overlapping_genes
            best_score = itertools.groupby(sorted(best_score, key=criterion), key=criterion)
            _, best_score = next(best_score)
            best_score = list(best_score)
            if len(best_score) > 1:
                criterion = lambda cs: cs.overlapping_length
                best_score = itertools.groupby(sorted(best_score, key=criterion), key=criterion)
                _, best_score = next(best_score)
                return [cs.system for cs in best_score]
            else:
                return [cs.system for cs in best_score]
        else:
            return best_systems

