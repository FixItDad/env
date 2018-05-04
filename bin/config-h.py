#!/usr/bin/python

# Implement an inheritance style configuration scheme in a single file. This is
# primarily aimed at Linux shell programmers with a var=value assignment syntax.
# This program may be useful for shell scripts that use similiar configuration
# parameters for different functions or in different environments. Rather than
# creating many small configuration files for each flavor of operation, the
# variable configurations can be represented clearly in a single file.

# Usage: config-h.py <config file> <definition name>
# Outputs 'var=value' lines to stdout according to the definition selected.
# Blank lines and lines starting with '#' (comments) are ignored.
# Each "definition" is a set of var=value lines. Whitespace around the '=' is removed.
# The program outputs var=value lines of the resulting configuration set.
# An example would probably be clearer:

#DEFINE T0
#var1 = valueA
#var2 = valueB
#var3 = valueC
#
#DEFINE T1 FROM T0
#var2 = value ZZZ
#
#DEFINE T2 FROM T0
#var3="new value"
#
#DEFINE S
#abc=123
#def=987
#
#DEFINE T FROM S
#abc=777


# With the example.conf file above, 'eval $(config-h.py example.conf T2)'
# would result in the following shell variables being defined:
# 
# var1=valueA
# var2=valueB
# var3="new value"
#
# 'config-h.py example.conf T' would output
# abc=777
# def=987

# 2018-05-04 Paul T Sparks

import copy
import sys

def abort(msg):
    print >>sys.stderr, msg
    sys.exit(1)

def log(*args):
    sys.stderr.write(' '.join(map(str,args))+'\n')


conf = sys.argv[2]
log("Getting config for",conf)
definitions = {}
count = 0
with open(sys.argv[1]) as f:
    for line in f:
        count += 1;
        if len(line.strip()) < 1 or line.lstrip().startswith("#"):
            continue
        if line.startswith("DEFINE "):
            vals = line[:-1].split()
            if len(vals) < 2: 
                abort("line %d missing name" % count)
            name = vals[1]
            log("name=",name)
            if len(vals) > 3 and vals[2] == "FROM":
                fromdef = vals[3]
                if fromdef not in definitions: 
                    abort('line %d "from" name undefined' % count)
                definitions[name] = copy.deepcopy(definitions[fromdef])
        else:
            if not name:
                abort('line %d missing DEFINE statement' % count)
            vals = line[:-1].split("=", 1)
            if len(vals) < 2:
                abort('line %d missing "=" in parameter definition' % count)
            if name not in definitions: definitions[name] = {}
            log("update",name,vals[0].strip(),vals[1].lstrip())
            definitions[name][vals[0].strip()]= vals[1].lstrip()

if conf not in definitions:
    abort('requested configuration is undefined' % count)
for i in definitions[conf].keys():
    print "%s=%s" % (i,definitions[conf][i])
