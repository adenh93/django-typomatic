#!/usr/bin/env bash
set -u

PYTHON_VERSION="3.6.8"
VIRTUAL_ENV_NAME="django-typomatic"

# Create the virtual environment and set it as the one to use
echo "Creating pyenv virtual environment and installing packages..."
pyenv install --skip-existing "${PYTHON_VERSION}"
pyenv virtualenv "${PYTHON_VERSION}" "${VIRTUAL_ENV_NAME}"
pyenv local "${VIRTUAL_ENV_NAME}" system