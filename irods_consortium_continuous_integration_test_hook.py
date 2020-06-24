from __future__ import print_function

import optparse
import abc
import json
import os
import pwd
import shutil
import glob
import time
import subprocess

import irods_python_ci_utilities


def get_test_prerequisites_apt():
    return 'globus-toolkit-repo_latest_all.deb'

def get_test_prerequisites_yum():
    return 'globus-toolkit-repo-latest.noarch.rpm'

def get_test_prerequisites():
    dispatch_map = {
        'Ubuntu': get_test_prerequisites_apt,
        'Centos': get_test_prerequisites_yum,
        'Centos linux': get_test_prerequisites_yum
    }
    try:
        return dispatch_map[irods_python_ci_utilities.get_distribution()]()
    except KeyError:
        irods_python_ci_utilities.raise_not_implemented_for_distribution()

def do_globus_config():
    irods_python_ci_utilities.subprocess_get_output(['sudo', 'chmod', 'o+rx', '/home/irodsbuild'], check_rc=True) # so user simpleca can read ~irodsbuild/.globus/usercert_request.pem
    irodsbuild_password = create_irodsbuild_certificate()
    create_irods_certificate()
    generate_proxy('irodsbuild', irodsbuild_password)
    generate_proxy('irods', None)
    irodsbuild_proxy_copy = make_irods_readable_copy_of_irodsbuild_proxy()
    irodsbuild_distinguished_name = get_irodsbuild_distinguished_name()
    create_test_configuration_json(irodsbuild_proxy_copy, irodsbuild_distinguished_name)

def create_irodsbuild_certificate():
    irods_python_ci_utilities.subprocess_get_output(['sudo', 'su', '-', 'irodsbuild', '-c', 'grid-cert-request -nopw -force -cn gsi_client_user'], check_rc=True)
    irods_python_ci_utilities.subprocess_get_output(['sudo', 'chmod', 'u+w', '/home/irodsbuild/.globus/userkey.pem'], check_rc=True)
    private_key_password = 'gsitest'
    irods_python_ci_utilities.subprocess_get_output(['openssl', 'rsa', '-in', '/home/irodsbuild/.globus/userkey.pem', '-out', '/home/irodsbuild/.globus/userkey.pem', '-des3', '-passout', 'pass:{0}'.format(private_key_password)], check_rc=True)
    irods_python_ci_utilities.subprocess_get_output(['sudo', 'chmod', '400', '/home/irodsbuild/.globus/userkey.pem'], check_rc=True)

    temporary_certificate_location = '/tmp/gsicert'
    irods_python_ci_utilities.subprocess_get_output(['sudo', 'su', '-s', '/bin/bash', '-c', 'grid-ca-sign -in /home/irodsbuild/.globus/usercert_request.pem -out {0}'.format(temporary_certificate_location), 'simpleca'], check_rc=True)

    irods_python_ci_utilities.subprocess_get_output(['sudo', 'cp', temporary_certificate_location, '/home/irodsbuild/.globus/usercert.pem'], check_rc=True)
    irods_python_ci_utilities.subprocess_get_output(['sudo', 'rm', temporary_certificate_location], check_rc=True)
    return private_key_password

def create_irods_certificate():
    irods_python_ci_utilities.subprocess_get_output(['sudo', 'su', '-', 'irods', '-c', 'grid-cert-request -nopw -force -cn irods_service'], check_rc=True)

    temporary_certificate_location = '/tmp/gsicert'
    irods_python_ci_utilities.subprocess_get_output(['sudo', 'su', '-s', '/bin/bash', '-c', 'grid-ca-sign -in /var/lib/irods/.globus/usercert_request.pem -out {0}'.format(temporary_certificate_location), 'simpleca'], check_rc=True)

    irods_python_ci_utilities.subprocess_get_output(['sudo', 'cp', temporary_certificate_location, '/var/lib/irods/.globus/usercert.pem'], check_rc=True)
    irods_python_ci_utilities.subprocess_get_output(['sudo', 'rm', temporary_certificate_location], check_rc=True)

def generate_proxy(username, password):
    if password:
        irods_python_ci_utilities.subprocess_get_output(['sudo', 'su', '-', username, '-c' 'echo {0} | grid-proxy-init -pwstdin'.format(password)], check_rc=True)
    else:
        irods_python_ci_utilities.subprocess_get_output(['sudo', 'su', '-', username, '-c' 'grid-proxy-init'], check_rc=True)

def make_irods_readable_copy_of_irodsbuild_proxy():
    uid = pwd.getpwnam('irodsbuild').pw_uid
    proxy_file = '/tmp/x509up_u' + str(uid)
    irods_copy_of_proxy = '/tmp/irods_copy_of_irodsbuild_gsi_proxy'
    irods_python_ci_utilities.subprocess_get_output(['sudo', 'cp', proxy_file, irods_copy_of_proxy], check_rc=True)
    irods_python_ci_utilities.subprocess_get_output(['sudo', 'chown', 'irods:irods', irods_copy_of_proxy], check_rc=True)
    return irods_copy_of_proxy

def get_irodsbuild_distinguished_name():
    _, name, _ = irods_python_ci_utilities.subprocess_get_output(['sudo', 'su', '-', 'irodsbuild', '-c', 'grid-cert-info -subject'], check_rc=True)
    return name.strip()

def create_test_configuration_json(irodsbuild_proxy_copy, irodsbuild_distinguished_name):
    config = {'client_user_proxy': irodsbuild_proxy_copy,
              'client_user_DN': irodsbuild_distinguished_name}
    config_file = '/tmp/gsi_test_cfg.json'
    with open(config_file, 'w') as f:
        json.dump(config, f)
    irods_python_ci_utilities.subprocess_get_output(['sudo', 'chmod', '777', config_file], check_rc=True)

def install_testing_dependencies():
    irods_python_ci_utilities.subprocess_get_output(['sudo', '-EH', 'pip', 'install', 'unittest-xml-reporting==1.14.0'])
    globus_toolkit_package_name = get_test_prerequisites()
    if irods_python_ci_utilities.get_distribution() == 'Ubuntu':
        package_repo = 'deb'
    elif irods_python_ci_utilities.get_distribution() == 'Centos linux':
        package_repo = 'rpm'

    irods_python_ci_utilities.subprocess_get_output(['wget', 'http://downloads.globus.org/toolkit/gt6/stable/installers/repo/{0}/{1}'.format(package_repo ,globus_toolkit_package_name)], check_rc=True)
    irods_python_ci_utilities.install_os_packages_from_files([globus_toolkit_package_name])
    if irods_python_ci_utilities.get_distribution() == 'Ubuntu':
        subprocess.check_call(['apt-get', 'update'])
    if irods_python_ci_utilities.get_distribution() == 'Centos linux':
        subprocess.check_call(['yum', 'install', '-y', 'epel-release'])
        subprocess.check_call(['yum', 'update'])
    irods_python_ci_utilities.install_os_packages(['globus-simple-ca', 'globus-gsi'])

def main():
    parser = optparse.OptionParser()
    parser.add_option('--output_root_directory')
    parser.add_option('--built_packages_root_directory')
    options, _ = parser.parse_args()

    output_root_directory = options.output_root_directory
    built_packages_root_directory = options.built_packages_root_directory
    package_suffix = irods_python_ci_utilities.get_package_suffix()
    os_specific_directory = irods_python_ci_utilities.append_os_specific_directory(built_packages_root_directory)

    install_testing_dependencies()
    irods_python_ci_utilities.install_os_packages_from_files(glob.glob(os.path.join(os_specific_directory, 'irods-auth-plugin-gsi*.{0}'.format(package_suffix))))
    do_globus_config()

    time.sleep(10)

    try:
        test_output_file = 'log/test_output.log'
        irods_python_ci_utilities.subprocess_get_output(['sudo', 'su', '-', 'irods', '-c', 'python2 scripts/run_tests.py --xml_output --run_s=test_irods_auth_plugin_gsi 2>&1 | tee {0}; exit $PIPESTATUS'.format(test_output_file)], check_rc=True)
    finally:
        if output_root_directory:
            irods_python_ci_utilities.gather_files_satisfying_predicate('/var/lib/irods/log', output_root_directory, lambda x: True)
            shutil.copy('/var/lib/irods/log/test_output.log', output_root_directory)
            shutil.copytree('/var/lib/irods/test-reports', os.path.join(output_root_directory, 'test-reports'))


if __name__ == '__main__':
    main()
