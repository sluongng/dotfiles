#!/bin/bash -e

# Github configuration
GITHUB_USER='sharkdp'
GITHUB_PROJECT='fd'

# Opt dir configuration
FILE_NAME='fd_amd64.deb'

# Extract latest build URL
## This script uses jq from https://github.com/stedolan/jq
URL=`curl -s "https://api.github.com/repos/${GITHUB_USER}/${GITHUB_PROJECT}/releases/latest" \
	| jq -r '.assets[].browser_download_url' \
	| grep 'fd_.*_amd64.deb' `

if [[ ! -z "${URL}" ]] ; then
 
	echo "Latest build is ${URL}"
 
 	# Download file from latest Github release
 	echo 'Downloading latest build'
 	curl -sL -o ${FILE_NAME} ${URL}
 	echo 'Download finished'
 
 	# If download success, install Telegram
 	if [[ -f "${FILE_NAME}" ]] ; then
 
 		echo 'Installing build'
		sudo dpkg -i ${FILE_NAME}
 
		echo `which fd`
 
 	else
 		echo "Could not find ${TAR_NAME}"
 	fi
 
else
 	echo 'Could not find latest build! Check the script/github api.'
fi

echo 'Cleaning up install file'
if [[ -f "${FILE_NAME}"	]] ; then

	rm -f ${FILE_NAME}

fi
