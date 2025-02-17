#!/bin/bash

wget https://github.com/IlyaGusev/memetron3000/releases/download/resources/videos.tar.gz
tar -xzvf videos.tar.gz
rm -f videos.tar.gz

git clone https://github.com/jacebrowning/memegen
cd memegen/templates && wget https://github.com/IlyaGusev/memetron3000/releases/download/resources/templates.tar.gz && tar -xzvf templates.tar.gz && cd ../..
rm -f memegen/templates/templates.tar.gz
