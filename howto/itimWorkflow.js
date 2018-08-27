
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


// Check to see if the value is all digits
function isDigits(val) {
    var instr=val.toString();
    for (var i=0; i< instr.length; i++) {
        var c= instr.charAt[i];
        if (c <'0' || c > '9')
            return false;
    }
    return true;
}

/* Calculate days in the month of Febuary for a given year.
29 days if year evenly divisible by 4 except for century years that are
not evenly divisible by 400. Otherwise 28.
 */
function daysInFebuary(year) {
    return (((year%4 == 0) && ((!(year%100 == 0)) || (year%400 == 0))) ? 29 : 28);
}

/* Check to see if the value passed (yyyy-mm-dd) actually makes a valid
date.  The Javascript Date object routines don't actually check the
values passed in, so check manually. Input value should be syntactically correct.
*/
function isDate(val) {
    var daysInMonth = new Array(31,31,29,31,30,31,30,31,31,30,31,30,31);
    var mon = parseInt(val.substring(5,7));
    var day = parseInt(val.substring(8,10));
    var year = parseInt(val.substring(0,4));
    if ((mon < 1) && (mon > 12))
        return false;
    var days= daysInMonth[mon]
    if (mon == 2) 
        var days= daysInFebuary(year);
    debug("year="+ year +" mon="+ mon +" day="+ day +" days="+ days);
    return ((mon <= 12) && (day <= days));
}

// Format that user is expected to enter in the ITIM console form
var ISO_FORMAT="yyyy-mm-dd";
var ISO_LEN= ISO_FORMAT.length;

function isValidISODate(val) {
    if ((val.length != ISO_LEN) || (val.charAt(4) != '-') || (val.charAt(7) != '-')) {
        debug("bad length or missing dashes:"+ val);
        return false;
    }
    tmp= val.substring(0,4)+ val.substring(5,7)+ val.substring(8,10);
    if (!isDigits(tmp)) {
        debug("Not all digits");
        return false;
    }
    return isDate(val);
}


/* Check a date for validity and fail the activity if it is not valid. */
function checkDate(attrName, object) {
    var dtA= object.getProperty(attrName);
    if (dtA.length == 0) // no value
        return;
    var dt= object.getProperty(attrName)[0];
    debug("checking date:"+ dt);
    if (! isValidISODate(dt)) {
        log("Bad date ("+ dt +") for attribute "+ attrName);
        activity.setResult(activity.FAILED, "Bad date ("+ dt +") for attribute "+ attrName);
        process.setResult(process.FAILED, "Bad date ("+ dt +") for attribute "+ attrName);
    }
}


/* Convert YYYY-MM-DD format to ITIM's generalizedTime format. Returns null if
the passed string is not valid. 
Regular expressions were not working, so did it the hard way...
 */
function gfipmDateToGeneralizedTime(gDate) {
    debug("Date to convert:"+ gDate);
    var test= gDate.substr(0,4)+ gDate.substr(5,2)+ gDate.substr(8,2);
    if (test.length != 8 && gDate.charAt(4) != '-' && gDate.charAt(7) != '-') {
        log("Bad date format for:"+ gDate);
        return null;
    }
    for (var i=0; i < test.length; i++) {
        if (test.charAt(i) < '0' || test.charAt(i) >'9') {
            log("Bad date format for:"+ gDate);
            return null;
        }
    }
    return test +"000000Z";
}


/* Return index of value within an array or -1 if the value does not exists.
Compares values exactly without type conversion.
 */
function arrayIndexOf(arr, value) {
    for (var i=0; i < arr.length; i++) {
        debug("Checking: "+ arr[i] +" = "+ value);
        if (arr[i] === value)
            return i;
    }
    debug("Value not found in array");
    return -1;
}

/* Combines altphone with telephonenumber values in a single array.
Avoids duplicate values.
 */
function combinePhoneNumbers(person) {
    var newPhones= new Array();
    var oldPhones= person.getProperty("telephonenumber");
    for (var i=0; i < oldPhones.length; i++) {
        newPhones[newPhones.length]= oldPhones[i];
    }

    var altPhones= person.getProperty("altphone");
    for (var i=0; i < altPhones.length; i++) {
        if (-1 == arrayIndexOf(newPhones, altPhones[i]))
            newPhones[newPhones.length]= altPhones[i];
    }
    return newPhones;
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
