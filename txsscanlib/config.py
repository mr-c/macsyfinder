# -*- coding: utf-8 -*-

#===============================================================================
# Created on Nov 12, 2012
# 
# @author: bertrand Néron
# @contact: bneron <at> pasteur <dot> fr
# @organization: organization_name
# @license: license
#===============================================================================

import os
import sys
import inspect
from ConfigParser import SafeConfigParser, NoSectionError

_prefix_path = '$PREFIX'

import logging

class Config(object):
    """
    parse configuration files and handle the configuration according the file location precedence
    /etc/txsscan.conf < ~/.txsscan.conf < .txsscan.conf
    if a configuration file is given on the command line, only this file is used.
    in fine the arguments passed have the highest priority
    """
    
    options = ('sequence_db', 'ordered_db', 'hmmer_exe' , 'e_value_res', 'i_evalue_sel', 'coverage_profile', 'def_dir', 'res_search_dir', 'res_search_suffix', 'profile_dir', 'profile_suffix', 'res_extract_suffix', 
               'log_level')

    def __init__(self, cfg_file = "",
                sequence_db = None ,
                ordered_db = None,  
                hmmer_exe = None,
                e_value_res = None,
                i_evalue_sel = None,
                coverage_profile = None,
                def_dir = None , 
                res_search_dir = None,
                res_search_suffix = None,
                profile_dir = None,
                profile_suffix = None,
                res_extract_suffix = None,
                log_level = None
                ):
        """
        :param sequence_db: the path to the sequence database
        :type sequence_db: string
        :param ordered_db: the genes of the db are ordered
        :type ordered_db: boolean
        :param hmmer_exe: the hmmsearch executabe
        :type hmmer_exe: string
        :param e_value_res: à déterminer
        :type  e_value_res: float
        :param i_evalue_sel: à déterminer
        :type  i_evalue_sel: float
        :param coverage_profile: a déterminer
        :type coverage_profile: float
        :param def_dir: the path to the definition directory
        :type def_dir: string
        :param res_search_dir: à déterminer
        :type  res_search_dir: string
        :param res_search_suffix: à déterminer
        :type  res_search_suffix: string
        :param res_extract_suffix: à déterminer
        :type  res_extract_suffix: string
        :param profile_dir: à déterminer
        :type  profile_dir: string
        :param profile_suffix: à déterminer
        :type  profile_suffix: string
        :param log_level: the level of log output
        :type log_level: int
        """

        config_files = [cfg_file] if cfg_file else [ os.path.join( _prefix_path , '/etc/txsscan/txsscan.conf'),
                                                     os.path.expanduser('~/.txsscan/txsscan.conf'),
                                                      '.txsscan.conf']
        self.parser = SafeConfigParser(defaults={
                                            'hmmer_exe' : 'hmmsearch',
                                            'e_value_res' : "1",
                                            'i_evalue_sel' : "0.5",
                                            'coverage_profile' : "0.5",
                                            'def_dir': './DEF',
                                            'res_search_dir' : './datatest/res_search',
                                            'res_search_suffix' : '.search_hmm.out',
                                            'res_extract_suffix' : '.res_hmm_extract',
                                            'profile_dir' : './profiles',
                                            'profile_suffix' : '.fasta-aln_edit.hmm',
                                            'log_level': 0,
                                            'log_file': sys.stderr
                                            },
                                  )
        used_files = self.parser.read(config_files)
        
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)

        cmde_line_opt = {}
        for arg in args:
            if arg in self.options and values[arg] is not None:
                cmde_line_opt[arg] = str(values[arg])

        try:
            log_level = self.parser.get('general', 'log_level', vars = cmde_line_opt)
        except AttributeError:
            log_level = logging.WARNING
        else:
            try:
                log_level = int(log_level)
            except ValueError:
                try:
                    log_level = getattr(logging, log_level.upper())
                except AttributeError:
                    log_level = logging.WARNING
        try:
            log_file = self.parser.get('general', 'log_file', vars = cmde_line_opt)
            try:
                log_handler = logging.FileHandler(log_file)
            except Exception , err:
                #msg = "Cannot log into %s : %s . logs will redirect to stderr" % (log_file,err)
                log_handler = logging.StreamHandler(sys.stderr)
        except AttributeError:
            log_handler = logging.StreamHandler( sys.stderr )    
            
        handler_formatter = logging.Formatter("%(levelname)-8s : L %(lineno)d : %(message)s")
        log_handler.setFormatter(handler_formatter)
        log_handler.setLevel(log_level)
        
        root = logging.getLogger()
        root.setLevel( logging.NOTSET )
        
        logger = logging.getLogger('txsscan')
        logger.setLevel(log_level)
        logger.addHandler(log_handler)
        self._log = logging.getLogger('txsscan.config')

        self.options = self._validate(cmde_line_opt)        
        
    
    def _validate(self, cmde_line_opt):
        """
        get all configuration values and validate the values

        :param cmde_line_opt: the options from the command line
        :type cmde_line_opt: dict
        :return: all the options for this execution
        :rtype: dictionnary
        """  
        options = {}
        if 'sequence_db' in cmde_line_opt:
            cmde_line_opt['file'] = cmde_line_opt['sequence_db']
        
        try:
            try:
               options['sequence_db'] = self.parser.get( 'base', 'file', vars = cmde_line_opt )    
            except NoSectionError:
                sequence_db = cmde_line_opt.get( 'sequence_db' , None )
                if sequence_db is None:
                    raise ValueError( "No genome sequence file specified")
                else:
                    options['sequence_db'] = sequence_db
            if not os.path.exists(options['sequence_db']):
                raise ValueError( "%s: No such sequence data " % options['sequence_db'])
            
            if 'ordered_db' in cmde_line_opt:
                options['ordered_db'] = cmde_line_opt['ordered_db']
            else:
                try:
                    options['ordered_db'] = self.parser.getboolean( 'base', 'ordered') 
                except NoSectionError:
                    options['ordered_db'] = False
            
            options['hmmer_exe'] = self.parser.get('hmmer', 'hmmer_exe', vars = cmde_line_opt)
            
            try:
                e_value_res = self.parser.get('hmmer', 'e_value_res', vars = cmde_line_opt)
                options['e_value_res'] = float(e_value_res)
            except ValueError:
                msg = "Invalid value for hmmer e_value_res :{0}: (float expected)".format(e_value_res)
                raise ValueError( msg )
            
            try:
                i_evalue_sel = self.parser.get('hmmer', 'i_evalue_sel', vars = cmde_line_opt)
                options['i_evalue_sel'] = float(i_evalue_sel)
            except ValueError:
                msg = "Invalid value for hmmer i_evalue_sel :{0}: (float expected)".format(i_evalue_sel)
                raise ValueError( msg )
            
            if i_evalue_sel > e_value_res:
                raise ValueError( "i_evalue_sel (%f) must be greater than e_value_res (%f)" %( i_evalue_sel, e_value_res) )
            
            try:
                coverage_profile = self.parser.get('hmmer', 'coverage_profile', vars = cmde_line_opt)
                options['coverage_profile'] = float(coverage_profile)
            except ValueError:
                msg = "Invalid value for hmmer coverage_profile :{0}: (float expected)".format(coverage_profile)
                raise ValueError( msg )
            
            options['def_dir'] = self.parser.get('directories', 'def_dir', vars = cmde_line_opt)
            if not os.path.exists(options['def_dir']):
                raise ValueError( "%s: No such definition directory" % options['def_dir'])

            options['res_search_dir'] = self.parser.get('directories', 'res_search_dir', vars = cmde_line_opt)
            if not os.path.exists(options['res_search_dir']):
                raise ValueError( "%s: No such research search directory" % options['res_search_dir'])

            options['profile_dir'] = self.parser.get('directories', 'profile_dir', vars = cmde_line_opt)
            if not os.path.exists( options['profile_dir'] ):
                raise ValueError( "%s: No such profile directory" % options['profile_dir'])

            options['res_search_suffix'] =  self.parser.get('directories', 'res_search_suffix', vars = cmde_line_opt)
            options['res_extract_suffix'] = self.parser.get('directories', 'res_extract_suffix', vars = cmde_line_opt)
            options['profile_suffix'] = self.parser.get('directories', 'profile_suffix', vars = cmde_line_opt)
            

        except ValueError, err:
            self._log.error(str(err))
            raise err
        return options

    @property
    def sequence_db(self):
        return self.options['sequence_db']

    @property
    def ordered_db(self):
        return self.options['ordered_db']

    @property
    def hmmer_exe(self):
        return self.options['hmmer_exe']

    @property
    def e_value_res(self):
        return self.options['e_value_res']

    @property
    def i_evalue_sel(self):
        return self.options['i_evalue_sel']

    @property
    def coverage_profile(self):
        return self.options['coverage_profile']

    @property
    def def_dir(self):
        return self.options['def_dir']

    @property
    def res_search_dir(self):
        return self.options['res_search_dir']

    @property
    def res_search_suffix(self):
        return self.options['res_search_suffix']

    @property
    def profile_dir(self):
        return self.options['profile_dir']

    @property
    def profile_suffix(self):
        return self.options['profile_suffix']

    @property
    def res_extract_suffix(self):
        return self.options['res_extract_suffix']

    