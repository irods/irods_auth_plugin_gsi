import os

import sys
if sys.version_info >= (2,7):
    import unittest
else:
    import unittest2 as unittest

from resource_suite import ResourceBase


class Test_Gsi(ResourceBase, unittest.TestCase):
    def setUp(self):
        super(Test_Gsi, self).setUp()
        globusDirSrc = '~/secrets/gsi/.globus'
        irodsHome = "~/"
        globusDirDest = irodsHome + '.globus'
        privateKey = globusDirDest + '/userkey.pem'

        # Untar the .globus directory to the irods home dir
        if not os.path.exists(globusDirDest):
            os.system("cp -r %s %s" % (globusDirSrc, globusDirDest))
            os.system("chmod 600 %s" % privateKey)

        # Set the DN for the user
        os.system("iadmin aua rods '/O=Grid/OU=GlobusTest/OU=simpleCA-pluto/OU=local/CN=irods'")

        try:
            self.prev_auth_scheme = os.environ['IRODS_AUTHENTICATION_SCHEME']
        except KeyError:
            self.prev_auth_scheme = None
        os.environ['IRODS_AUTHENTICATION_SCHEME'] = 'gsi'

    def tearDown(self):
        if self.prev_auth_scheme:
            os.environ['IRODS_AUTHENTICATION_SCHEME'] = self.prev_auth_scheme
        super(Test_Gsi, self).tearDown()

    # Try to authenticate before getting a certificate. Make sure this fails.
    def test_authentication_gsi_without_cert(self):
        # Destroy the proxy certs so we can test for failure
        os.system("grid-proxy-destroy")

        # Try an ils and make sure it fails
        self.admin.assert_icommand("ils", 'STDERR_SINGLELINE', "GSI_ERROR_ACQUIRING_CREDS")

    # Try to authenticate after getting a TGT. This should pass
    def test_authentication_gsi_with_cert(self):
        gsiPassword = "irods"

        # Make sure we have a valid proxy cert
        pipe = os.popen("grid-proxy-init -pwstdin", 'w')
        print "Writing password: %s to the grid-proxy-init" % gsiPassword
        pipe.write(gsiPassword)
        pipe.close()

        # Try an iinit
        self.admin.assert_icommand("iinit", 'STDOUT_SINGLELINE', "Using GSI, attempting connection/authentication")

        # Try an ils
        self.admin.assert_icommand("ils", 'STDOUT_SINGLELINE', "home")
