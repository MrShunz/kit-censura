#!/bin/bash -x

echo "Creating new empty files..."

touch lista.agcom
touch lista.consob
touch lista.manuale
touch lista.manuale-ip

echo "Creating dirs..."
mkdir -p tmp lists gpg
