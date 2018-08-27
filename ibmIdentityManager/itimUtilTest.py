#!/bin/env python

# Unit tests for itimUtil.sh / itimUtil.py

# 2013-07-23 Paul T Sparks

import Queue
import ldap
import os
import os.path
import sys
import tempfile
import time
import unittest


# ITIM search base in LDAP
ITIM_BASE='dc=itim'

# Default LDAP login ID
LDAP_ID= 'cn=root'

TEST_UID= 'atest2'
TEST_UID2= 'asparks1'


# ITIM status values
ITIM_ACTIVE='0'
ITIM_INACTIVE='1'

def log(*args):
    print >> sys.stderr, ' '.join(map(str,args))

def verifyEnvVars(varList):
    missing= 0
    for var in varList:
        if not (var in os.environ.keys()):
            missing += 1
            log(var, 'not defined. Use: export %s=' % var)
    if missing > 0:
        raise AssertionError('Missing test environment configuration')

# LDAP connection pool. Just use the standard Python Queue to manage connections.
LDAP_CONNECTION_POOL_SIZE = 1
_ldapPool= Queue.Queue(LDAP_CONNECTION_POOL_SIZE)

_binDir= None

# Wait a short time for ITIM objects to syncronize (across the cluster?)
# TODO: hopefully remove this code after fixing "restore" functionality
def waitForItimSync(seconds=60):
    time.sleep(seconds)


def testSetup():
    global _binDir
    verifyEnvVars(('USER_ID','USER_PW','PLATFORM_PW','LDAP_PW', 'LDAP_URL'))
    ldapid= os.getenv('LDAP_ID', LDAP_ID)
    ldapurl= os.getenv('LDAP_URL')
    ldappw= os.getenv('LDAP_PW')

    # Initialize LDAP connection pool
    for i in range(LDAP_CONNECTION_POOL_SIZE):
        l = ldap.initialize(ldapurl)
        l.simple_bind_s(ldapid, ldappw)
        _ldapPool.put(l)

    import __main__ as main
    _binDir= os.path.dirname(main.__file__)




# Do an LDAP search for a single object
# Raise an exception if no results or more than 1 result is found.
# Returns the LDAP (dn, attributes) tuple for the object.
# Uses ldapConnection if supplied, otherwise uses a connection from the pool.
def ldapGetObject(base, searchFilter, ldapConnection=None):
    conn= ldapConnection
    try:
        if not ldapConnection:
            conn= _ldapPool.get()
        results_id= conn.search(base, ldap.SCOPE_SUBTREE, searchFilter, None)
        rType, rData= conn.result(results_id, 0)
        if rData == []:
            raise ldap.NO_SUCH_OBJECT('No object %s in base=%s' % (searchFilter, base))
        if rType != ldap.RES_SEARCH_ENTRY:
            raise ldap.LDAPError('Unexpected search type %s data:'% (rType, rData))
        result= rData[0]
        rType, rData= conn.result(results_id, 0)
        if rData != []:
            raise ldap.MORE_RESULTS_TO_RETURN('Found more than 1 result for %s in %s' % (searchFilter, base))
    finally:
        if not ldapConnection:
            _ldapPool.put(conn)
    return (result[0], ldap.cidict.cidict(result[1]))

# Do an LDAP search for objects
# Returns list of LDAP (dn, attributes) tuples
def ldapGetObjects(base, searchFilter, ldapConnection=None):
    conn= ldapConnection
    if not ldapConnection:
        conn= _ldapPool.get()

    results=[]
    results_id= conn.search(base, ldap.SCOPE_SUBTREE, searchFilter, None)
    while True:
        rType, rData= conn.result(results_id, 0)
        if rData == []:
            break
        if rType != ldap.RES_SEARCH_ENTRY:
            log('Got unexpected search type '+ rType +' data:'+ rData)
            return None
        for i in rData:
            results.append((i[0], ldap.cidict.cidict(i[1])))

    if not ldapConnection:
        _ldapPool.put(conn)
    return results


# Perform a synchronous LDAP modify if the dry-run option is not specified.
# Logs some details of the modification for human inspection.
def ldapModify(dn, modList, ldapConnection=None):
    conn= ldapConnection
    if not ldapConnection:
        conn= _ldapPool.get()
    msg= 'Updating dn: '+ dn +' attribute(s):'
    for i in modList:
        msg+= ' '+ i[1]
    log(msg)
    try:
        conn.modify_s(dn, modList)
    except ldap.LDAPError, e:
        log(e)
    if not ldapConnection:
        _ldapPool.put(conn)
    return

def executeItimUtil(data):
    fd, filename = tempfile.mkstemp('.itimUtilTest')
    tempf= os.fdopen(fd, 'w')
    tempf.write(data)
    tempf.close()

    logfile= '/tmp/itimUtilTest.log'
    command=_binDir + os.sep +'itimUtil.sh -o %s %s %s' % (logfile, os.environ['USER_ID'], filename)
    print >> sys.stderr, 'Executing command:', command
    status= os.system(command)
    assert (0 == status), 'Bad status %s for command %s' % (status, command)
    os.unlink(filename)
    return



# Do an assertion for equality of 2 lists.
# Values must be the same and in the same order.
def assertListEqual(expectedList, actualList, description):
    msg='%s values:Expected %s got %s.' % (description, expectedList, actualList)
    assert (0 == cmp(expectedList, actualList)), msg


class ServiceAttrTestCase(unittest.TestCase):
    # erservicename of the service object we are testing with
    testServiceName= 'vcc monitor'
    # attributes to manipulate
    testAttr='description'
    testAttr2='eritdiurl'

    # DN and attribute values of the service object
    svcDn= None
    avcAttr= None
    # LDAP filter for the service object
    filter= None
    # test values. Hopefully unique
    val1='QzzpJJrf9Zz--='
    val2='9p8h34wr,mb 67zf4'
    val3='(*Hkser7yh3dWEjks'

    # Save object attributes the first time through so we can restore the object at the end
    def setUp(self):
        if not self.svcDn:
            self.filter= '(erservicename=%s)' % self.testServiceName
            self.svcDn, self.svcAttr= ldapGetObject(ITIM_BASE, self.filter)
            assert self.svcDn, 'Service not found'
            assert self.svcAttr, 'No Service attributes'
    
    # Test adding atributes
    def testAdd(self):
        expectedVals= list(self.svcAttr[self.testAttr])

        expectedVals.append(self.val1)
        executeItimUtil("serviceAttr~%s~{'add':{'%s':'%s'}}\n" % (self.filter, self.testAttr, self.val1))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual(expectedVals, attr[self.testAttr], self.filter +' '+ self.testAttr)

        expectedVals.append(self.val2)
        expectedVals.append(self.val3)
        executeItimUtil("serviceAttr~%s~{'Add':{'%s':['%s','%s']}}\n" % 
                        (self.filter, self.testAttr, self.val2, self.val3))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual(expectedVals, attr[self.testAttr], self.filter +' '+ self.testAttr)


    # Test removal of all attribute values
    def testDel(self):
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assert (attr[self.testAttr]), '%s attribute is empty' % self.testAttr

        executeItimUtil("serviceAttr~%s~{'del': ['%s']}\n" % (self.filter, self.testAttr))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assert (not self.testAttr in attr.keys()), 'unexpected values for '+ self.testAttr +':'+ str(attr[self.testAttr])


    # Test removal of all attribute values for 2 attributes at one time.
    def testDel2(self):
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assert (attr[self.testAttr]), '%s attribute is empty' % self.testAttr

        executeItimUtil("serviceAttr~%s~{'del':['%s','%s']}\n" % (self.filter, self.testAttr, self.testAttr2))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assert (not self.testAttr in attr.keys()), 'unexpected values for '+ self.testAttr +':'+ str(attr[self.testAttr])
        assert (not self.testAttr2 in attr.keys()), 'unexpected values for '+ self.testAttr2 +':'+ str(attr[self.testAttr2])


    # Test replacement of attribute values (single and multiple attributes and values)
    def testRep(self):
        executeItimUtil("serviceAttr~%s~{'rep':{'%s':'%s'}}\n" % (self.filter, self.testAttr, self.val1))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val1], attr[self.testAttr], self.filter +' '+ self.testAttr)
        
        executeItimUtil("serviceAttr~%s~{'rep':{'%s':['%s','%s']}}\n" % 
                        (self.filter, self.testAttr, self.val2, self.val3))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val2, self.val3], attr[self.testAttr], self.filter +' '+ self.testAttr)

        executeItimUtil("serviceAttr~%s~{'rep':{'%s':'%s', '%s':'%s'}}\n" % 
                        (self.filter, self.testAttr, self.val1, self.testAttr2, self.val2))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val1], attr[self.testAttr], self.filter +' '+ self.testAttr)
        assertListEqual([self.val2], attr[self.testAttr2], self.filter +' '+ self.testAttr2)
        
        executeItimUtil("serviceAttr~%s~{'rep':{'%s':['%s','%s'], '%s':'%s'}}\n" % 
                        (self.filter, self.testAttr, self.val2, self.val3, self.testAttr2, self.val1))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val2, self.val3], attr[self.testAttr], self.filter +' '+ self.testAttr)
        assertListEqual([self.val1], attr[self.testAttr2], self.filter +' '+ self.testAttr2)


    # Restore our test object
    def tearDown(self):
        modList= [(ldap.MOD_REPLACE, self.testAttr , self.svcAttr[self.testAttr]),
                  (ldap.MOD_REPLACE, self.testAttr2 , self.svcAttr[self.testAttr2])]
        ldapModify(self.svcDn, modList)


class PersonAttrOpTestCase(unittest.TestCase):
    # DN and attribute values of the person object
    objDn= None
    objAttr= None

    # test attribute names
    attr1='title'
    attr2='altmail'

    # LDAP filter for the person object
    filter= None
    # test values. Hopefully unique
    val1='QzzpJJrf9Zz--='
    val2='9p8h34wr,mb 67zf4'
    val3='Hkser7yh3dWEjks'
    val4='k7sdfII67gw34r  +'

    # Save object attributes the first time through so we can restore the object at the end
    def setUp(self):
        if not self.objDn:
            self.filter= '(&(uid=%s)(objectclass=erpersonitem))' % TEST_UID
            self.objDn, self.objAttr= ldapGetObject(ITIM_BASE, self.filter)
            assert self.objDn, 'Person not found'
            assert self.objAttr, 'No Person attributes'
            assert (self.attr1 in self.objAttr), 'Test user has no value for attribute:'+ self.attr1
            assert (self.attr2 in self.objAttr), 'Test user has no value for attribute:'+ self.attr2


    # Test replacement of attribute values (single and multiple attributes and values)
    def testAttributeChanges(self):
        try:
            executeItimUtil("personAttrRep~%s~{'%s':'%s'}\n" % (self.filter, self.attr1, self.val4))
            dn, attr= ldapGetObject(ITIM_BASE, self.filter)
            assertListEqual([self.val4], attr[self.attr1], self.filter +' '+ self.attr1)
            waitForItimSync()
        except Exception:
            modList= [(ldap.MOD_REPLACE, self.attr1 , self.objAttr[self.attr1])]
            ldapModify(self.objDn, modList)
            raise

        try:
            self.addValues()
            self.deleteSingleAttribute()
            self.addMultipleNewValues()
            self.replaceWithMultipleValues()
            self.deleteMultipleAttributes()
            # Try again with empty attributes
            self.deleteMultipleAttributes()
            self.deleteEmptySingleAttributeValue()
            self.addValuesToMultipleAttributes()
            self.deleteSingleAttributeValue()
            self.replaceSingleValuesOnMultipleAttributes()
            self.deleteMultipleAttributeValues()
            self.replaceMultipleValuesWithMultipleAttributes()
            self.restoreToOriginalValues()
        except Exception:
            log('Attempting to restore test person account.')
            executeItimUtil("personAttrRep~%s~{'%s':%s}\n" % (self.filter, self.attr1, self.objAttr[self.attr1]))
            executeItimUtil("personAttrRep~%s~{'%s':%s}\n" % (self.filter, self.attr2, self.objAttr[self.attr2]))
            raise

    
    def addValues(self):
        expectedVals1= [self.val4]
        expectedVals2= list(self.objAttr[self.attr2])

        # Add single value
        expectedVals1.append(self.val1)
        executeItimUtil("personAttrAdd~%s~{'%s':'%s'}\n" % (self.filter, self.attr1, self.val1))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual(expectedVals1, attr[self.attr1], self.filter +' '+ self.attr1)

        waitForItimSync()
        # Add to multiple attributes at one time
        expectedVals1.append(self.val2)
        expectedVals1.append(self.val3)
        expectedVals2.append(self.val1)
        executeItimUtil("personAttrAdd~%s~{'%s':['%s','%s'], '%s':'%s'}\n" % 
                        (self.filter, self.attr1, self.val2, self.val3, self.attr2,self.val1))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual(expectedVals1, attr[self.attr1], self.filter +' '+ self.attr1)
        assertListEqual(expectedVals2, attr[self.attr2], self.filter +' '+ self.attr2)
        waitForItimSync()


    def deleteSingleAttribute(self):
        # Delete all values for a single attribute
        executeItimUtil("personAttrDel~%s~['%s']\n" % (self.filter, self.attr1))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assert (not self.attr1 in attr.keys()), 'unexpected values for '+ self.attr1 +':'+ str(attr[self.attr1])
        waitForItimSync()

    def addMultipleNewValues(self):
        # Add multiple values to attribute with no value
        executeItimUtil("personAttrAdd~%s~{'%s':['%s','%s']}\n" % 
                        (self.filter, self.attr1, self.val3, self.val1))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val3, self.val1], attr[self.attr1], self.filter +' '+ self.attr1)
        waitForItimSync()

    def replaceWithMultipleValues(self):
        executeItimUtil("personAttrRep~%s~{'%s':['%s','%s']}\n" % 
                        (self.filter, self.attr1, self.val2, self.val4))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val2, self.val4], attr[self.attr1], self.filter +' '+ self.attr1)
        waitForItimSync()

    def deleteMultipleAttributes(self):
        executeItimUtil("personAttrDel~%s~['%s','%s']\n" % (self.filter, self.attr1, self.attr2))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assert (not self.attr1 in attr.keys()), 'unexpected values for '+ self.attr1 +':'+ str(attr[self.attr1])
        assert (not self.attr2 in attr.keys()), 'unexpected values for '+ self.attr2 +':'+ str(attr[self.attr2])
        waitForItimSync()

    def deleteEmptySingleAttributeValue(self):
        executeItimUtil("personAttrDel~%s~{'%s':'%s'}\n" % (self.filter, self.attr1, self.val2))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assert (not self.attr1 in attr.keys()), 'unexpected values for '+ self.attr1 +':'+ str(attr[self.attr1])
        assert (not self.attr2 in attr.keys()), 'unexpected values for '+ self.attr2 +':'+ str(attr[self.attr2])
        waitForItimSync()

    def addValuesToMultipleAttributes(self):
        executeItimUtil("personAttrAdd~%s~{'%s':['%s','%s'], '%s':'%s'}\n" % 
                        (self.filter, self.attr1, self.val2, self.val3, self.attr2,self.val1))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val2, self.val3], attr[self.attr1], self.filter +' '+ self.attr1)
        assertListEqual([self.val1], attr[self.attr2], self.filter +' '+ self.attr2)
        waitForItimSync()

    def deleteSingleAttributeValue(self):
        executeItimUtil("personAttrDel~%s~{'%s':'%s'}\n" % (self.filter, self.attr1, self.val2))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val3], attr[self.attr1], self.filter +' '+ self.attr1)
        assertListEqual([self.val1], attr[self.attr2], self.filter +' '+ self.attr2)
        waitForItimSync()

    def replaceSingleValuesOnMultipleAttributes(self):
        executeItimUtil("personAttrRep~%s~{'%s':'%s', '%s':'%s'}\n" % 
                        (self.filter, self.attr1, self.val1, self.attr2, self.val2))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val1], attr[self.attr1], self.filter +' '+ self.attr1)
        assertListEqual([self.val2], attr[self.attr2], self.filter +' '+ self.attr2)
        waitForItimSync()
        
    def deleteMultipleAttributeValues(self):
        executeItimUtil("personAttrAdd~%s~{'%s':['%s','%s'], '%s':('%s','%s')}\n" % 
                        (self.filter, self.attr1, self.val2, self.val3, self.attr2, self.val1, self.val3))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val1, self.val2, self.val3], attr[self.attr1], self.filter +' '+ self.attr1)
        assertListEqual([self.val2, self.val1, self.val3], attr[self.attr2], self.filter +' '+ self.attr2)
        waitForItimSync()

        executeItimUtil("personAttrDel~%s~{'%s':['%s','%s'], '%s':['%s','unusedValue']}\n" % 
                        (self.filter, self.attr1, self.val2, self.val3, self.attr2, self.val1))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val1], attr[self.attr1], self.filter +' '+ self.attr1)
        assertListEqual([self.val2, self.val3], attr[self.attr2], self.filter +' '+ self.attr2)
        waitForItimSync()

    def replaceMultipleValuesWithMultipleAttributes(self):
        executeItimUtil("personAttrRep~%s~{'%s':['%s','%s'], '%s':'%s'}\n" % 
                        (self.filter, self.attr1, self.val2, self.val3, self.attr2, self.val1))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val2, self.val3], attr[self.attr1], self.filter +' '+ self.attr1)
        assertListEqual([self.val1], attr[self.attr2], self.filter +' '+ self.attr2)
        waitForItimSync()

    def restoreToOriginalValues(self):
        executeItimUtil("personAttrRep~%s~{'%s':%s, '%s':%s}\n" % 
                        (self.filter, self.attr1, self.objAttr[self.attr1],
                         self.attr2, self.objAttr[self.attr2]))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual(self.objAttr[self.attr1], attr[self.attr1], self.filter +' '+ self.attr1)
        assertListEqual(self.objAttr[self.attr2], attr[self.attr2], self.filter +' '+ self.attr2)


class PersonAttrTestCase(unittest.TestCase):
    # DN and attribute values of the person object
    objDn= None
    objAttr= None

    # test attribute names
    attr1='title'
    attr2='altmail'

    # LDAP filter for the person object
    filter= None
    # test values. Hopefully unique
    val1='QzzpJJrf9Zz--='
    val2='9p8h34wr,mb 67zf4'
    val3='Hkser7yh3dWEjks'
    val4='k7sdfII67gw34r  +'

    # Save object attributes the first time through so we can restore the object at the end
    def setUp(self):
        if not self.objDn:
            self.filter= '(&(uid=%s)(objectclass=erpersonitem))' % TEST_UID
            self.objDn, self.objAttr= ldapGetObject(ITIM_BASE, self.filter)
            assert self.objDn, 'Person not found'
            assert self.objAttr, 'No Person attributes'
            assert (self.attr1 in self.objAttr), 'Test user has no value for attribute:'+ self.attr1
            assert (self.attr2 in self.objAttr), 'Test user has no value for attribute:'+ self.attr2


    # Test replacement of attribute values using single command.
    def testAttributes(self):
        try:
            executeItimUtil("personAttr~%s~{'Rep':{'%s':'%s'}}\n" % (self.filter, self.attr1, self.val4))
            dn, attr= ldapGetObject(ITIM_BASE, self.filter)
            assertListEqual([self.val4], attr[self.attr1], self.filter +' '+ self.attr1)
            waitForItimSync()
        except Exception:
            modList= [(ldap.MOD_REPLACE, self.attr1 , self.objAttr[self.attr1])]
            ldapModify(self.objDn, modList)
            raise

        try:
            self.addValues()
            self.deleteSingleAttribute()
            self.addMultipleNewValues()
            self.replaceWithMultipleValues()
            self.deleteMultipleAttributes()
            # Try again with empty attributes
            self.deleteMultipleAttributes()
            self.deleteEmptySingleAttributeValue()
            self.addValuesToMultipleAttributes()
            self.deleteSingleAttributeValue()
            self.replaceSingleValuesOnMultipleAttributes()
            self.deleteMultipleAttributeValues()
            self.replaceMultipleValuesWithMultipleAttributes()
            self.addAndDeleteAttributes()
            self.replaceAndDeleteAttributes()
            self.addValueWithQuote()
            self.restoreToOriginalValues()
        except Exception:
            log('Attempting to restore test person account.')
            executeItimUtil("personAttrRep~%s~{'%s':%s}\n" % (self.filter, self.attr1, self.objAttr[self.attr1]))
            executeItimUtil("personAttrRep~%s~{'%s':%s}\n" % (self.filter, self.attr2, self.objAttr[self.attr2]))
            raise

    
    def addValues(self):
        expectedVals1= [self.val4]
        expectedVals2= list(self.objAttr[self.attr2])

        # Add single value
        expectedVals1.append(self.val1)
        executeItimUtil("personAttr~%s~{'Add':{'%s':'%s'}}\n" % (self.filter, self.attr1, self.val1))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual(expectedVals1, attr[self.attr1], self.filter +' '+ self.attr1)

        waitForItimSync()
        # Add to multiple attributes at one time
        expectedVals1.append(self.val2)
        expectedVals1.append(self.val3)
        expectedVals2.append(self.val1)
        executeItimUtil("personAttr~%s~{'Add':{\"%s\":['%s',\"%s\"], '%s':'%s'}}\n" % 
                        (self.filter, self.attr1, self.val2, self.val3, self.attr2,self.val1))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual(expectedVals1, attr[self.attr1], self.filter +' '+ self.attr1)
        assertListEqual(expectedVals2, attr[self.attr2], self.filter +' '+ self.attr2)
        waitForItimSync()


    def deleteSingleAttribute(self):
        # Delete all values for a single attribute
        executeItimUtil("personAttr~%s~{'Del':['%s']}\n" % (self.filter, self.attr1))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assert (not self.attr1 in attr.keys()), 'unexpected values for '+ self.attr1 +':'+ str(attr[self.attr1])
        waitForItimSync()

    def addMultipleNewValues(self):
        # Add multiple values to attribute with no value
        executeItimUtil("personAttr~%s~{'Add':{'%s':['%s','%s']}}\n" % 
                        (self.filter, self.attr1, self.val3, self.val1))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val3, self.val1], attr[self.attr1], self.filter +' '+ self.attr1)
        waitForItimSync()

    def replaceWithMultipleValues(self):
        executeItimUtil("personAttr~%s~{'Rep':{'%s':['%s','%s']}}\n" % 
                        (self.filter, self.attr1, self.val2, self.val4))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val2, self.val4], attr[self.attr1], self.filter +' '+ self.attr1)
        waitForItimSync()

    def deleteMultipleAttributes(self):
        executeItimUtil("personAttr~%s~{'Del':['%s','%s']}\n" % (self.filter, self.attr1, self.attr2))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assert (not self.attr1 in attr.keys()), 'unexpected values for '+ self.attr1 +':'+ str(attr[self.attr1])
        assert (not self.attr2 in attr.keys()), 'unexpected values for '+ self.attr2 +':'+ str(attr[self.attr2])
        waitForItimSync()

    def deleteEmptySingleAttributeValue(self):
        executeItimUtil("personAttr~%s~{'Del':{'%s':'%s'}}\n" % (self.filter, self.attr1, self.val2))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assert (not self.attr1 in attr.keys()), 'unexpected values for '+ self.attr1 +':'+ str(attr[self.attr1])
        assert (not self.attr2 in attr.keys()), 'unexpected values for '+ self.attr2 +':'+ str(attr[self.attr2])
        waitForItimSync()

    def addValuesToMultipleAttributes(self):
        executeItimUtil("personAttr~%s~{'add':{'%s':['%s','%s'], '%s':'%s'}}\n" % 
                        (self.filter, self.attr1, self.val2, self.val3, self.attr2,self.val1))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val2, self.val3], attr[self.attr1], self.filter +' '+ self.attr1)
        assertListEqual([self.val1], attr[self.attr2], self.filter +' '+ self.attr2)
        waitForItimSync()

    def deleteSingleAttributeValue(self):
        executeItimUtil("personAttr~%s~{'del':{'%s':'%s'}}\n" % (self.filter, self.attr1, self.val2))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val3], attr[self.attr1], self.filter +' '+ self.attr1)
        assertListEqual([self.val1], attr[self.attr2], self.filter +' '+ self.attr2)
        waitForItimSync()

    def replaceSingleValuesOnMultipleAttributes(self):
        executeItimUtil("personAttr~%s~{'rep':{'%s':'%s', '%s':'%s'}}\n" % 
                        (self.filter, self.attr1, self.val1, self.attr2, self.val2))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val1], attr[self.attr1], self.filter +' '+ self.attr1)
        assertListEqual([self.val2], attr[self.attr2], self.filter +' '+ self.attr2)
        waitForItimSync()
        
    def deleteMultipleAttributeValues(self):
        executeItimUtil("personAttr~%s~{'add':{'%s':['%s','%s'], '%s':('%s','%s')}}\n" % 
                        (self.filter, self.attr1, self.val2, self.val3, self.attr2, self.val1, self.val3))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val1, self.val2, self.val3], attr[self.attr1], self.filter +' '+ self.attr1)
        assertListEqual([self.val2, self.val1, self.val3], attr[self.attr2], self.filter +' '+ self.attr2)
        waitForItimSync()

        executeItimUtil("personAttr~%s~{'del':{'%s':['%s','%s'], '%s':['%s','unusedValue']}}\n" % 
                        (self.filter, self.attr1, self.val2, self.val3, self.attr2, self.val1))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val1], attr[self.attr1], self.filter +' '+ self.attr1)
        assertListEqual([self.val2, self.val3], attr[self.attr2], self.filter +' '+ self.attr2)
        waitForItimSync()

    def replaceMultipleValuesWithMultipleAttributes(self):
        executeItimUtil("personAttr~%s~{'rep':{'%s':['%s','%s'], '%s':'%s'}}\n" % 
                        (self.filter, self.attr1, self.val2, self.val3, self.attr2, self.val1))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val2, self.val3], attr[self.attr1], self.filter +' '+ self.attr1)
        assertListEqual([self.val1], attr[self.attr2], self.filter +' '+ self.attr2)
        waitForItimSync()

    def addAndDeleteAttributes(self):
        executeItimUtil("personAttr~%s~{'del':{'%s':'%s'}, 'add':{'%s':'%s'}}\n" % 
                        (self.filter, self.attr1, self.val2, self.attr2, self.val2))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val3], attr[self.attr1], self.filter +' '+ self.attr1)
        assertListEqual([self.val1, self.val2], attr[self.attr2], self.filter +' '+ self.attr2)
        waitForItimSync()

    def replaceAndDeleteAttributes(self):
        executeItimUtil("personAttr~%s~{'rep':{'%s':'%s'}, 'Del':['%s']}\n" % 
                        (self.filter, self.attr1, self.val1, self.attr2))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val1], attr[self.attr1], self.filter +' '+ self.attr1)
        assert (not self.attr2 in attr.keys()), 'unexpected values for '+ self.attr2 +':'+ str(attr[self.attr2])
        waitForItimSync()

    def addValueWithQuote(self):
        # Add multiple values to attribute with no value
        executeItimUtil("personAttr~%s~{'Add':{'%s':\"Jon's Pet\"}}\n" % (self.filter, self.attr1))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual([self.val1,"Jon's Pet"], attr[self.attr1], self.filter +' '+ self.attr1)
        waitForItimSync()

    def restoreToOriginalValues(self):
        executeItimUtil("personAttr~%s~{'rep':{'%s':%s, '%s':%s}}\n" % 
                        (self.filter, self.attr1, self.objAttr[self.attr1],
                         self.attr2, self.objAttr[self.attr2]))
        dn, attr= ldapGetObject(ITIM_BASE, self.filter)
        assertListEqual(self.objAttr[self.attr1], attr[self.attr1], self.filter +' '+ self.attr1)
        assertListEqual(self.objAttr[self.attr2], attr[self.attr2], self.filter +' '+ self.attr2)



class PersonOperationsTestCase(unittest.TestCase):

    # Verify that all user accounts have the expected status
    # Returns a string with list of services that do not have the expected status or '' otherwise
    def verifyAccountStatus(self, personDn, expectedStatus):
        retVal= ''
        filtr= '(&(objectclass=eraccountitem)(owner=%s))' % personDn
        results= ldapGetObjects(ITIM_BASE, filtr)
        for acctDn, acctAttr in results:
            if acctAttr['eraccountstatus'][0] != expectedStatus:
                svcDn, svcAttr= ldapGetObject(acctAttr['erservice'][0],'(objectclass=erserviceitem)')
                retVal += svcAttr['erservicename'][0]
        return retVal

    # Verify that the user and their accounts have the expected status
    def verifyStatus(self, uid, expectedStatus):
        msg= {ITIM_ACTIVE:'not active',
              ITIM_INACTIVE:'active'}
        personDn, attr= ldapGetObject(ITIM_BASE, '(&(uid=%s)(objectclass=erpersonitem))' % uid)
        assert (attr['erpersonstatus'][0] == expectedStatus), 'Person uid=%s is %s' % (uid, msg[expectedStatus])

        badAccts= ''
        results= ldapGetObjects(ITIM_BASE, '(&(objectclass=eraccountitem)(owner=%s))' % personDn)
        for acctDn, acctAttr in results:
            if acctAttr['eraccountstatus'][0] != expectedStatus:
                svcDn, svcAttr= ldapGetObject(acctAttr['erservice'][0],'(objectclass=erserviceitem)')
                badAccts += svcAttr['erservicename'][0] + ','
        assert len(badAccts) == 0, 'Uid=%s account(s) %s are %s' % (uid, badAccts[:-1], msg[expectedStatus])


    def testSingleSuspendRestore(self):
        filtr= '(&(uid=%s)(objectclass=erpersonitem))' % TEST_UID

        self.verifyStatus(TEST_UID, ITIM_ACTIVE)

        executeItimUtil("personSuspend~%s\n" % filtr)
        self.verifyStatus(TEST_UID, ITIM_INACTIVE)
        waitForItimSync()
        
        executeItimUtil("personRestore~%s\n" % filtr)
        self.verifyStatus(TEST_UID, ITIM_ACTIVE)
        waitForItimSync()

    # Suspend and restore 2 accounts at a time
    def testMultipleSuspendRestore(self):
        filtr1= '(&(uid=%s)(objectclass=erpersonitem))' % TEST_UID
        filtr2= '(&(uid=%s)(objectclass=erpersonitem))' % TEST_UID2
        filtr3= '(&(|(uid=%s)(uid=%s))(objectclass=erpersonitem))' % (TEST_UID,TEST_UID2)

        self.verifyStatus(TEST_UID, ITIM_ACTIVE)
        self.verifyStatus(TEST_UID2, ITIM_ACTIVE)

        executeItimUtil("personSuspend~%s\npersonSuspend~%s\n" % (filtr1, filtr2))
        self.verifyStatus(TEST_UID, ITIM_INACTIVE)
        self.verifyStatus(TEST_UID2, ITIM_INACTIVE)
        waitForItimSync()
        
        executeItimUtil("personRestore~%s\npersonRestore~%s\n" % (filtr1, filtr2))
        self.verifyStatus(TEST_UID, ITIM_ACTIVE)
        self.verifyStatus(TEST_UID2, ITIM_ACTIVE)
        waitForItimSync()

        executeItimUtil("personSuspend~%s\n" % filtr3)
        self.verifyStatus(TEST_UID, ITIM_INACTIVE)
        self.verifyStatus(TEST_UID2, ITIM_INACTIVE)
        waitForItimSync()
        
        executeItimUtil("personRestore~%s\n" % filtr3)
        self.verifyStatus(TEST_UID, ITIM_ACTIVE)
        self.verifyStatus(TEST_UID2, ITIM_ACTIVE)
        waitForItimSync()



# TODO filter does not select any objects

# TODO personAttrAdd with value that already exists. Do not add twice.

# TODO verify personCreate


if __name__ == '__main__':
    testSetup()

    service= ServiceAttrTestCase
    personAttrOp= PersonAttrOpTestCase
    personAttr= PersonAttrTestCase
    personOps= PersonOperationsTestCase
    unittest.main()

#    suite= unittest.TestSuite()
#    suite.addTest(unittest.makeSuite(PersonAttrTestCase))
#    runner= unittest.TextTestRunner()
#    runner.run(suite)

