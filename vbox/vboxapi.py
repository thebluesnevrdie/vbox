import bottle, subprocess
from bottle import run, get

# TODO: need to add multi-OS "which" to find this
VBoxManagePath = ['/usr/bin/VBoxManage']

def runVBoxManage(opts):
    command = VBoxManagePath + opts
    process = subprocess.check_output(command)
    return process.splitlines()

@get('/info')
def getVBoxVersion():
    our_version = runVBoxManage(['-v'])[0]
    return {'version': our_version }

if __name__ == "__main__":
    run(host='localhost', port=8000, debug=True, reloader=True)
