import getpass
import os, sys, logging
from jnpr.junos import Device
from jnpr.junos.utils.sw import SW
from jnpr.junos.utils.config import Config
from jnpr.junos.exception import ConnectError
from jnpr.junos.exception import ConfigLoadError
from jnpr.junos.exception import CommitError
from jnpr.junos.exception import LockError
from jnpr.junos.exception import UnlockError
import time

path = '/home/jvyas/projects/juniper_upgrade/upgrade_logs/'
hostName = input ("Enter the Juniper Device Hostname that want to upgrade : " + str())
uName = input ("Enter Your User Name : " + str())
uPass = getpass.getpass("Enter " + uName + " Password : ")
logfileName = input("Enter File Name to store Logs : " + str())
#The package variable defines the path on the local server to the new Junos OS image. Because the no_copy parameter
#defaults to False, the installation process copies the software image from the local server to the target device.

package = input("Enter the JUNOS package Name to install with extension : " + str())

#The remote_path variable defines the path on the target device to which the software package is copied.
#The default is /var/tmp.
remote_path = '/var/tmp'
validate = True
no_copy= True
#logfile = '/Users/jvyas34/Desktop/PYTHON/Python Projects/JUNOS Upgrade/install_4.log'
logfile = path + str(logfileName)+".log"
print("#="*40)
print("Verifying number of Routing Engine in " + str(hostName))
print("#="*40)

try:
    dev = Device(host=hostName, user=uName, password=uPass)
    dev.open()
    Dual_RE_Check = dev.facts['2RE']
    print("Device Has 2 Routing Engine :-" + str(Dual_RE_Check))
    dev.close()
except ConnectError as err:
    print("Cannot connect to device: {0}".format(err))
    sys.exit(1)

#===============================================================================
def update_progress(dev, report):
    #log the progress of the installing process
    logging.info(report)

#===============================================================================

def addconfig(Config_File):
    dev = Device(host=hostName, user=uName, password=uPass)
    dev.open()
    dev.bind(cu=Config)
    print("#="*40)
    print("binding the device to configuration mode")
    print("#="*40)

    try:
        # Lock the configuration, load configuration changes, and commit
        dev.cu.lock()
        print("Strep:1 ==> Locking the configuration")
    except LockError as err:
        dev.close()
        print("Step:1 ==> Unable to lock configuration: {0}".format(err))

    try:
        dev.cu.load(template_path=Config_File, format="set", merge=True)
        print("Step2: ==> Loading configuration changes : Adding command for Routing Engine Redundancy")
    except (ConfigLoadError, Exception) as err:
        print("Step2: ==> Unable to load configuration changes: {0}".format(err))

    try:
        dev.cu.commit(comment='Juniper JUNOS Device Upgrade')
        print("Step3: ==> Committing the configuration : Routing Engine Redundancy Commands Added")
    except CommitError as err:
        print("Step3: ==> Unable to commit configuration: {0}".format(err))

    try:
        dev.cu.unlock()
        print("Step4: ==> Unlocking the configuration")
    except UnlockError as err:
        print("Step4: ==> Unable to unlock configuration: {0}".format(err))

    dev.close()
#===============================================================================
REBOOT_WAITING = 90
PROBE_DELAY = 20
def rechability():
    time.sleep(REBOOT_WAITING)

    while dev.probe(PROBE_DELAY) != True:
        print("Ping or Netconf is not Reachable")
        dev.probe(PROBE_DELAY)
    print("Reboot completed and Ping/Netconf is Available Now")
    print("Please don't login to configuration mode. if something needs to verify then please verify it through User mode only")

    time.sleep(300)

#===============================================================================

def JunosSwUpgrade():

    # initialize logging
    logging.basicConfig(filename=logfile, level=logging.INFO,
                        format='%(asctime)s:%(name)s: %(message)s')
    logging.getLogger().name = hostName
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.info('Information logged in {0}'.format(logfile))

    if no_copy == False:
        # verify package exists
        if not (os.path.isfile(package)):
            msg = 'Software package does not exist: {0}. '.format(package)
            logging.error(msg)
            print("Package not Exists error and exit with system exit")
            sys.exit()

    dev = Device(host=hostName, user=uName, password=uPass)

    try:
        dev.open()
    except ConnectError as err:
        logging.error('Cannot connect to device: {0}\n'.format(err))
        print("Connection issue with the Target device")
        return

    # Create an instance of SW
    sw = SW(dev)

    try:
        logging.info('Starting the software upgrade process: {0}' \
                     .format(package))
        print("Starting software upgrade process")
        ok = sw.install(package=package, remote_path=remote_path,
                        progress=update_progress, validate=validate, no_copy=True, all_re=True)
    except Exception as err:
        msg = 'Unable to install software, {0}'.format(err)
        logging.error(msg)
        ok = False

    if ok is True:
        logging.info('Software installation complete. Rebooting')
        rsp = sw.reboot()
        logging.info('Upgrade pending reboot cycle, please be patient.')
        logging.info(rsp)
    else:
        msg = 'Unable to install software, {0}'.format(ok)
        logging.error(msg)

    # End the NETCONF session and close the connection
    dev.close()

#===============================================================================

def main():

    if Dual_RE_Check == True:
        print("#+"*40)
        print("Dual RE Upgrade")
        print("Doing Configuration to Deactivate Gress between REs")
        print("#+"*40)

        deactivate_redundancy = "./config_files/set_config_deactivate_redundancy.set"
        addconfig(deactivate_redundancy)
        print("Deactivating command's execution completed")

        print("#+"*40)
        print("Dual RE Upgrade Starting")
        print("#+"*40)
        JunosSwUpgrade()

        print("#+"*40)
        print("After Upgrade checking Reachability of the Host")
        print("#+"*40)
        rechability()

        print("#+"*40)
        print("Doing Configuration to Activate Gress between REs")
        print("#+"*40)
        activate_redundancy = "./config_files/set_config_activate_redundancy.set"
        addconfig(activate_redundancy)
        print("Activating command's execution completed")
    else:
        print("#+"*40)
        print("Single RE Upgrade")
        print("#+"*40)
        JunosSwUpgrade()

        print("#+"*40)
        print("After Upgrade checking Reachability of the Host")
        print("#+"*40)
        rechability()

    print("#+"*40)
    print("After Device Upgraded Verifying New Version")
    print("#+"*40)
    dev.open()
    newVersion = dev.facts['version']
    print("Device Upgraded to : " + str(newVersion))
    print("Device Upgraded successfully and now closing session")
    dev.close()

if __name__ == "__main__":
    main()
