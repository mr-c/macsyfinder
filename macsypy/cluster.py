#########################################################################
# MacSyFinder - Detection of macromolecular systems in protein dataset  #
#               using systems modelling and similarity search.          #
# Authors: Sophie Abby, Bertrand Neron                                  #
# Copyright (c) 2014-2021  Institut Pasteur (Paris) and CNRS.           #
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
import logging

import macsypy.gene

from .error import MacsypyError
from .gene import GeneStatus
from .hit import MultiSystem, Loner, LonerMultiSystem, get_best_hit_4_func

_log = logging.getLogger(__name__)


def _collocates(h1, h2, rep_info):
        """
        compute the distance (in number of gene between) between 2 hits

        :param :class:`macsypy.hit.ModelHit` h1: the first hit to compute inter hit distance
        :param :class:`macsypy.hit.ModelHit` h2: the second hit to compute inter hit distance
        :return: True if the 2 hits spaced by lesser or equal genes than inter_gene_max_space.
                 Managed circularity.
        """
        # compute the number of genes between h1 and h2
        dist = h2.get_position() - h1.get_position() - 1
        g1 = h1.gene_ref
        g2 = h2.gene_ref
        model = g1.model
        
        d1 = g1.inter_gene_max_space
        d2 = g2.inter_gene_max_space

        if d1 is None and d2 is None:
            inter_gene_max_space = model.inter_gene_max_space
        elif d1 is None:
            inter_gene_max_space = d2
        elif d2 is None:
            inter_gene_max_space = d1
        else: # d1 and d2 are defined
            inter_gene_max_space = min(d1, d2)

        if 0 <= dist <= inter_gene_max_space:
            return True
        elif dist <= 0 and rep_info.topology == 'circular':
            # h1 and h2 overlap the ori
            dist = rep_info.max - h1.get_position() + h2.get_position() - rep_info.min
            return dist <= inter_gene_max_space
        return False


def _clusterize(hits, model, hit_weights, rep_info):
    """
    clusterize hit regarding the distance between them

    :param hits: the hits to clusterize
    :type hits: list of :class:`macsypy.model.ModelHit` objects
    :param model: the model to consider
    :type model: :class:`macsypy.model.Model` object
    :param hit_weights: the hit weight to compute the score
    :type hit_weights: :class:`macsypy.hit.HitWeight` object
    :type rep_info: :class:`macsypy.Indexes.RepliconInfo` object

    :return: the clusters
    :rtype: list of :class:`macsypy.cluster.Cluster` objects.
    """
    clusters = []
    cluster_scaffold = []
    # sort hits by increasing position and then descending score
    hits.sort(key=lambda h: (h.position, - h.score))
    # remove duplicates hits (several hits for the same sequence),
    # keep the first one, this with the best score
    # position == sequence rank in replicon
    hits = [next(group) for pos, group in itertools.groupby(hits, lambda h: h.position)]
    if hits:
        hit = hits[0]
        cluster_scaffold.append(hit)
        previous_hit = cluster_scaffold[0]

        for m_hit in hits[1:]:
            if _collocates(previous_hit, m_hit, rep_info):
                cluster_scaffold.append(m_hit)
            else:
                if len(cluster_scaffold) > 1:
                    # close the current scaffold if it contains at least 2 hits
                    cluster = Cluster(cluster_scaffold, model, hit_weights)
                    clusters.append(cluster)
                elif model.min_genes_required == 1:
                    # close the current scaffold if it contains 1 hit
                    # but it's allowed by the model
                    cluster = Cluster(cluster_scaffold, model, hit_weights)
                    clusters.append(cluster)
                elif model.get_gene(cluster_scaffold[0].gene.name).loner:
                    # close the current scaffold it contains 1 hit
                    # to handle circularity if it's the last cluster
                    cluster = Cluster(cluster_scaffold, model, hit_weights)
                    clusters.append(cluster)
                    # the hit transformation in loner is perform at the end when
                    # circularity and merging is done

                # open new scaffold
                cluster_scaffold = [m_hit]
            previous_hit = m_hit

        # close the last current cluster
        len_scaffold = len(cluster_scaffold)
        if len_scaffold > 1:
            new_cluster = Cluster(cluster_scaffold, model, hit_weights)
            clusters.append(new_cluster)
        elif len_scaffold == 1:
            # handle circularity
            # if there are clusters
            # may be the hit collocate with the first hit of the first cluster
            if clusters and _collocates(cluster_scaffold[0], clusters[0].hits[0], rep_info):
                new_cluster = Cluster(cluster_scaffold, model, hit_weights)
                clusters[0].merge(new_cluster, before=True)
            elif cluster_scaffold[0].gene_ref.loner:
                # the hit does not collocate but it's a loner
                # handle clusters containing only one loner
                new_cluster = Cluster(cluster_scaffold, model, hit_weights)
                clusters.append(new_cluster)
            elif model.min_genes_required == 1:
                # the hit does not collocate but the model required only one gene
                # handle clusters containing only one gene
                new_cluster = Cluster(cluster_scaffold, model, hit_weights)
                clusters.append(new_cluster)

        # handle circularity
        if len(clusters) > 1:
            if _collocates(clusters[-1].hits[-1], clusters[0].hits[0], rep_info):
                clusters[0].merge(clusters[-1], before=True)
                clusters = clusters[:-1]
        return clusters


def set_multi_system_hit(clusters):
    """
    check all hits in clusters and cast those wich ref_gene is tagged as mullti-system
    in :class:`macsypy.hit.MultiSystem`

    :param clusters: the clusters
    :type clusters: list of :class:`macsypy.cluster.Cluster`
    :return: The clusters with MutiSystem hits and the register of multi systems hits
             (which will use to compute the clusters combination)
    :rtype: tuple of 2 elts

            * list of :class:`macsypy.cluster.Cluster` objects
            * dixt { str func_name: :class:`macsypy.hit.MultiSystem`}
    """
    ms_registry = {}
    if clusters:
        model = clusters[0].model
        hit_weights = clusters[0].hit_weights
        for clst in clusters:
            for hit in clst.hits:
                if hit.gene_ref.alternate_of().multi_system:
                    func_name = hit.gene_ref.alternate_of().name
                    if func_name in ms_registry:
                        ms_registry[func_name].append((hit, clst))
                    else:
                        ms_registry[func_name] = [(hit, clst)]

        for func_name in ms_registry.items():
            ms =  ms_registry[func_name]
            ms_registry[func_name] = []
            for i in range(len(ms)):
                counterpart = ms[:]
                hit, clst = counterpart.pop(i)
                new_ms_hit = MultiSystem(hit, counterpart=counterpart)
                clst.replace(hit, new_ms_hit)
                ms_registry[func_name].append((MultiSystem(hit, counterpart=counterpart), clst))
            # replace List of Loners by the best Loner
            best_ms = get_best_hit_4_func(func_name, ms_registry[func_name], key='score')
            ms_registry[func_name] = best_ms

        ms_registry = {func_name: Cluster([ms], model, hit_weights) for func_name, ms in ms_registry.items()}
    return clusters, ms_registry


def _get_true_loners(clusters, model, hit_weights):
    """
    A we call a True Loner a Cluster composed of only one gene tagged as loner
    (by opposition with hit representing a gene tagged loner but include in cluster with several other genes)

    :param clusters: the clusters
    :type clusters: list of :class:`macsypy.cluster.Cluster` objects.
    :param model: the model to consider
    :type model: :class:`macsypy.model.Model` object
    :param hit_weights: the hit weight to compute the score
    :type hit_weights: :class:`macsypy.hit.HitWeight` object
    :return: tuple of 2 elts

             * dict containing true clusters  {str func_name : :class:`macsypy.hit.Loner | :class:`macsypy.hit.LonerMultiSystem` object}
             * list of :class:`macsypy.cluster.Cluster` objects
    """
    ###################
    # get True Loners #
    ###################
    # true_loner is a hit which encode for a gene tagged as loner
    # and which does NOT clusterize with some other hits of interest
    true_clusters = []
    true_loners = {}

    for clstr in clusters:
        if len(clstr) > 1:
            true_clusters.append(clstr)
        elif clstr.loner:
            loner = clstr[0]
            func_name = loner.gene_ref.alternate_of().name
            if func_name in true_loners:
                true_loners[func_name].append(loner)
            else:
                true_loners[func_name] = [loner]
        else:
            # it's a cluster of 1 hit
            # but it's NOT a loner
            # min_genes_required == 1
            true_clusters.append(clstr)

    for func_name in true_loners:
        # transform ModelHit in Loner
        loners = true_loners[func_name]
        true_loners[func_name] = []
        for i in range(len(loners)):
            if loners[0].multi_system:
                # the counterpart have been already computed during the MS hit instanciation
                true_loners[func_name].append(LonerMultiSystem(hit))
            else:
                counterpart = loners[:]
                hit = counterpart.pop(i)
                true_loners[func_name].append(Loner(hit, counterpart=counterpart))
        # replace List of Loners by the best Loner
        best_loner = get_best_hit_4_func(func_name, true_loners[func_name], key='score')
        true_loners[func_name] = best_loner

    true_loners = {func_name: Cluster([loner], model, hit_weights) for func_name, loner in true_loners.items()}
    return true_loners, true_clusters



def build_clusters(hits, rep_info, model, hit_weights):
    """
    From a list of filtered hits, and replicon information (topology, length),
    build all lists of hits that satisfied the constraints:

        * max_gene_inter_space
        * loner
        * multi_system

    If Yes create a cluster
    A cluster contains at least two hits separated by less or equal than max_gene_inter_space
    Except for loner genes which are allowed to be alone in a cluster

    :param hits: list of filtered hits
    :type hits: list of :class:`macsypy.hit.ModelHit` objects
    :param rep_info: the replicon to analyse
    :type rep_info: :class:`macsypy.Indexes.RepliconInfo` object
    :param model: the model to study
    :type model: :class:`macsypy.model.Model` object
    :return: list of regular clusters,
             the True loners (loners not in cluster)
             the multi systems hits
    :rtype: tuple with 3 elements

            * true_clusters which is list of :class:`Cluster` objects
            * true_loners: a dict with the function and a :class:macsypy.hit.Loner object as value
            * multi_systems_hits: a dict TODO
    """
    if hits:
        clusters = _clusterize(hits, model, hit_weights, rep_info)
        clusters, multi_system_hits = set_multi_system_hit(clusters)
        true_loners, true_clusters = _get_true_loners(clusters, model, hit_weights)

    else:  # there is not hits
        true_clusters = []
        true_loners = {}
        multi_system_hits = {}
    return true_clusters, true_loners, multi_system_hits


class Cluster:
    """
    Handle hits relative to a model which collocates
    """

    _id = itertools.count(1)

    def __init__(self, hits, model, hit_weights):
        """

        :param hits: the hits constituting this cluster
        :type hits: [ :class:`macsypy.hit.CoreHit` | :class:`macsypy.hit.ModelHit`, ... ]
        :param model: the model associated to this cluster
        :type model: :class:`macsypy.model.Model`
        """
        self.hits = hits
        self.model = model
        self._check_replicon_consistency()
        self._score = None
        self._genes_roles = None
        self._hit_weights = hit_weights
        self.id = f"c{next(self._id)}"

    def __len__(self):
        return len(self.hits)

    def __getitem__(self, item):
        return self.hits[item]

    @property
    def hit_weights(self):
        return self._hit_weights

    @property
    def loner(self):
        """
        :return: True if this cluster is made of only one hit representing a loner gene
                 False otherwise:
                 - contains several hits
                 - contains one hit but gene is not tag as loner (max_gene_required = 1)
        """
        # need this method in build_cluster before to transform ModelHit in Loner
        # so cannot rely on Loner type
        return len(self) == 1 and self.hits[0].gene_ref.loner


    def _check_replicon_consistency(self):
        """
        :raise: MacsypyError if all hits of a cluster are NOT related to the same replicon
        """
        rep_name = self.hits[0].replicon_name
        if not all([h.replicon_name == rep_name for h in self.hits]):
            msg = "Cannot build a cluster from hits coming from different replicons"
            _log.error(msg)
            raise MacsypyError(msg)


    def __contains__(self, v_hit):
        """
        :param v_hit: The hit to test
        :type v_hit: :class:`macsypy.hit.ModelHit` object
        :return: True if the hit is in the cluster hits, False otherwise
        """
        return v_hit in self.hits


    def fulfilled_function(self, gene):
        """

        :param gene: The gene which must be tested.
        :type gene: :class:`macsypy.gene.ModelGene` object
        :return: True if the cluster contains one hit which fulfill the function corresponding to the gene
                 (the gene hitself or an exchageable)
        """
        if self._genes_roles is None:
            self._genes_roles = {h.gene_ref.alternate_of().name for h in self.hits}
        if isinstance(gene, macsypy.gene.ModelGene):
            function = gene.name
        else:
            # gene is a string
            function = gene
        return function in self._genes_roles


    def merge(self, cluster, before=False):
        """
        merge the cluster in this one. (do it in place)

        :param cluster:
        :type cluster: :class:`macsypy.cluster.Cluster` object
        :param bool before: If False the hits of the cluster will be add at the end of this one,
                            Otherwise the cluster hits will be inserted before the hits of this one.
        :return: None
        :raise MacsypyError: if the two clusters have not the same model
        """
        if cluster.model != self.model:
            raise MacsypyError("Try to merge Clusters from different model")
        else:
            if before:
                self.hits = cluster.hits + self.hits
            else:
                self.hits.extend(cluster.hits)

    @property
    def replicon_name(self):
        return self.hits[0].replicon_name


    @property
    def score(self):
        if self._score is not None:
            return self._score
        else:
            seen_hits = {}
            _log.debug(f"===================== compute score for cluster =====================")
            for v_hit in self.hits:
                _log.debug(f"-------------- test hit {v_hit.gene.name} --------------")

                # attribute a score for this hit
                # according to status of the gene_ref in the model: mandatory/accessory
                if v_hit.status == GeneStatus.MANDATORY:
                    hit_score = self._hit_weights.mandatory
                elif v_hit.status == GeneStatus.ACCESSORY:
                    hit_score = self._hit_weights.accessory
                elif v_hit.status == GeneStatus.NEUTRAL:
                    hit_score = self._hit_weights.neutral
                else:
                    raise MacsypyError(f"a Cluster contains hit {v_hit.gene.name} {v_hit.position}"
                                       f" which is neither mandatory nor accessory: {v_hit.status}")
                _log.debug(f"{v_hit.id} is {v_hit.status} hit score = {hit_score}")

                # weighted the hit score according to the hit match the gene or
                # is an exchangeable
                if v_hit.gene_ref.is_exchangeable:
                    hit_score *= self._hit_weights.exchangeable
                    _log.debug(f"{v_hit.id} is exchangeable hit score = {hit_score}")
                else:
                    hit_score *= self._hit_weights.itself

                if v_hit.loner and v_hit.multi_system:
                    hit_score *= self._hit_weights.loner_multi_system
                    _log.debug(f"{v_hit.id} is loner and multi_system hit score = {hit_score}")

                # funct is the name of the gene if it code for itself
                # or the name of the reference gene if it's an exchangeable
                funct = v_hit.gene_ref.alternate_of().name
                if funct in seen_hits:
                    # count only one occurrence of each function per cluster
                    # the score use is the max of hit score for this function
                    if hit_score > seen_hits[funct]:
                        seen_hits[funct] = hit_score
                        _log.debug(f"{v_hit.id} code for {funct} update hit_score to {hit_score}")
                    else:
                        _log.debug(f"{v_hit.id} code for {funct} which is already take in count in cluster")
                else:
                    _log.debug(f"{v_hit.id} {v_hit.gene_ref.name} is not already in cluster")
                    seen_hits[funct] = hit_score

            hits_scores = seen_hits.values()
            score = sum(hits_scores)
            _log.debug(f"cluster score = sum({list(hits_scores)}) = {score}")
        _log.debug(f"===============================================================")
        self._score = score
        return score


    def __str__(self):
        """

        :return: a string representation of this cluster
        """
        s = f"""Cluster:
- model = {self.model.name}
- replicon = {self.replicon_name}
- hits = {', '.join([f"({h.id}, {h.gene.name}, {h.position})" for h in self.hits])}"""
        return s

    def replace(self, old, new):
        idx = self.hits.index(old)
        self.hits[idx] = new