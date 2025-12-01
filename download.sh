#!/bin/bash

wget https://github.com/IlyaGusev/memetron3000/releases/download/resources/images.tar.gz
mkdir -p images && cd images && cp ../images.tar.gz . && tar -xzvf images.tar.gz && cd ..
rm -f images/images.tar.gz


