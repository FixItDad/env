## Authorization
User / group permissions granted in Web console interface at
**vCenter Servers > Manage > Permissions**

## vCenter system logs
 * vCenter Server 5.x and earlier versions on Windows XP, 2000, 2003: %ALLUSERSPROFILE%\Application Data\VMware\VMware VirtualCenter\Logs\
 * vCenter Server 5.x and earlier versions on Windows Vista, 7, 2008: C:\ProgramData\VMware\VMware VirtualCenter\Logs\
 * vCenter Server Appliance 5.x: /var/log/vmware/vpx/
 * vCenter Server Appliance 5.x UI: /var/log/vmware/vami
 * For vCenter Server 6.0, see Location of VMware vCenter Server 6.0 log files (2110014)
Note: If the service is running under a specific user, the logs may be located in the profile directory of that user instead of %ALLUSERSPROFILE%.

vpxd.log: The main vCenter Server log, consisting of all vSphere Client and WebServices connections, internal tasks and events, and communication with the vCenter Server Agent (vpxa) on managed ESXi/ESX hosts.
