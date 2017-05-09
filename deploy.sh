#!/bin/bash

ROOT="$(readlink -f "$(dirname "${BASH_SOURCE[0]}")")"
cd $ROOT

set -e
trap "rm vault.pw" SIGINT SIGTERM EXIT

echo $ANSIBLE_VAULT_PASSWORD > vault.pw

ANSIBLE_LIBRARY="$ROOT/ansible/library" \
ansible-playbook \
  --vault-password-file=vault.pw \
  --extra-vars=@ansible/secrets.yml \
  ansible/deploy.yml
