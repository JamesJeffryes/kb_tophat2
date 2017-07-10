# -*- coding: utf-8 -*-
import unittest
import os  # noqa: F401
import json  # noqa: F401
import time
import requests  # noqa: F401
import shutil

from os import environ
try:
    from ConfigParser import ConfigParser  # py2
except:
    from configparser import ConfigParser  # py3

from pprint import pprint  # noqa: F401

from biokbase.workspace.client import Workspace as workspaceService
from kb_tophat2.kb_tophat2Impl import kb_tophat2
from kb_tophat2.kb_tophat2Server import MethodContext
from kb_tophat2.authclient import KBaseAuth as _KBaseAuth
from kb_tophat2.Utils.TopHatUtil import TopHatUtil
from AssemblyUtil.AssemblyUtilClient import AssemblyUtil
from ReadsUtils.ReadsUtilsClient import ReadsUtils


class kb_tophat2Test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        token = environ.get('KB_AUTH_TOKEN', None)
        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('kb_tophat2'):
            cls.cfg[nameval[0]] = nameval[1]
        # Getting username from Auth profile for token
        authServiceUrl = cls.cfg['auth-service-url']
        auth_client = _KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': token,
                        'user_id': user_id,
                        'provenance': [
                            {'service': 'kb_tophat2',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        cls.wsURL = cls.cfg['workspace-url']
        cls.wsClient = workspaceService(cls.wsURL)
        cls.serviceImpl = kb_tophat2(cls.cfg)
        cls.scratch = cls.cfg['scratch']
        cls.callback_url = os.environ['SDK_CALLBACK_URL']

        suffix = int(time.time() * 1000)
        cls.wsName = "test_kb_tophat2_" + str(suffix)
        cls.wsClient.create_workspace({'workspace': cls.wsName})

        cls.tophat_runner = TopHatUtil(cls.cfg)

        cls.ru = ReadsUtils(cls.callback_url)
        cls.au = AssemblyUtil(cls.callback_url)

        cls.prepare_data()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    @classmethod
    def prepare_data(cls):
        # upload reads object
        fwd_reads_file_name = 'reads_1.fq'
        fwd_reads_file_path = os.path.join(cls.scratch, fwd_reads_file_name)
        shutil.copy(os.path.join('data', fwd_reads_file_name), fwd_reads_file_path)

        rev_reads_file_name = 'reads_2.fq'
        rev_reads_file_path = os.path.join(cls.scratch, rev_reads_file_name)
        shutil.copy(os.path.join('data', rev_reads_file_name), rev_reads_file_path)

        se_reads_object_name = 'test_se_reads'
        cls.se_reads_ref = cls.ru.upload_reads({'fwd_file': fwd_reads_file_path,
                                                'wsname': cls.wsName,
                                                'sequencing_tech': 'Unknown',
                                                'name': se_reads_object_name
                                                })['obj_ref']

        pe_reads_object_name = 'test_pe_reads'
        cls.pe_reads_ref = cls.ru.upload_reads({'fwd_file': fwd_reads_file_path,
                                                'rev_file': rev_reads_file_path,
                                                'wsname': cls.wsName,
                                                'sequencing_tech': 'Unknown',
                                                'name': pe_reads_object_name
                                                })['obj_ref']

        # upload assembly object
        fasta_file_name = 'test_ref.fa'
        fasta_file_path = os.path.join(cls.scratch, fasta_file_name)
        shutil.copy(os.path.join('data', fasta_file_name), fasta_file_path)

        assemlby_name = 'test_assembly'
        cls.assembly_ref = cls.au.save_assembly_from_fasta({'file': {'path': fasta_file_path},
                                                            'workspace_name': cls.wsName,
                                                            'assembly_name': assemlby_name
                                                            })

    def getWsClient(self):
        return self.__class__.wsClient

    def getWsName(self):
        return self.__class__.wsName

    def getImpl(self):
        return self.__class__.serviceImpl

    def getContext(self):
        return self.__class__.ctx

    def test_bad_run_tophat2_app_params(self):
        invalidate_input_params = {
            'missing_input_ref': 'input_ref',
            'assembly_or_genome_ref': 'assembly_or_genome_ref',
            'workspace_name': 'workspace_name',
            'alignment_object_name': 'alignment_object_name'
        }
        with self.assertRaisesRegexp(
                ValueError, '"input_ref" parameter is required, but missing'):
            self.getImpl().run_tophat2_app(self.getContext(), invalidate_input_params)

        invalidate_input_params = {
            'input_ref': 'input_ref',
            'missing_assembly_or_genome_ref': 'assembly_or_genome_ref',
            'workspace_name': 'workspace_name',
            'alignment_object_name': 'alignment_object_name'
        }
        with self.assertRaisesRegexp(
                ValueError, '"assembly_or_genome_ref" parameter is required, but missing'):
            self.getImpl().run_tophat2_app(self.getContext(), invalidate_input_params)

        invalidate_input_params = {
            'input_ref': 'input_ref',
            'assembly_or_genome_ref': 'assembly_or_genome_ref',
            'missing_workspace_name': 'workspace_name',
            'alignment_object_name': 'alignment_object_name'
        }
        with self.assertRaisesRegexp(
                ValueError, '"workspace_name" parameter is required, but missing'):
            self.getImpl().run_tophat2_app(self.getContext(), invalidate_input_params)

        invalidate_input_params = {
            'input_ref': 'input_ref',
            'assembly_or_genome_ref': 'assembly_or_genome_ref',
            'workspace_name': 'workspace_name',
            'missing_alignment_object_name': 'alignment_object_name'
        }
        with self.assertRaisesRegexp(
                ValueError, '"alignment_object_name" parameter is required, but missing'):
            self.getImpl().run_tophat2_app(self.getContext(), invalidate_input_params)

    def test_run_tophat2_app_se_reads(self):
        input_params = {
            'input_ref': self.se_reads_ref,
            'assembly_or_genome_ref': self.assembly_ref,
            'workspace_name': self.getWsName(),
            'alignment_object_name': 'My_Alignment'
        }

        result = self.getImpl().run_tophat2_app(self.getContext(), input_params)[0]

        self.assertTrue('result_directory' in result)
        result_files = os.listdir(result['result_directory'])
        print result_files
        self.assertTrue('reads_alignment_object_ref' in result)

    def test_run_tophat2_app_pe_reads(self):
        input_params = {
            'input_ref': self.pe_reads_ref,
            'assembly_or_genome_ref': self.assembly_ref,
            'workspace_name': self.getWsName(),
            'alignment_object_name': 'My_Alignment',
            'reads_condition': 'test_condition'
        }

        result = self.getImpl().run_tophat2_app(self.getContext(), input_params)[0]

        self.assertTrue('result_directory' in result)
        result_files = os.listdir(result['result_directory'])
        print result_files
        self.assertTrue('reads_alignment_object_ref' in result)
