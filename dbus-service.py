
from threading import Thread
from gi.repository import GLib
from pydbus import SystemBus
from pydbus.generic import signal
import pkg_resources
from time import sleep
from prototype import *
import pwd

load97()

loop = GLib.MainLoop()

def uname2identity(uname):
    if uname == '':
        # For some reason Gnome enrollment UI does not send the user name
        # (it also ignores our num-enroll-stages attribute). I probably should upgrade Gnome
        print('No username specified. ')
        uname = 'unicorn'
    pw=pwd.getpwnam(uname)
    sidstr='S-1-5-21-111111111-1111111111-1111111111-%d' % pw.pw_uid
    return sid_from_string(sidstr)


class Device():
    name = 'Validity sensor'

    def __init__(self):
        setattr(self, 'num-enroll-stages', 7)
        setattr(self, 'scan-type', 'press')

    def Claim(self, usr):
        print('In Claim %s' % usr)

    def Release(self):
        print('In Release')
        
    def ListEnrolledFingers(self, usr):
        print('In ListEnrolledFingers %s' % usr)

        usr=db.lookup_user(uname2identity(usr))

        if usr == None:
            print('User not found on this device')
            return []
        
        rc = [subtype_to_string(f['subtype']) for f in usr.fingers]
        print(repr(rc))
        return rc

    def do_scan(self):
        try:
            z=identify()
            self.VerifyStatus('verify-match', True)
        except Exception as e:
            print('Opps: %s' % repr(e))
            self.VerifyStatus('verify-no-match', True)

    def VerifyStart(self, finger_name):
        print('In VerifyStart %s' % finger_name)
        Thread(target=lambda: self.do_scan()).start()

    def VerifyStop(self):
        print('In VerifyStop')

    def DeleteEnrolledFingers(self, user):
        print('In DeleteEnrolledFingers %s' % user)
        usr=db.lookup_user(uname2identity(user))

        if usr == None:
            print('User not found on this device')
            return

        db.del_record(usr.dbid)

    def do_enroll(self, finger_name):
        # it is pointless to try and remember username passed in claim as Gnome does not seem to be passing anything useful anyway
        try:
            # hardcode the username and finger for now
            z=enroll(uname2identity('unicorn'), 0xf5)
            print('Enroll was successfull')
            self.EnrollStatus('enroll-completed', True)
        except Exception as e:
            print('Enroll failed %s' % repr(e))
            self.EnrollStatus('enroll-failed', True)

    def EnrollStart(self, finger_name):
        print('In EnrollStart %s' % finger_name)
        Thread(target=lambda: self.do_enroll(finger_name)).start()
        

    def EnrollStop(self):
        print('In EnrollStop')

    VerifyFingerSelected = signal()
    VerifyStatus = signal()
    EnrollStatus = signal()

class Manager():
    def GetDevices(self):
        print('In GetDevices')
        return ['/net/reactivated/Fprint/Device/0']

    def GetDefaultDevice(self):
        print('In GetDefaultDevice')
        return '/net/reactivated/Fprint/Device/0'


def readif(fn):
    with open('/usr/share/dbus-1/interfaces/' + fn, 'rb') as f:
        # for some reason Gio can't seem to handle XML entities declared inline
        return f.read().decode('utf-8') \
                .replace('&ERROR_CLAIM_DEVICE;', 'net.reactivated.Fprint.Error.ClaimDevice') \
                .replace('&ERROR_ALREADY_IN_USE;', 'net.reactivated.Fprint.Error.AlreadyInUse') \
                .replace('&ERROR_INTERNAL;', 'net.reactivated.Fprint.Error.Internal') \
                .replace('&ERROR_PERMISSION_DENIED;', 'net.reactivated.Fprint.Error.PermissionDenied') \
                .replace('&ERROR_NO_ENROLLED_PRINTS;', 'net.reactivated.Fprint.Error.NoEnrolledPrints') \
                .replace('&ERROR_NO_ACTION_IN_PROGRESS;', 'net.reactivated.Fprint.Error.NoActionInProgress') \
                .replace('&ERROR_INVALID_FINGERNAME;', 'net.reactivated.Fprint.Error.InvalidFingername') \
                .replace('&ERROR_NO_SUCH_DEVICE;', 'net.reactivated.Fprint.Error.NoSuchDevice')

Device.dbus=[readif('net.reactivated.Fprint.Device.xml')]
Manager.dbus=[readif('net.reactivated.Fprint.Manager.xml')]


bus = SystemBus()
bus.publish('net.reactivated.Fprint', 
        ('/net/reactivated/Fprint/Manager', Manager()), 
        ('/net/reactivated/Fprint/Device/0', Device())
    )
loop.run()
