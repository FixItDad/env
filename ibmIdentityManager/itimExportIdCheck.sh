#!/usr/bin/ksh

#run in the extracted export jar file directory

cat *.xml |sed -e 's/="/\
/g' |grep "^.*id\.[0-9]" |sed -e 's/".*//' | sort -u >ids

grep "^#" ids |sed -e 's/#//' >refs
grep -v "^#" ids >defs
comm -3 defs refs
