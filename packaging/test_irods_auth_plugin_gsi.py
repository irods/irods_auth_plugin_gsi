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

    # Placeholder for the previous auth scheme state
    prev_auth_scheme = "native"

    def setUp(self):
        ResourceBase.__init__(self)
        s.twousers_up()
        self.run_resource_setup()

    def tearDown(self):
        self.run_resource_teardown()
        s.twousers_down()

    # Configure iRODS to enable gsi support. Note it will not be turned on until the appropriate environment variable is set
    def gsi_setup(self):

        globusDirSrc = "~/secrets/gsi/.globus"
        irodsHome = "~/"
        globusDirDest = irodsHome + "/.globus"
        privateKey = globusDirDest + "/userkey.pem"

        # Untar the .globus directory to the irods home dir
        if not os.path.exists(globusDirDest):
            os.system("cp -r %s %s" % (globusDirSrc, globusDirDest))
            os.system("chmod 600 %s" % privateKey)

        # Set the DN for the user
        os.system("iadmin aua rods '/O=Grid/OU=GlobusTest/OU=simpleCA-pluto/OU=local/CN=irods'")
        
        # Set the appropriate environment variables
        try:
            self.prev_auth_scheme = os.environ['irodsAuthScheme']
        except KeyError:
            pass

        # Set the irodsAuthScheme to turn on GSI
        os.environ['irodsAuthScheme'] = "gsi"

    # Restore the state of the system
    def gsi_teardown(self):

        # Restore the previous auth scheme
        os.environ['irodsAuthScheme'] = self.prev_auth_scheme

    # Try to authenticate before getting a certificate. Make sure this fails.
    def test_authentication_gsi_without_cert(self):

        self.gsi_setup()

        # Destroy the proxy certs so we can test for failure
        os.system("grid-proxy-destroy")

        # Try an ils and make sure it fails
        assertiCmd(s.adminsession, "ils", "ERROR", "GSI_ERROR_ACQUIRING_CREDS")

        self.gsi_teardown()

    # Try to authenticate after getting a TGT. This should pass
    def test_authentication_gsi_with_cert(self):
        gsiPassword = "irods"

        self.gsi_setup()

        # Make sure we have a valid proxy cert
        pipe = os.popen("grid-proxy-init -pwstdin", 'w')
        print("Writing password: " gsiPassword " to the grid-proxy-init")
        pipe.write(gsiPassword)
        pipe.close()

        # Try an ils
        assertiCmd(s.adminsession, "ils", "LIST", "home")

        self.gsi_teardown()
