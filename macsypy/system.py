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
import json
import statistics
from itertools import chain
import logging
_log = logging.getLogger(__name__)

from.gene import GeneStatus
from .cluster import Cluster, RejectedClusters
from .hit import ValidHit


# la liste des clusters a fournir est a generer avant match
# si len(clusters) = 1 single_loci
# si len(clusters) > 1 multi_loci
# il faut genegerer la liste de toutes les combinaisons
# et appeler cette fonction pour chaqu'une entre elles
# from itertools import combinations

# combinations('ABCD', 1) => inutile mais generique => single_loucs
# combinations('ABCD', 2) => multi_locus a ne faire que si model.multi_locus= True
# combinations('ABCD', 3)
# combinations('ABCD', len("ABCD")) => inutile mais generique => recheche parmis tous les clusters


def match(clusters, model):
    """
    Check a set of clusters fill model constraints.
    If yes create a :class:`macsypy.system.PutativeSystem` otherwise create
    a :class:`macsypy.cluster.RejectedClusters`.

    :param clusters: The list of cluster to check if fit the model
    :type clusters: list of :class:`macsypy.cluster.Cluster` objects
    :param model:  The model to consider
    :type model: :class:`macsypy.model.Model` object
    :return: either a System or a RejectedClusters
    :rtype: :class:`macsypy.system.System` or :class:`macsypy.cluster.RejectedClusters` object
    """
    def create_exchangeable_map(genes):
        """
        create a map between an exchangeable (homolog or analog) gene name and it's gene ref

        :param genes: The genes to get the homologs or analogs
        :type genes: list of :class:`macsypy.gene.Gene` objects
        :rtype: a dict with keys are the homolog_or analog gene_name the reference gene name
        """
        map = {}
        for gene in genes:
            if gene.exchangeable:
                for ex_gene in itertools.chain(gene.get_homologs(), gene.get_analogs()):
                    map[ex_gene.name] = gene
        return map

    # init my structures to count gene occurrences
    mandatory_counter = {g.name: 0 for g in model.mandatory_genes}
    exchangeable_mandatory = create_exchangeable_map(model.mandatory_genes)

    accessory_counter = {g.name: 0 for g in model.accessory_genes}
    exchangeable_accessory = create_exchangeable_map(model.accessory_genes)

    forbidden_counter = {g.name: 0 for g in model.forbidden_genes}
    exchangeable_forbidden = create_exchangeable_map(model.forbidden_genes)

    neutral_counter = {g.name: 0 for g in model.neutral_genes}
    exchangeable_neutral = create_exchangeable_map(model.neutral_genes)

    # count the hits
    # and track for each hit for which gene it counts for
    valid_clusters = []
    forbidden_hits = []
    for cluster in clusters:
        valid_hits = []
        for hit in cluster.hits:
            gene_name = hit.gene.name
            if gene_name in mandatory_counter:
                mandatory_counter[hit.gene.name] += 1
                valid_hits.append(ValidHit(hit, hit.gene, GeneStatus.MANDATORY))
            elif gene_name in exchangeable_mandatory:
                gene_ref = exchangeable_mandatory[gene_name]
                mandatory_counter[gene_ref.name] += 1
                valid_hits.append(ValidHit(hit, gene_ref, GeneStatus.MANDATORY))
            elif gene_name in accessory_counter:
                accessory_counter[gene_name] += 1
                valid_hits.append(ValidHit(hit, hit.gene, GeneStatus.ACCESSORY))
            elif gene_name in exchangeable_accessory:
                gene_ref = exchangeable_accessory[gene_name]
                accessory_counter[gene_ref.name] += 1
                valid_hits.append(ValidHit(hit, gene_ref, GeneStatus.ACCESSORY))
            elif gene_name in neutral_counter:
                neutral_counter[gene_name] += 1
                valid_hits.append(ValidHit(hit, hit.gene, GeneStatus.NEUTRAL))
            elif gene_name in exchangeable_neutral:
                gene_ref = exchangeable_neutral[gene_name]
                neutral_counter[gene_ref.name] += 1
                valid_hits.append(ValidHit(hit, gene_ref, GeneStatus.NEUTRAL))
            elif gene_name in forbidden_counter:
                forbidden_counter[gene_name] += 1
                # valid_hits.append(ValidHit(hit, hit.gene, GeneStatus.FORBIDDEN))
                forbidden_hits.append(hit)
            elif gene_name in exchangeable_forbidden:
                gene_ref = exchangeable_forbidden[gene_name]
                forbidden_counter[gene_ref.name] += 1
                # valid_hits.append(ValidHit(hit, hit.gene.ref, GeneStatus.FORBIDDEN))
                forbidden_hits.append(hit)
        if valid_hits:
            valid_clusters.append(Cluster(valid_hits, model))

    # the count is finished
    # check if the quorum is reached
    # count how many different genes are represented in the clusters
    # the neutral genes belong to the cluster
    # but they do not count for the quorum
    mandatory_genes = [g for g, occ in mandatory_counter.items() if occ > 0]
    accessory_genes = [g for g, occ in accessory_counter.items() if occ > 0]
    neutral_genes = [g for g, occ in neutral_counter.items() if occ > 0]
    forbidden_genes = [g for g, occ in forbidden_counter.items() if occ > 0]
    _log.debug("#" * 50)
    _log.debug(f"mandatory_genes: {mandatory_genes}")
    _log.debug(f"accessory_genes: {accessory_genes}")
    _log.debug(f"neutral_genes: {neutral_genes}")
    _log.debug(f"forbidden_genes: {forbidden_genes}")

    reasons = []
    is_a_system = True
    if forbidden_genes:
        is_a_system = False
        msg = f"There is {len(forbidden_hits)} forbidden genes occurrence(s):" \
              f" {', '.join(h.gene.name for h in forbidden_hits)}"
        reasons.append(msg)
        _log.debug(msg)
    if len(mandatory_genes) < model.min_mandatory_genes_required:
        is_a_system = False
        msg = f'The quorum of mandatory genes required ({model.min_mandatory_genes_required}) is not reached: ' \
              f'{len(mandatory_genes)}'
        reasons.append(msg)
        _log.debug(msg)
    if len(accessory_genes) + len(mandatory_genes) < model.min_genes_required:
        is_a_system = False
        msg = f'The quorum of genes required ({model.min_genes_required}) is not reached:' \
              f' {len(accessory_genes) + len(mandatory_genes)}'
        reasons.append(msg)
        _log.debug(msg)

    if is_a_system:
        res = System(model, valid_clusters)
        _log.debug("is a system")
    else:
        reason = '\n'.join(reasons)
        res = RejectedClusters(model, clusters, reason)
    _log.debug("#" * 50)
    return res


class HitSystemTracker(dict):

    def __init__(self, systems):
        super(HitSystemTracker, self).__init__()
        for system in systems:
            v_hits = system.hits
            for v_hit in v_hits:
                hit = v_hit.hit
                if hit not in self:
                    self[hit] = set()
                self[hit].add(system)


class ClusterSystemTracker(dict):

    def __init__(self, systems):
        super(ClusterSystemTracker, self).__init__()
        for system in systems:
            clusters = system.clusters
            for clst in clusters:
                if clst not in self:
                    self[clst] = set()
                self[clst].add(system)


class System:

    _id = itertools.count(1)

    def __init__(self, model, clusters):
        """

        :param model:  The model which has ben used to build this system
        :type model: :class:`macsypy.model.Model` object
        :param clusters: The list of cluster that form this system
        :type clusters: list of :class:`macsypy.cluster.Cluster` objects
        """
        self._replicon_name = clusters[0].replicon_name
        self.id = f"{self._replicon_name}_{model.name}_{next(self._id)}"
        self.model = model
        self.clusters = clusters
        self._mandatory_occ = None
        self._accessory_occ = None
        self._neutral_occ = None
        self._count()

    def _count(self):
        """
        fill 2 structures one for mandatory the other for accessory
        each structure count how many hit for each gene
        :return: None
        """
        self._mandatory_occ = {g.name: [] for g in self.model.mandatory_genes}
        self._accessory_occ = {g.name: [] for g in self.model.accessory_genes}
        self._neutral_occ = {g.name: [] for g in self.model.neutral_genes}

        # all the hits are ValidHit
        for hit in self.hits:
            if hit.status == GeneStatus.MANDATORY:
                self._mandatory_occ[hit.gene_ref.name].append(hit)
            elif hit.status == GeneStatus.ACCESSORY:
                self._accessory_occ[hit.gene_ref.name].append(hit)
            elif hit.status == GeneStatus.NEUTRAL:
                self._neutral_occ[hit.gene_ref.name].append(hit)

    @property
    def replicon_name(self):
        return self._replicon_name

    @property
    def mandatory_occ(self):
        return {k: v for k, v in self._mandatory_occ.items()}

    @property
    def accessory_occ(self):
        return {k: v for k, v in self._accessory_occ.items()}

    @property
    def neutral_occ(self):
        return {k: v for k, v in self._neutral_occ.items()}

    @property
    def wholeness(self):
        """

        :return:
        """
        # model completude
        # the neutral hit do not participate to the model completude
        score = sum([1 for hits in chain(self._mandatory_occ.values(), self._accessory_occ.values()) if hits]) / \
                (len(self._mandatory_occ) + len(self._accessory_occ))
        return score

    @property
    def score(self):
        """
        :return: a score take in account
            * if a hit match for the gene or is an homolog or analog
            * if a hit is duplicated and already present in the system or the cluster
            * if a hit match for mandatory/accessory gene of the model
        :rtype: float
        """
        score = sum([clst.score for clst in self.clusters])
        for gene in self.model.mandatory_genes + self.model.accessory_genes:
            clst_having_hit = sum([1 for clst in self.clusters if clst.fulfilled_function(gene)])
            if clst_having_hit:
                clst_penalty = (clst_having_hit - 1) * 1.5
                score -= clst_penalty
        return score


    def occurrence(self):
        """
        sometimes several systems collocates so they form only one cluster
        so macsyfinder build only one system
        the occurrence is an indicator of how many systems are
        it's based on the number of occurrence of each mandatory genes

        :return: a predict number of biologic systems
        """
        occ_per_gene = [len(hits) for hits in self._mandatory_occ.values()]
        # if a systems contains 5 gene whit occ of 1 and 5 gene with 0 occ
        # the median is 0.5
        # round(0.5) = 0
        # so I fix a floor value at 1
        return max(1, round(statistics.median(occ_per_gene)))


    @property
    def hits(self):
        """
        :return: The list of all hits that compose this system
        :rtype: [:class:`macsypy.hit.ValidHits` , ... ]
        """
        hits = [h for cluster in self.clusters for h in cluster.hits]
        return hits

    @property
    def loci(self):
        """
        :return: The number of loci of this system
        :rtype: int > 0
        """
        # we do not take loners in account
        loci = sum([1 for c in self.clusters if len(c) > 1])
        return loci


    @property
    def multi_loci(self):
        """
        :return: True if the systems is multi_loci. False otherwise
        :rtype: bool
        """
        return self.loci > 1


class SystemSerializer:

    def __init__(self, system, hit_system_tracker):
        self.system = system
        self.hit_system_tracker = hit_system_tracker

    def __str__(self):
        clst = ", ".join(["[" + ", ".join([str((v_h.gene.name, v_h.position)) for v_h in cluster.hits]) + "]"
                          for cluster in self.system.clusters])

        s = f"""system id = {self.system.id}
model = {self.system.model.fqn}
replicon = {self.system.replicon_name}
clusters = {clst}
occ = {self.system.occurrence()}
wholeness = {self.system.wholeness:.3f}
loci nb = {self.system.loci}
score = {self.system.score:.3f}
"""
        for title, genes in (("mandatory", self.system.mandatory_occ),
                             ("accessory", self.system.accessory_occ),
                             ("neutral", self.system.neutral_occ)):
            s += f"\n{title} genes:\n"
            for g_name, hits in genes.items():
                s += f"\t- {g_name}: {len(hits)} "
                all_hits_str = []
                for h in hits:
                    used_in_systems = [s.id for s in self.hit_system_tracker[h.hit]
                                       if s.model.fqn != self.system.model.fqn]
                    if used_in_systems:
                        hit_str = f"{h.gene.name} [{', '.join(used_in_systems)}]"
                    else:
                        hit_str = f"{h.gene.name}"
                    all_hits_str.append(hit_str)
                s += f'({", ".join(all_hits_str)})\n'

        return s


    def to_json(self):
        """
        :return: a serialisation of this system in json format
                 The json have the following structure
                 {'id': str system_id
                  'model': str model fully qualified name
                  'loci_nb': int number of loci
                  'replicon_name': str the replicon name
                  'clusters': [[ str hit gene name, ...], [...]]
                  'gene_composition': {
                        'mandatory': {str gene_ref name: [ str hit gene name, ... ]},
                        'accessory': {str gene_ref name: [ str hit gene name, ... ]},
                        'neutral': {str gene_ref name: [ str hit gene name, ... ]}
                        }
                 }
        """
        system = {'id': self.system.id,
                  'model': self.system.model.fqn,
                  'loci_nb': len(self.system.clusters),
                  'replicon_name': self.system.replicon_name,
                  'clusters': [[v_h.gene.name for v_h in cluster.hits]for cluster in self.system.clusters],
                  'gene_composition':
                      {'mandatory': {gene_ref: [hit.gene.name for hit in hits]
                                     for gene_ref, hits in self.system.mandatory_occ.items()},
                       'accessory': {gene_ref: [hit.gene.name for hit in hits]
                                     for gene_ref, hits in self.system.accessory_occ.items()},
                       'neutral': {gene_ref: [hit.gene.name for hit in hits]
                                     for gene_ref, hits in self.system.neutral_occ.items()}

                       }
                  }
        return json.dumps(system)
