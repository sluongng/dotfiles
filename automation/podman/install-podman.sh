#!/bin/bash

# This script is mean to install podman for Ubuntu only
# Work around since Podman only support Ubuntu LTS

sudo add-apt-repository -y "deb http://ppa.launchpad.net/projectatomic/ppa/ubuntu bionic main"
sudo apt update
sudo apt install -y podman
