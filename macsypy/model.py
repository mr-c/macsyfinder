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


import logging
_log = logging.getLogger(__name__)
from itertools import chain

from .error import ModelInconsistencyError
from .registries import split_def_name


class ModelBank:
    """
    Build and store all Models objects. Systems must not be instantiated directly.
    This model factory must be used. It ensures there is a unique instance
    of a model for a given model name.
    To get a model, use the method __getitem__ via the "[]". If the Model is already cached in the ModelBank,
    it is returned. Otherwise a new model is built, stored and then returned.
    """

    def __init__(self):
        self._model_bank = {}


    def __getitem__(self, name):
        """
        :param name: the name of the model
        :type name: string
        :return: the model corresponding to the name.
         If the model already exists, return it, otherwise build it and return it.
        :rtype: :class:`macsypy.model.Model` object
        """
        if name in self._model_bank:
            return self._model_bank[name]
        else:
            raise KeyError(name)


    def __contains__(self, model):
        """
        Implement the membership test operator
        
        :param model: the model to test
        :type model: :class:`macsypy.model.Model` object
        :return: True if the model is in the Model factory, False otherwise
        :rtype: boolean
        """
        return model in self._model_bank.values()


    def __iter__(self):
        """
        Return an iterator object on the models contained in the bank
        """
        return iter(self._model_bank.values())


    def __len__(self):
        """
        :return: the number of models stored in the bank
        :rtype: integer
        """
        return len(self._model_bank)
    
    
    def add_model(self, model):
        """
        :param model: the model to add
        :type model: :class:`macsypy.model.Model` object
        :raise: KeyError if a model with the same name is already registered.
        """
        if model.fqn in self._model_bank:
            raise KeyError("a model named {0} is already registered in the models' bank".format(model.name))
        else:
            self._model_bank[model.fqn] = model


class Model:
    """
    Handles a macromolecular model.

    Contains all its pre-defined characteristics expected to be fulfilled to predict a complete model:
        - component list (genes that are required, accessory, forbidden)
        - quorum (number of genes)
        - genetic architecture

    """

    def __init__(self, fqn, inter_gene_max_space, min_mandatory_genes_required=None,
                 min_genes_required=None, max_nb_genes=None, multi_loci=False):
        """
        :param fqn: the fully qualified name of the model CRISPR-Cas/sub-typing/CAS-TypeIE
        :type fqn: string
        :param inter_gene_max_space: the maximum distance between two genes (**co-localization** parameter)
        :type inter_gene_max_space: integer
        :param min_mandatory_genes_required: the quorum of mandatory genes to define this model
        :type min_mandatory_genes_required: integer
        :param min_genes_required: the quorum of genes to define this model
        :type min_genes_required: integer
        :param max_nb_genes: 
        :type max_nb_genes: integer
        :param multi_loci: 
        :type multi_loci: boolean
        """
        self.name = split_def_name(fqn)[-1]
        self.fqn = fqn
        self._inter_gene_max_space = inter_gene_max_space
        self._min_mandatory_genes_required = min_mandatory_genes_required
        self._min_genes_required = min_genes_required
        if self._min_mandatory_genes_required is not None and self._min_genes_required is not None:
            if self._min_genes_required < self._min_mandatory_genes_required:
                raise ModelInconsistencyError("{}: min_genes_required '{}' must be greater or equal"
                                              " than min_mandatory_genes_required '{}'".format(
                                                 self.fqn,
                                                 self.min_genes_required,
                                                 self.min_mandatory_genes_required)
                                              )
        self._max_nb_genes = max_nb_genes
        self._multi_loci = multi_loci
        self._mandatory_genes = []
        self._accessory_genes = []
        self._forbidden_genes = []


    def __str__(self):
        s = "name: {}\n".format(self.name)
        s += "fqn: {}\n".format(self.fqn)
        s += "==== mandatory genes ====\n"
        for g in self._mandatory_genes:
            s += "{}\n".format(g.name)
        s += "==== accessory genes ====\n"
        for g in self._accessory_genes:
            s += "{}\n".format(g.name)
        s += "==== forbidden genes ====\n"
        for g in self._forbidden_genes:
            s += "{}\n".format(g.name)
        s += "============== end pprint model ================\n"
        return s


    def __hash__(self):
        return id(self)


    def __lt__(self, other):
        """
        :param other: the other model to compare
        :return: True if this fully qualified name is lesser than to other fully qualified name.
                 False otherwise.
        :rtype: boolean
        """
        return self.fqn < other.fqn


    def __gt__(self, other):
        """
        :param other: the other model to compare
        :return: True if this fully qualified name is greater than to other fully qualified name.
                 False otherwise.
        :rtype: boolean
        """
        return self.fqn > other.fqn


    def __eq__(self, other):
        """
        :param other: the other model to compare
        :return: True if this fully qualified name is equal to other fully qualified name.
                 False otherwise.
        :rtype: boolean
        """
        return self.fqn == other.fqn


    @property
    def inter_gene_max_space(self):
        """
        :return: set the maximum distance allowed between 2 genes for this model
        :rtype: integer
        """
        # self._inter_gene_max_space come from the definition (xml)
        # cfg_inter_gene_max_space come from the configuration command line option or conf file
        # so cfg_inter_gene_max_space must superseed self._inter_gene_max_space
        return self._inter_gene_max_space


    @property
    def min_mandatory_genes_required(self):
        """
        :return: get the quorum of mandatory genes required for this model
        :rtype: integer
        """
        if self._min_mandatory_genes_required is None:
            return len(self._mandatory_genes)
        return self._min_mandatory_genes_required


    @property
    def min_genes_required(self):
        """
        :return: get the minimum number of genes to assess for the model presence.
        :rtype: integer
        """
        if self._min_genes_required is None:
            return len(self._mandatory_genes)
        return self._min_genes_required

    @property
    def max_nb_genes(self):
        """
        :return: the maximum number of genes to assess the model presence.
        :rtype: int (or None)
        """
        return self._max_nb_genes

    @property
    def multi_loci(self):
        """
        :return: True if the model is authorized to be inferred from multiple loci, False otherwise
        :rtype: boolean
        """

        return self._multi_loci

        
    def add_mandatory_gene(self, gene):
        """
        Add a gene to the list of mandatory genes

        :param gene: gene that is mandatory for this model
        :type gene: :class:`macsypy.gene.Gene` object
        """
        self._mandatory_genes.append(gene)


    def add_accessory_gene(self, gene):
        """
        Add a gene to the list of accessory genes

        :param gene: gene that is allowed to be present in this model
        :type gene: :class:`macsypy.gene.Gene` object
        """
        self._accessory_genes.append(gene)


    def add_forbidden_gene(self, gene):
        """
        Add a gene to the list of forbidden genes

        :param gene: gene that must not be found in this model
        :type gene: :class:`macsypy.genen.Gene` object
        """
        self._forbidden_genes.append(gene)


    @property
    def mandatory_genes(self):
        """
        :return: the list of genes that are mandatory in this macromolecular model
        :rtype: list of :class:`macsypy.gene.Gene` objects
        """
        return self._mandatory_genes


    @property
    def accessory_genes(self):
        """
        :return: the list of genes that are allowed in this macromolecular model
        :rtype: list of :class:`macsypy.gene.Gene` objects
        """
        return self._accessory_genes


    @property
    def forbidden_genes(self):
        """
        :return: the list of genes that are forbidden in this macromolecular model
        :rtype: list of :class:`macsypy.gene.Gene` objects
        """
        return self._forbidden_genes


    def get_gene(self, gene_name):
        """
        :param gene_name: the name of the gene to get
        :type gene_name: string
        :return: the gene corresponding to gene_name.
        :rtype: a :class:`macsypy.gene.Gene` object.
        :raise: KeyError the model does not contain any gene with name gene_name.
        """
        all_genes = (self.mandatory_genes, self.accessory_genes, self.forbidden_genes)
        for g_list in all_genes:
            for g in g_list:
                if g.name == gene_name:
                    return g
                else:
                    homolgs = g.get_homologs()
                    analogs = g.get_analogs()
                    for ex in homolgs + analogs:
                        if ex.name == gene_name:
                            return ex
        raise KeyError("Model {} does not contain gene {}".format(self.name, gene_name))


    def get_gene_ref(self, gene):
        """
        :param gene: the gene to get the gene reference.
        :type gene: a :class:`macsypy.gene.Gene` or macsypy.gene.Homolog` or macsypy.gene.Analog` object.
        :return: The gene reference of the gene if exists (if the gene is an Homolog or an Analog),
                 otherwise return None.
        :rtype: :class:`macsypy.gene.Gene` object or None
        :raise: KeyError if gene is not in the model
        """
        g = self.get_gene(gene.name)
        try:
            return g.gene_ref
        except AttributeError:
            return None


    def filter(self, hits):
        """
        filter the hits according to this model. The hits must be link to a gene, belonging to the model
        as mandatory, accessory or forbidden, or be an analog or homologs of one these genes

        :param hits: list of hits to filter
        :type hits: list of :class:`macsypy.report.Hit` object
        :return: list of hits
        :rtype: list of :class:`macsypy.report.Hit` object
        """
        primary_genes = [g for g in chain(self._mandatory_genes, self._accessory_genes, self._forbidden_genes)]
        exchangeable_genes = [g_ex for g in primary_genes for g_ex in chain(g.get_analogs(), g.get_homologs())if g.exchangeable]
        all_genes = {g.name for g in chain(primary_genes, exchangeable_genes)}

        compatible_hits = [h for h in hits if h.gene.name in all_genes]
        return compatible_hits