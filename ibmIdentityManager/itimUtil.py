# This utility should only be invoked via the itimUtil.sh wrapper script.

# Support utility to submit ITIM object changes via the ITIM API. Changes are specified 
# through a text file.
# Changes are submitted asynchronously and status is reported later in the output.
# See usage information in the wrapper script.

# 2013-10-23 Paul T Sparks
#  Added personCreate command. Added argStyle configuration to allow multiple "eval" options
#  for commands with the same number of args.
# 2013-07-12 Paul T Sparks

# TODO Enhancements
# During *AttrAdd prevent adding duplicate values (?)

# ITIM API imports
from com.ibm.itim.apps import InitialPlatformContext, PlatformContext, Request
from com.ibm.itim.apps.identity import OrganizationalContainerMO, PersonManager, PersonMO 
from com.ibm.itim.apps.jaas.callback import PlatformCallbackHandler
from com.ibm.itim.apps.policy import Entitlement, ProvisioningPolicy, ProvisioningPolicyManager, ProvisioningPolicyMO
from com.ibm.itim.apps.provisioning import AccountManager, AccountMO, ServiceMO
from com.ibm.itim.apps.search import SearchMO 
from com.ibm.itim.apps.system import SystemUserMO 
from com.ibm.itim.common import AttributeValue, EntitlementAttributeValue
from com.ibm.itim.dataservices.model import CompoundDN, DistinguishedName, ObjectProfileCategory, SearchParameters
from com.ibm.itim.dataservices.model.domain import Person,Service,OrganizationalContainerSearch,OrganizationSearch
from com.ibm.itim.dataservices.model.system import SystemUser

from com.ibm.websphere.security.auth.callback import WSCallbackHandlerImpl

from java.lang import Exception, System, Thread
from java.util import ArrayList, Collections, HashMap, Hashtable, Locale
from javax.security.auth.login import LoginContext

import os
import sys
import time

# Default WebSphere username for platform authentication
PLATFORM_ID='wasadmin'

# Interval for request status polling.
DEFAULT_POLLING_INTERVAL= 3 * 1000 # milliseconds

# Time to wait for all requests to complete before exiting.
FINAL_WAIT_TIME= 30 # seconds

# Turn debug info ON/OFF here
debugFlag= 0

# Conditionally output debug messages
def debug(*args):
    if debugFlag:
        print >> sys.stderr, ' '.join(map(str,args))

outfile= sys.stderr
# Output log messages
def log(*args):
    print >> outfile, ' '.join(map(str,args))


# Abstract the ITIM API interface
class Itimapi:
    # organization types
    ORG='org'
    ORGUNIT='orgunit'
    BPUNIT='bpunit'
    LOC='loc'

    # List of pending ITIM request objects
    requests= []

    pollingInterval= DEFAULT_POLLING_INTERVAL
    """ Polling interval in seconds for checking request status"""

    # Set up and connect to ITIM
    def __init__(self, platformID, platformPW, itimID, itimPW):
        self.setupIbmCorbaProperties(platformID, platformPW)

        # Get some configuration parameters that were loaded from enRole.properties
        contextFactory= java.lang.System.getProperty("enrole.platform.contextFactory")
        platformURL= java.lang.System.getProperty("enrole.appServer.url")
        platformRealm= java.lang.System.getProperty("enrole.appServer.realm")
        debug('platformURL=', platformURL)
        self.tenant= java.lang.System.getProperty("enrole.defaulttenant.id")
        self.tenantDN = "ou=%s,dc=itim" %  self.tenant

        env= Hashtable()
        env.put(InitialPlatformContext.CONTEXT_FACTORY, contextFactory)
        env.put(PlatformContext.PLATFORM_URL, platformURL)
        env.put(PlatformContext.PLATFORM_PRINCIPAL, platformID)
        env.put(PlatformContext.PLATFORM_CREDENTIALS, platformPW)
        env.put(PlatformContext.PLATFORM_REALM, platformRealm)
        debug(env.toString())
        debug(java.lang.System.getProperty("com.ibm.CORBA.loginSource"))
        debug(java.lang.System.getProperty("com.ibm.CORBA.loginUserid"))
        debug(java.lang.System.getProperty("com.ibm.CORBA.loginPassword"))
        self.platform= InitialPlatformContext(env)

        callbackHandler= WSCallbackHandlerImpl(itimID, platformRealm, itimPW)
        loginContext= LoginContext("WSLogin", callbackHandler)
        loginContext.login()
        self.subject= loginContext.getSubject()

    # Some additional properties to allow access to ITIM platform
    def setupIbmCorbaProperties(self, platformID, platformPW):
        java.lang.System.setProperty("com.ibm.CORBA.loginSource", "properties")
        java.lang.System.setProperty("com.ibm.CORBA.loginUserid", platformID)
        java.lang.System.setProperty("com.ibm.CORBA.loginPassword", platformPW)

    def getPlatformContext(self):
        return self.platform

    def getSubject(self):
        return self.subject

    # Get ITIM AccountManager object
    def getAccountManager(self):
        return AccountManager(self.platform, self.subject)

    # Get ITIM PersonManager object
    def getPersonManager(self):
        return PersonManager(self.platform, self.subject)

    def accountsForPerson(self, personMO):
        """Get list of Account objects for a person."""
        acctMgr= AccountManager(self.platform, self.subject)
        return acctMgr.getAccounts(personMO, Locale.US)

    def findObjects(self, ldapFilter, objectType, constructor):
        """Returns a list of managed objects"""
        searchMO= SearchMO(self.platform, self.subject)
        searchMO.setContext(CompoundDN(DistinguishedName(self.tenant)))
        searchMO.setCategory(objectType)
        searchMO.setFilter(ldapFilter)
        searchMO.setPaging(0)

        searchResults= searchMO.execute()
        objectList= searchResults.getResults()
        searchResults.close()

        moList= []
        for mObject in objectList:
            moList.append(constructor(self.platform, self.subject, mObject.getDistinguishedName()))
        return moList

    def findPersons(self, ldapFilter):
        """Find persons based on LDAP filter. Returns list of PersonMO objects"""
        return self.findObjects(ldapFilter, ObjectProfileCategory.PERSON, PersonMO)

    def findServices(self, ldapFilter):
        """Find services based on LDAP filter. Returns list of ServiceMO objects"""
        return self.findObjects(ldapFilter, ObjectProfileCategory.SERVICE, ServiceMO)

    def findAccounts(self, ldapFilter):
        """Find services based on LDAP filter. Returns list of ServiceMO objects"""
        return self.findObjects(ldapFilter, ObjectProfileCategory.ACCOUNT, AccountMO)

    def findSystemUsers(self, ldapFilter):
        """Returns list of ITIM accounts (systemuser objects) based on LDAP filter."""
        return self.findObjects(ldapFilter, ObjectProfileCategory.SYSTEM_USER, SystemUserMO)

    def findProvisioningPolices(self, ldapFilter):
        """Returns list of ProvisioningPolicyMO objects based on LDAP filter."""
        return self.findObjects(ldapFilter, ObjectProfileCategory.PROVISIONING_POLICY, ProvisioningPolicyMO)

    def findOrgsByName(self, ldapFilter):
        """Returns list of OrganizationalContainerMO objects based on LDAP filter."""
        return self.findObjects(ldapFilter, ObjectProfileCategory.CONTAINER, OrganizationalContainerMO)

    # TODO Finish this
    def findOrgsByName(self, name):
        ldapFilter='(|(ou=%s)(o=%s)(l=%s))' % (name, name, name)
#        ldapFilter='(ou=%s)' % name
        print 'ldapfilter=', ldapFilter
        return self.findObjects(ldapFilter, ObjectProfileCategory.CONTAINER, OrganizationalContainerMO)


    def close(self):
        """Close the ITIM API connection."""
        self.platform.close()

    # Map status values to user text.
    COMPLETE_STATUS= {Request.SUCCEEDED:'succ', Request.FAILED:'fail', Request.WARNING:'warn'}

    def __checkRequests(self):
        toRemove= []
        for i in self.requests:
            request, description = i
            status= request.status
            if status in self.COMPLETE_STATUS.keys():
                log('Result:',self.COMPLETE_STATUS[status],description)
                toRemove.append(i)
        for i in toRemove:
            self.requests.remove(i)
        return (0 == len(self.requests))

    def requestsComplete(self, waitSeconds=0):
        """ Check remaining outstanding ITIM requests to see if they are complete. Returns True if all requests
        are complete. Will wait up to waitSeconds (+ pollingInterval) for all requests to complete. 
        """
        status= self.__checkRequests()
        if waitSeconds == 0:
            return status
        endTime = System.currentTimeMillis() + 1000 * waitSeconds
        while not status and (System.currentTimeMillis() < endTime):
            Thread.sleep(self.pollingInterval)
            status= self.__checkRequests()
        return status

    def submitRequest(self, description, operation, *args):
        """ Add a submitted request to be monitored until completion."""
        try:
            request = operation(*args)
            if request == None:
                raise Exception('ITIM request returned null')
            self.requests.append((request, time.strftime('%H:%M:%S') +' '+ description))
        except java.lang.Exception, e:
            log('Error submitting request:',description,'exception=', e)
        except Exception, e:
            log('Error submitting request:',description,'errno=', e.errno, 'strerror=', e.strerror)

    def submitOperation(self, description, operation, *args):
        """ Submit a synchronous ITIM operation."""
        try:
            operation(*args)
        except java.lang.Exception, e:
            log('Error submitting operation:',description,'exception=', e)
        except Exception, e:
            log('Error submitting operation:',description,'errno=', e.errno, 'strerror=', e.strerror)



# We get options from the environment rather than directly from the command line since the wsadmin jython is
# so old and limited that it can't do non-echoed input of passwords. Program option and argument validation is done
# using a wrapper script.
def getOptions():
    options= {}
    envKeys= os.environ.keys()

    options['userid']= os.environ['USER_ID']
    options['userpw']= os.environ['USER_PW']
    options['platformpw']= os.environ['PLATFORM_PW']
    if 'COMMAND_FILE' in envKeys:
        options['cmdfile']= os.environ['COMMAND_FILE']
    if 'OUTPUT_FILE' in envKeys:
        options['outfile']= os.environ['OUTPUT_FILE']
    options['dryrun']= ('DRY_RUN' in envKeys) and (os.environ['DRY_RUN'] == 'Y')
        
    return options



# ITIM API handle
api= None
# output file handle
outfile= sys.stdout

# Wrap the itimapi function to allow skipping for dry runs.
def submitRequest(itimapi, description, operation, *args):
    debug('submitting request')
    if options['dryrun']:
        log('Not submitting request:', description)
    else:
        itimapi.submitRequest(description, operation, *args)

# Wrap the itimapi function to allow skipping for dry runs.
def submitOperation(itimapi, description, operation, *args):
    debug('submitting request')
    if options['dryrun']:
        log('Not submitting request:', description)
    else:
        itimapi.submitOperation(description, operation, *args)


# Replace attribute values for a DirectoryObject
def dirObjectAttrRep(obj, attrDict):
    debug('dirObectAttrRep: Enter')
    for attrname in attrDict.keys():
        attrtype= type(attrDict[attrname])
        if attrtype == type([]) or attrtype == type(()):
            vals= ArrayList()
            for v in attrDict[attrname]:
                vals.add(v)
            obj.setAttribute(AttributeValue(attrname, vals))
        else:
            obj.setAttribute(AttributeValue(attrname, str(attrDict[attrname])))


# Add attribute values to a DirectoryObject without overwriting existing attribute values.
def dirObjectAttrAdd(obj, attrDict):
    debug('dirObectAttrAdd: Enter')
    for attrname in attrDict.keys():
        vals= ArrayList()
        attrtype= type(attrDict[attrname])
        if attrtype == type([]) or attrtype == type(()):
            for v in attrDict[attrname]:
                vals.add(v)
        else:
            vals.add(str(attrDict[attrname]))

        av= obj.getAttribute(attrname)
        if not av:
            av= AttributeValue()
            av.setName(attrname)
        debug('AttrAdd- '+ attrname +' Before: '+ str(av.getValues()))
        av.addValues(vals)
        obj.setAttribute(av)
        debug('AttrAdd- '+ attrname +' After: '+ str(av.getValues()))


# Delete attribute values from a DirectoryObject
def dirObjectAttrDel(obj, attrs):
    debug('dirObjectAttrDel: Enter')
    if type({}) != type(attrs): # remove all values
        for attrname in attrs:
            obj.removeAttribute(attrname)
    else: # removed selected values
        for attrname in attrs.keys():
            attrtype= type(attrs[attrname])
            if attrtype == type([]) or attrtype == type(()):
                toBeRemoved= attrs[attrname]
            else:
                toBeRemoved= [str(attrs[attrname])]

            newVals= ArrayList()
            av= obj.getAttribute(attrname)
            if not av: # no values in object
                return
            existingValues=av.getValues()
            for attrVal in existingValues:
                if not attrVal in toBeRemoved:
                    newVals.add(attrVal)
            obj.setAttribute(AttributeValue(attrname, newVals))
            


# Attribute operation name to function mapping
attrOp= {
    'Add': dirObjectAttrAdd,
    'Del': dirObjectAttrDel,
    'Rep': dirObjectAttrRep,
    'add': dirObjectAttrAdd,
    'del': dirObjectAttrDel,
    'rep': dirObjectAttrRep,
}


# Extract specified attribute values for selected identities in the same format used for input.
def cmdPersonExtract(ldapfilter, attrlist):
    log('cmdPersonExtract("'+ ldapfilter +'",'+ str(attrlist) +')')
    for personMO in api.findPersons(ldapfilter):
        person= personMO.getData()
        uid= person.getAttribute('uid').getString()
        outfile.write('personAttrRep~(uid='+ uid +')~{')
        for attrname in attrlist:
            attrval= person.getAttribute(attrname)
            if not attrval:
                continue
            outfile.write("'"+ attrname +"':(")
            for val in attrval.getValues():
                outfile.write("'"+ val +"',")
            outfile.write('),')
        outfile.write('}\n')

# Perform requested operation on the specified attributes for the specified accounts
def cmdAccountAttr(ldapfilter, attrs):
    log('cmd: accountAttr("%s",%s)' % (ldapfilter, str(attrs)))
    for accountMO in api.findAccounts(ldapfilter):
        account= accountMO.getData()
        for op in attrs.keys():
            attrOp[op](account, attrs[op])
        name = account.getAttribute('erglobalid').getString()
        submitRequest(api,'accountAttr globalid='+ name +' '+ str(attrs), 
                      accountMO.update, account, None)

# Perform a restore operation on the specified accounts
def cmdAccountRestore(ldapfilter):
    log('cmd: accountRestore("%s")' % (ldapfilter))
    for accountMO in api.findAccounts(ldapfilter):
        account= accountMO.getData()
        name = account.getAttribute('erglobalid').getString()
        password = "WFbR_OdzY=p98X=ZCM7r" # This should be ignored due to PW sync
        submitRequest(api,'accountRestore globalid='+ name, 
                      accountMO.restore, password, None)

# Perform requested operation on the specified attributes for the specified persons
def cmdPersonAttr(ldapfilter, attrs):
    log('cmd: personAttr("%s",%s)' % (ldapfilter, str(attrs)))
    for personMO in api.findPersons(ldapfilter):
        person= personMO.getData()
        for op in attrs.keys():
            attrOp[op](person, attrs[op])
        name= person.getAttribute('uid').getString()
        name += '-'+ person.getAttribute('erglobalid').getString()
        submitRequest(api,'personAttr name-globalid='+ name +' '+ str(attrs), 
                      personMO.update, person, None)

# Perform requested operation on the specified attributes for the specified services
def cmdServiceAttr(ldapfilter, attrs):
    log('cmd: serviceAttr("%s",%s)' % (ldapfilter, str(attrs)))
    svcs= api.findServices(ldapfilter)
    if len(svcs) == 0:
        log('No services found for filter ',ldapfilter)
    for serviceMO in svcs:
        service= serviceMO.getData()
        for op in attrs.keys():
            attrOp[op](service, attrs[op])
        name= service.getAttribute('erservicename').getString()
        name += '-'+service.getAttribute('erglobalid').getString()
        submitOperation(api,'serviceAttr name-globalid='+ name +' '+ str(attrs), 
                      serviceMO.update, service)

# Perform requested operation on the specified attributes for the specified system user
# TODO There is no update method for SystemUserMO. Figure out how to best handle updates
# to SystemUser objects.
def cmdSystemUserAttr(ldapfilter, attrs):
    log('cmd: systemuserAttr("%s",%s)' % (ldapfilter, str(attrs)))
    for systemuserMO in api.findSystemUsers(ldapfilter):
        systemuser= systemuserMO.getData()
        for op in attrs.keys():
            attrOp[op](systemuser, attrs[op])
        name= systemuser.getAttribute('eruid').getString()
        name += '-'+ systemuser.getAttribute('erglobalid').getString()
        submitRequest(api,'systemuserAttr name-globalid='+ name +' '+ str(attrs), 
                      systemuserMO.update, systemuser, None)


# Perform requested operation on the specified attributes for the specified persons
# DEPRECATED Use cmdPersonAttr
def cmdPersonAttrOp(op, ldapfilter, attrs):
    log('cmd: personAttr%s("%s",%s)' % (op, ldapfilter, str(attrs)))
    for personMO in api.findPersons(ldapfilter):
        person= personMO.getData()
        attrOp[op](person, attrs)
        name = person.getAttribute('erglobalid').getString()
        submitRequest(api,'personAttr'+ op +' globalid='+ name +' '+ str(attrs), 
                      personMO.update, person, None)


# Restore selected identities and all of their accounts
def cmdPersonRestore(ldapfilter):
    log('cmd: personRestore("'+ ldapfilter +'")')
    acctMgr= api.getAccountManager()
    for personMO in api.findPersons(ldapfilter):
        uid= personMO.getData().getAttribute('uid').getString()
        submitRequest(api, 'personRestore uid='+ uid, personMO.restore, None)

        acctMOs= api.accountsForPerson(personMO)
        accts= ArrayList()
        for i in acctMOs:
            accts.add(i.getData())
        submitRequest(api, 'personAccountsRestore uid='+ uid, acctMgr.restore, accts, None)


# Suspend selected identities.
def cmdPersonSuspend(ldapfilter):
    log('cmd: personSuspend("'+ ldapfilter +'")')
    for personMO in api.findPersons(ldapfilter):
        uid= personMO.getData().getAttribute('uid').getString()
        submitRequest(api,'personSuspend uid='+ uid, personMO.suspend, None)

# Create a new identity
def cmdPersonCreate(organizationName, profileName, attrDict):
    log('cmd: personCreate("'+ organizationName +'","'+ profileName +'",'+ str(attrDict) +')')
    person= Person(profileName)

    for attrname in attrDict.keys():
        vals= ArrayList()
        attrtype= type(attrDict[attrname])
        if attrtype == type([]) or attrtype == type(()): # multi-valued attribute
            for v in attrDict[attrname]:
                vals.add(v)
        else:
            vals.add(str(attrDict[attrname]))

        av= AttributeValue()
        av.setName(attrname)
        av.addValues(vals)
        person.setAttribute(av)

    containerMO= api.findOrgsByName(organizationName)
    pMgr= api.getPersonManager()
    submitRequest(api, 'personCreate:'+ str(attrDict), pMgr.createPerson, containerMO[0], person, None)


# Test command for developer use only.
def cmdTest(orgName):
    policies= api.findProvisioningPolices('(erpolicyitemname=TAM)')
    print policies
    print policies[0]
    print policies[0].getData()
    print policies[0].getData().getDescription()
    print policies[0].getData().getEntitlements()
    print policies[0].getData().getEntitlements()[0].getType()
    print policies[0].getData().getEntitlements()[0].getTarget()
    print policies[0].getData().getEntitlements()[0].getProvisioningParameters()

# Wait for requests to complete
def cmdWaitForRequests(timeout):
    log('cmd: waitForRequests('+ timeout +')')
    if options['dryrun']:
        return
    if api.requestsComplete(int(timeout)):
        log('Result: waitForRequests: Request processing completed.')
    else:
        log('Result: waitForRequests: Some requests have not completed.')


# Wait a specified amount of time
def cmdWait(timeout):
    log('cmd: wait('+ timeout +')')
    if options['dryrun']:
        return
    time.sleep(int(timeout))

# Map command names to number of args and function. The argStyle option is to allow different
# styles of arg evaluation prior to calling the command function.
CMD={
    #command Name: (argStyle, numArgs, functionName)
    'accountAttr': (2,2,cmdAccountAttr),
    'accountRestore': (1,1,cmdAccountRestore),
    'personAttr': (2,2,cmdPersonAttr),
    'serviceAttr': (2,2,cmdServiceAttr),
#    'systemuserAttr': (2,2,cmdSystemUserAttr),
    'personExtract': (2,2,cmdPersonExtract),
    'personRestore': (1,1,cmdPersonRestore),
    'personSuspend': (1,1,cmdPersonSuspend),
    'personCreate': (3,3,cmdPersonCreate),
    'test': (1,1,cmdTest),
    'wait': (1,1,cmdWait),
    'waitForRequests': (1,1,cmdWaitForRequests),
}

# Map attribute command names to operation and function name.
# These are the "old" style attribute commands. They are being included
# since the syntax was included in the design brief.
#ATTRCMD={
#    #command Name: (op, functionName)
#    'personAttrAdd': ('Add',cmdPersonAttrOp),
#    'personAttrDel': ('Del',cmdPersonAttrOp),
#    'personAttrRep': ('Rep',cmdPersonAttrOp),
#}


# Main command processing loop. Read commands from input file and process them.
# There is special handling for attribute commands.
def processCommands(cmdfile):
    linenum= 0
    for cmdline in cmdfile.readlines():
        linenum += 1
        cmdline= cmdline.strip()
        if len(cmdline) == 0: # skip empty lines
            continue
        if cmdline[0] == '#': # skip comment lines
            continue

        fields= cmdline.split('~')
        cmd= fields[0]
        # special processing for attribute commands
#        if cmd in ATTRCMD.keys():
#            op, cmdFn= ATTRCMD[cmd]
#            cmdFn(op, fields[1], eval(fields[2]))
#            continue

        if not cmd in CMD.keys():
            raise NameError('Unknown command: '+ cmd +' at line '+ str(linenum))
        argStyle, numArgs, cmdFn = CMD[cmd]
        if numArgs < len(fields) - 1:
            raise TypeError('Missing args for command: '+ cmd +' at line '+ linenum)
        if argStyle == 0:
            cmdFn()
        elif argStyle == 1:
            cmdFn(fields[1])
        elif argStyle == 2:
            cmdFn(fields[1],eval(fields[2]))
        elif argStyle == 3:
            cmdFn(fields[1], fields[2], eval(fields[3]))
        elif argStyle == 4:
            cmdFn(fields[1], eval(fields[2]), eval(fields[3]))
    debug('Command processing completed:')


####  Main Program #####
options= getOptions()

infile= sys.stdin
if 'cmdfile' in options.keys():
    infile= open(options['cmdfile'],'r')

outfile= sys.stderr
if 'outfile' in options.keys():
    debug('Writing to '+ options['outfile'])
    outfile= open(options['outfile'],'w')

api= Itimapi(PLATFORM_ID, options['platformpw'], options['userid'], options['userpw'])

try:
    processCommands(infile)

    if api.requestsComplete(FINAL_WAIT_TIME):
        log('Request processing completed.')
    else:
        log('Some requests have not completed. View the request status in the ITIM console')
except KeyboardInterrupt: # Exit nicely on Ctrl-C
    pass

api.close()
outfile.close()
