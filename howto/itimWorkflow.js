
// change the condition to "true" to enable debug
var DEBUG=true;
//var DEBUG=false;

// log a debug message
function debug(msg) {
    if (DEBUG) activity.auditEvent(activity.id +":"+ msg);
}
//log an audit message
function log(msg) {
    activity.auditEvent(activity.id +":"+ msg);
}

/* Dump attributes for a directory object */
function debugDirectoryObject(obj) {
    if (! DEBUG) return;
    var props= obj.getPropertyNames();
    for (var i=0; i < props.length; i++) {
        var attrs= obj.getProperty(props[i]);
        debug("["+ props[i] +"]:"+ attrs);
    }
}


/* Return index of value within an array or -1 if the value does not exists.
Compares values exactly without type conversion.
 */
function arrayIndexOf(arr, value) {
    for (var i=0; i < arr.length; i++) {
        if (arr[i] === value)
            return i;
    }
    return -1;
}


/* Get the ITIM account for a person. Pull all the person's accounts and cycle through them until
the ITIM account is detected based on the service type.
Returns the ITIM Account object or null if not found.
 */
function getPersonITIMAccount(oPerson) {
    var oAccounts = (new AccountSearch()).searchByOwner(oPerson.dn);
    if (oAccounts == null) {
        log("No accounts found for " + oPerson.getProperty("uid"));
        return null;
    }
    for (var i=0; i < oAccounts.length; i++) {
        var oService = new Service(oAccounts[i].getProperty("erservice")[0]);
        if (oService.getProperty("erservicename")[0] == "ITIM Service") {
            return oAccounts[i];
        }
    }
    return null;
}



// Full ITIM API available in 5.1 (Rumored, but NOT!!!)
var dn= new com.ibm.itim.dataservices.model.DistinguishedName(account.get().dn);
var accountEnt= (new com.ibm.itim.dataservices.model.domain.AccountSearch()).lookup(dn);
