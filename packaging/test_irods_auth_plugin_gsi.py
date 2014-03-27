import sys
if (sys.version_info >= (2,7)):
    import unittest
else:
    import unittest2 as unittest
from pydevtest_common import assertiCmd, assertiCmdFail, getiCmdOutput, create_local_testfile, get_hostname
import pydevtest_sessions as s
from resource_suite import ResourceBase
import os
import commands
import time
import socket

class Test_Gsi_Suite(unittest.TestCase, ResourceBase):
    
    my_test_resource = {"setup":[], "teardown":[]}

    def setUp(self):
        ResourceBase.__init__(self)
        s.twousers_up()
        self.run_resource_setup()

    def tearDown(self):
        self.run_resource_teardown()
        s.twousers_down()

    # Configure iRODS to enable gsi support. Note it will not be turned on until the appropriate environment variable is set
    def gsi_setup(self):

        globusDirTar = "~/secrets/gsi/globus.tar.gz"
        irodsHome = "~/"
        globusDirDest = irodsHome + "/.globus"
        privateKey = globusDirDest + "/userkey.pem"

        # Untar the .globus directory to the irods home dir
        if not os.path.exists(globusDirDest):
            os.system("cd %s && tar xf %s" % (irodsHome, globusDirTar))
            os.system("chmod 600 %s" % privateKey)

        # Set the DN for the user
        assertiCmd(s.adminsession, "iadmin aua rods '/O=Grid/OU=GlobusTest/OU=simpleCA-pluto/OU=local/CN=irods'")
        
        # Set the irodsAuthScheme to turn on GSI
        os.environ['irodsAuthScheme'] = "gsi"

    # Try to authenticate before getting a certificate. Make sure this fails.
    def test_authentication_gsi_without_cert(self):

        self.gsi_setup()

        # Destroy the proxy certs so we can test for failure
        os.system("grid-proxy-destroy")

        # Try an ils and make sure it fails
        assertiCmdFail(s.adminsession, "ils", "LIST", "home")

    # Try to authenticate after getting a TGT. This should pass
    def test_authentication_gsi_with_cert(self):
        gsiPassword = "irods"

        self.gsi_setup()

        # Make sure we have a valid TGT
        os.system("echo %s | grid-proxy-init -pwstdin" % gsiPassword)

        # Try an ils
        assertiCmd(s.adminsession, "ils", "LIST", "home")

