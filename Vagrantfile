# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/xenial64"

  config.vm.network "forwarded_port", guest: 80, host: 8080

  config.vm.provision "ansible_local" do |ansible|
    ansible.provisioning_path = "/vagrant/ansible"
    ansible.playbook = "provision.yml"
    ansible.raw_arguments = [
      "--extra-vars=@local-secrets.yml",
    ]
    ansible.limit = "server"
    ansible.inventory_path = "vagrant_inventory"
  end
end
