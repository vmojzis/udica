#!/bin/python3

import selinux
import semanage

from os import chdir, getcwd

import udica.perms as perms

CONFIG_CONTAINER = '/etc'
HOME_CONTAINER = '/home'
LOG_CONTAINER = '/var/log'
TMP_CONTAINER = '/tmp'

TEMPLATES_STORE = '/usr/share/udica/templates'

templates_to_load = []

def add_template(template):
    templates_to_load.append(template)

def list_templates_to_string(templates_to_load):
    return '.cil,'.join(map(str, templates_to_load)) + '.cil'

def list_contexts(directory):
    directory_len = (len(directory))

    handle = semanage.semanage_handle_create()
    semanage.semanage_connect(handle)

    (rc, fclist) = semanage.semanage_fcontext_list(handle)
    (rc, fclocal) = semanage.semanage_fcontext_list_local(handle)
    (rc, fchome) = semanage.semanage_fcontext_list_homedirs(handle)

    contexts = []
    for fcontext in fclist + fclocal + fchome:
        expression = semanage.semanage_fcontext_get_expr(fcontext)
        if expression[0:directory_len] == directory:
            context = semanage.semanage_fcontext_get_con(fcontext)
            if context:
                contexts.append(semanage.semanage_context_get_type(context))

    selabel = selinux.selabel_open(selinux.SELABEL_CTX_FILE, None, 0)
    (rc, context) = selinux.selabel_lookup(selabel, directory, 0)
    contexts.append(context.split(':')[2])
    return contexts

def list_ports(port_number):

    handle = semanage.semanage_handle_create()
    semanage.semanage_connect(handle)

    (rc, plist) = semanage.semanage_port_list(handle)
    (rc, plocal) = semanage.semanage_port_list_local(handle)

    for port in plist + plocal:
        con = semanage.semanage_port_get_con(port)
        ctype = semanage.semanage_context_get_type(con)
        low = semanage.semanage_port_get_low(port)
        if (low == port_number):
            return ctype

def create_policy(opts,capabilities,mounts,ports):
    policy = open(opts['ContainerName'] +'.cil', 'w')
    policy.write('(block ' + opts['ContainerName'] + '\n')
    policy.write('    (blockinherit container)\n')
    add_template("base_container");

    if opts['FullNetworkAccess']:
        policy.write('    (blockinherit net_container)\n')
        add_template("net_container");

    if opts['XAccess']:
        policy.write('    (blockinherit x_container)\n')
        add_template("x_container");

    if opts['TtyAccess']:
        policy.write('    (blockinherit tty_container)\n')
        add_template("tty_container");

    if ports:
        policy.write('    (blockinherit restricted_net_container)\n')
        add_template("net_container");

    # capabilities
    if capabilities:
        caps=''
        for item in capabilities:
            caps = caps + perms.cap[item]

        policy.write('    (allow process process ( capability ( ' + caps  + '))) \n')
        policy.write('\n')

    # ports
    for item in ports:
        policy.write('    (allow process ' + list_ports(item['hostPort']) + ' ( ' + perms.socket[item['protocol']] + ' (  name_bind ))) \n')

    # mounts
    for item in mounts:
        if not item['source'].find("/"):
            if (item['source'] == LOG_CONTAINER and 'ro' in item['options']):
                policy.write('    (blockinherit log_container)\n')
                add_template("log_container");
                continue;

            if (item['source'] == LOG_CONTAINER and 'rw' in item['options']):
                policy.write('    (blockinherit log_rw_container)\n')
                add_template("log_container");
                continue;

            if (item['source'] == HOME_CONTAINER and 'ro' in item['options']):
                policy.write('    (blockinherit home_container)\n')
                add_template("home_container");
                continue;

            if (item['source'] == HOME_CONTAINER and 'rw' in item['options']):
                policy.write('    (blockinherit home_rw_container)\n')
                add_template("home_container");
                continue;

            if (item['source'] == TMP_CONTAINER and 'ro' in item['options']):
                policy.write('    (blockinherit tmp_container)\n')
                add_template("tmp_container");
                continue;

            if (item['source'] == TMP_CONTAINER and 'rw' in item['options']):
                policy.write('    (blockinherit tmp_rw_container)\n')
                add_template("tmp_container");
                continue;

            if (item['source'] == CONFIG_CONTAINER and 'ro' in item['options']):
                policy.write('    (blockinherit config_container)\n')
                add_template("config_container");
                continue;

            if (item['source'] == CONFIG_CONTAINER and 'rw' in item['options']):
                policy.write('    (blockinherit config_rw_container)\n')
                add_template("config_container");
                continue;

            contexts = list_contexts(item['source'])
            for context in contexts:
                if 'rw' in item['options']:
                    policy.write('    (allow process ' + context + ' ( dir ( ' + perms.perm['drw'] + ' ))) \n')
                    policy.write('    (allow process ' + context + ' ( file ( ' + perms.perm['frw'] + ' ))) \n')
                    policy.write('    (allow process ' + context + ' ( sock_file ( ' + perms.perm['srw'] + ' ))) \n')
                if 'ro' in item['options']:
                    policy.write('    (allow process ' + context + ' ( dir ( ' + perms.perm['dro'] + ' ))) \n')
                    policy.write('    (allow process ' + context + ' ( file ( ' + perms.perm['fro'] + ' ))) \n')
                    policy.write('    (allow process ' + context + ' ( sock_file ( ' + perms.perm['sro'] + ' ))) \n')

    policy.write(') ')
    policy.close()

def load_policy(opts):
    PWD = getcwd()
    chdir(TEMPLATES_STORE)

    if opts['LoadModules']:
        handle = semanage.semanage_handle_create()
        semanage.semanage_connect(handle)

        for template in templates_to_load:
            semanage.semanage_module_install_file(handle, template + '.cil')

        chdir(PWD)

        semanage.semanage_module_install_file(handle, opts['ContainerName'] + '.cil')

        semanage.semanage_commit(handle)
    else:
        templates = list_templates_to_string(templates_to_load)
        print('\nPlease load these modules using: \n# semodule -i ' + opts['ContainerName'] + '.cil ' + TEMPLATES_STORE + "/{" + templates + '}')
