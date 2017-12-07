#! /usr/bin/awk -f
# 2009/07/28  Paul T Sparks

# Extract data from LDIF formatted file and output in CSV format.

BEGIN {
  if (length(taglist) == 0) {
    print "Include -v taglist='tag1,tag1' as an option on the command line" >"/dev/stderr";
    print "Include -v del='~' to change the seperator char to something other than comma" >"/dev/stderr";
    print "Include -v quote=N for no quotes" >"/dev/stderr";
    exit 1;
  }
  if (length(del) == 0) {
      del=",";
  }
  if (length(quote) == 0) {
      quote="\"";
  } else if (quote == "N") {
      quote="";
  }

  if (length(headers) > 0)
      print taglist;
  tags = split(taglist, tag, ",");
  for (i=1; i <= tags; i++) {
    tagref[tag[i]]= i;
  }
}

/^$/ {
  next;
}

/^dn:/ {
  if (hasData == 1) {
    for (i=1; i < tags; i++) {
	printf("%s%s%s%s", quote, vals[i], quote, del);
    }
    printf("%s%s%s\n",quote, vals[tags], quote);
  }
  delete vals;
  hasData = 0;
}

/^[^ ]/ {
  sep = index($0, ": ");
  if (sep == 0)
    next;
  id = substr($0, 1, sep -1);
  value = substr($0, sep +2);
  if (!(id in tagref)) {
    delete tagref[id];
    next;
  }
  vals[tagref[id]]= value;
  hasData = 1;
}

END {
  if (hasData == 1) {
    for (i=1; i < tags; i++) {
	printf("%s%s%s%s", quote, vals[i], quote, del);
    }
    printf("%s%s%s\n",quote, vals[tags], quote);
  }
}
