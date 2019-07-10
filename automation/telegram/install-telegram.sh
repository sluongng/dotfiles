#!/bin/bash -e

# Github configuration
GITHUB_USER='telegramdesktop'
GITHUB_PROJECT='tdesktop'

# Opt dir configuration
TAR_NAME='tsetup.tar.xz'
OPT_DIR='/opt/'
TAR_DIR="${OPT_DIR}${TAR_NAME}"

# Extract latest build URL
## This script uses jq from https://github.com/stedolan/jq
URL=`curl -s "https://api.github.com/repos/${GITHUB_USER}/${GITHUB_PROJECT}/releases/latest" \
	| jq -r '.assets[].browser_download_url' \
	| grep 'tsetup\..*.tar.xz'`

if [[ ! -z "${URL}" ]] ; then

	echo "Latest build is ${URL}"

	# Download file from latest Github release
	echo 'Downloading latest build'
	curl -sL -o ${TAR_NAME} ${URL}
	echo 'Download finished'

	# If download success, install Telegram
	if [[ -f "${TAR_NAME}" ]] ; then

		mkdir --parents ${OPT_DIR}
		sudo mv ${TAR_NAME} ${OPT_DIR}

		echo 'Extracting build'
		tar xf ${TAR_DIR} -C ${OPT_DIR}

		echo 'Cleaning up install file'
		rm -rf ${TAR_DIR}

	else
		echo "Could not find ${TAR_NAME}"
	fi

else
	echo 'Could not find latest build! Check the script/github api.'
fi
