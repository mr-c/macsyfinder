MacSyFinder
===========

[![pipeline status](https://gitlab.pasteur.fr/gem/MacSyFinder/badges/master/pipeline.svg)]
(https://gitlab.pasteur.fr/gem/MacSyFinder/commits/master)
[![coverage report](https://gitlab.pasteur.fr/gem/MacSyFinder/badges/master/coverage.svg)]
(https://gitlab.pasteur.fr/gem/MacSyFinder/commits/master)
[![Documentation]()https://img.shields.io/badge/style-plastic-blue.svg?style=plastic

MacSyFinder - Detection of macromolecular systems in protein datasets using systems modelling and similarity search.



Citation
-------- 
Abby SS, Néron B, Ménager H, Touchon M, Rocha EPC (2014). MacSyFinder: A Program to Mine Genomes for Molecular Systems with an Application to CRISPR-Cas Systems. PLoS ONE 9(10): e110726. doi:10.1371/journal.pone.0110726
http://www.plosone.org/article/info%3Adoi%2F10.1371%2Fjournal.pone.0110726


Download distribution
---------------------
 
[ ![Download](https://api.bintray.com/packages/gem-pasteur/MacSyFinder/macsyfinder/images/download.svg) ](https://bintray.com/gem-pasteur/MacSyFinder/macsyfinder/_latestVersion)


Installation from distribution
------------------------------

1. Uncompress and untar the package:

   `tar -xzf macsyfinder-x.x.tar.gz`

2. Go to the MacSyFinder directory
 
    `cd macsyfinder-x.x`

3. Build 

    `python setup.py build`

4. Test    

    `python setup.py test -vv`

5. Install

    * on linux    
        `sudo python setup.py install`

    * on MacOS
      From `sierra` and `high sierra` version we cannot install anything in /usr even if you are root.
      So we need to install in /usr/local
      `sudo python setup.py install --prefix /usr/local`
      
    To see all installation options "python setup.py --help"

See the INSTALL file for more details.


Installation from repository
----------------------------

 Please be careful, MacSyView has its own repository: https://github.com/gem-pasteur/macsyview
 
 
 
Unit tests with Travis-CI
-------------------------
 [![Build Status](https://travis-ci.org/gem-pasteur/macsyfinder.svg?branch=master)](https://travis-ci.org/gem-pasteur/macsyfinder)


Documentation
-------------

You will find complete documentation for setting up your project at the Read the Docs site.

[![Doc] (https://readthedocs.org/projects/macsyfinder/badge/?version=latest)](http://macsyfinder.readthedocs.org/en/latest/#)
