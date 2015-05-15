# CliQr Dynamic Inventory for Ansible
This is a quick-and-dirty attempt at an Ansible dynamic inventory script for CliQr. 

##Use:
Look up your CliQr API username and key (under User Management->Actions->Manage Access Key) and plug them in at the top of cliqr.py, along with your Cliqr hostname. Reference cliqr.py as your inventory when running Ansible.

##SSH credentials:
Since CliQr manages the SSH keys, the inventory script will download all your user keys and add them to your local SSH agent automatically. 

###Known issues:
* The sudo password doesn't appear to be exposed via the CliQr API. This prevents Ansible from doing much of anything useful.
* Should have an ini file.
* Auto-agent add on the SSH keys is kinda nasty.
* Only implements the optimized "_meta" style inventory script (eg, no support for older-style --host/--list).