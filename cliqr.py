#! /usr/local/bin/python

# Ansible CliQr dynamic inventory provider
# Copyright 2015, Matt Davis (mdavis+cliqr@ansible.com)

import requests, json, subprocess, os, tempfile, sys, stat

# TODO; support ini file

# If True, persist keys to disk, otherwise, add all keys to ssh agent
# Under Tower, persist_keys=True requires /var/tmp to be in the AWX_PROOT_SHOW_PATHS (or PROOT to be disabled)
persist_keys = True

# plug your CliQr API host and credentials in here (from User Management->Actions->Manage Access Key)
api_host = 'yourhost.cliqr.com'
api_user =  'your_api_user'
api_key = 'your_api_key'

class CliqrInventory():
    def __init__(self, api_hostname, api_user, api_key, api_port=443):
        self.api_base_url = 'https://{0}:{1}/v1/'.format(api_hostname, api_port)
        self.api_user = api_user
        self.api_key = api_key
        self.all_keys = None

    def _api_get(self, resource, params=None):
        headers = {'X-CLIQR-API-KEY-AUTH' : 'true', 'Accept': 'application/json'}
        r = requests.get(self.api_base_url + resource, auth=(self.api_user, self.api_key), headers=headers, params=params)
        r.raise_for_status()

        return r.json()

    def _get_running_jobs(self):
        # TODO: handle pagination- not working as documented...
        jobs = self._api_get('jobs')

        running_jobs = [rj for rj in jobs.get('jobs', []) if rj.get('status', '') == 'Running']

        return running_jobs

    def _get_job_detail(self, job_id):
        job = self._api_get('jobs/{0}'.format(job_id))

        return job

    def _get_user_keys(self):
        user_keys = self._api_get('user/keys')

        return user_keys

    def _add_user_keys_to_agent(self, persist_keys=False):
        ssh_keys = self.all_keys.get('sshKeys')
        for k in ssh_keys:
            if persist_keys:
                filename = '/var/tmp/' + k.get('cloud') + '.pem'
                tempf = open(filename, 'w')
                os.chmod(filename, stat.S_IRWXU)
            else:
                tempfd, filename = tempfile.mkstemp()
                tempf = os.fdopen(tempfd, 'w')
            tempf.write(k.get('key'))
            tempf.close()
            if not persist_keys:
                subprocess.call(['ssh-add',filename])
                os.remove(filename)

    def _walk_job(self, job_detail, hosts, groups):
        appName = job_detail.get('appName', 'unknown')
        parameters = job_detail.get('parameters', dict())
        cloud = parameters.get('cloudParams', dict()).get('cloud', 'unknown')
        # ack, this API is weird- envParams is a list of dicts with key/value contents...
        ssh_user = [p.get('value') for p in parameters.get('appParams', list()) if p.get('name') == 'launchUserName'][0]

        jobVMEntries = job_detail.get('virtualMachines')

        jobHosts = dict()

        cloudHostSet = groups.setdefault('cloud_'+cloud, set())

        for jobVMEntry in jobVMEntries:
            if jobVMEntry.get('status') == 'NodeReady':
                jobHosts[jobVMEntry.get('publicIp')] = dict(
                                          public_ip=jobVMEntry.get('publicIp'),
                                          vm_id=jobVMEntry.get('id'),
                                          cloud=cloud,
                                          ansible_ssh_user=ssh_user,
                                          ansible_ssh_private_key_file='/var/tmp/%s.pem'%cloud
                                         )
                cloudHostSet.add(jobVMEntry.get('publicIp'))

        appHostSet = groups.setdefault('appname_'+appName, set())

        for subjob in job_detail.get('jobs'):
            subjobHosts = dict()
            self._walk_job(subjob, subjobHosts, groups)
            jobHosts.update(subjobHosts)
            appHostSet |= set(subjobHosts.keys())

        # run this after we've walked the subjobs so we'll get all hosts created in subjobs too
        appHostSet |= set(jobHosts.keys())

        hosts.update(jobHosts)

    def get_inventory(self, persist_keys=False):
        self.all_keys = self._get_user_keys()
        running_jobs = self._get_running_jobs()
        running_job_details = [self._get_job_detail(rj.get('id')) for rj in running_jobs]
        self._add_user_keys_to_agent(persist_keys)
        hosts = {}
        groups = {}
        [self._walk_job(j, hosts, groups) for j in running_job_details]

        inv_dict = dict(_meta=dict(hostvars=hosts))
        for groupname, group in groups.iteritems():
            inv_dict[groupname] = dict(hosts=list(group))

        return inv_dict

def main():
    persist_keys = False

    inv = CliqrInventory(api_host, api_user, api_key)

    inv_dict = inv.get_inventory(True)

    print json.dumps(inv_dict)


main()
