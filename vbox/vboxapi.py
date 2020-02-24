import subprocess
from fastapi import FastAPI, HTTPException

app = FastAPI()

# TODO: need to add multi-OS "which" to find this
VBoxManagePath = ["/usr/bin/VBoxManage"]


def _runVBoxManage(opts):
    command = VBoxManagePath + opts
    print(command)
    process = subprocess.run(command, capture_output=True)
    if process.returncode != 0:
        error_list = process.stderr.splitlines()
        print(error_list)
        # if VBoxManage usage info is included in output, skip it
        if (len(error_list) > 4) and (error_list[4] == b"Usage:"):
            error_list = error_list[749:]
        our_error = []
        for err in error_list:
            tmp_error = err.decode("ascii")
            # strip the following prefix from error lines
            if tmp_error.startswith("VBoxManage: error: "):
                our_error.append(tmp_error[19:])
            else:
                our_error.append(tmp_error)
        raise HTTPException(status_code=404, detail=our_error)
    else:
        our_output = []
        for line in process.stdout.splitlines():
            our_output.append(line.decode("ascii"))
        return our_output


@app.get("/host")
def getHostInfo():
    version = _runVBoxManage(["-v"])[0]
    info = {"version": version, "CPUs": {}}
    hostinfo = _runVBoxManage(["list", "hostinfo"])[2:]
    for line in hostinfo:
        if line.startswith("Host time"):
            info["Host time"] = line[11:]
        elif line.startswith("Processor#"):
            cpu_num = line[10]
            tmp_key, val = line.split(":")
            key = tmp_key[12:]
            if not info["CPUs"].get(cpu_num):
                info["CPUs"][cpu_num] = {}
            info["CPUs"][cpu_num][key] = val.strip()
        else:
            key, val = line.split(":")
            info[key] = val.strip()
    return info


@app.get("/host/extpacks")
def getHostExtpacks():
    extpacks = {}
    extpacks_list = _runVBoxManage(["list", "extpacks"])[1:]
    if len(extpacks_list) == 0:
        return {}
    for line in extpacks_list:
        if line.startswith("Pack no."):
            tmp_key, val = line.split(":")
            key = tmp_key[8:].strip()
            extpacks[key] = {"Name": val.strip()}
            current_pack = key
        else:
            key, val = line.split(":")
            extpacks[current_pack][key] = val.strip()
    return extpacks


@app.get("/host/ostypes")
def getHostOstypes():
    ostypes = {}
    ostypes_list = _runVBoxManage(["list", "ostypes"])
    for line in ostypes_list:
        if len(line) == 0:
            continue
        if line.startswith("ID"):
            current_ostype = line[3:].strip()
            ostypes[current_ostype] = {}
        else:
            key, val = line.split(":")
            ostypes[current_ostype][key] = val.strip()
    return ostypes


@app.get("/host/properties")
def getHostProperties():
    properties = {}
    properties_list = _runVBoxManage(["list", "systemproperties"])
    for line in properties_list:
        key, val = line.split(":")
        properties[key] = val.strip()
    return properties


@app.get("/host/usb")
def getHostUsb():
    raise HTTPException(status_code=501)


@app.get("/machines")
def getMachinesList():
    all_vms = {}
    running_vms = []
    all_list = _runVBoxManage(["list", "vms"])
    running_list = _runVBoxManage(["list", "runningvms"])
    for line in running_list:
        uuid_start = line.find("{") + 1
        running_vms.append(line[uuid_start:-1])
    for line in all_list:
        tmp_name, tmp_uuid = line.split('" {')
        name = tmp_name[1:]
        uuid = tmp_uuid[:-1]
        all_vms[name] = {"uuid": uuid, "running": "false"}
        if uuid in running_vms:
            all_vms[name]["running"] = "true"
    return all_vms


@app.get("/machines/{vm}")
def getMachinesNodeInfo(vm: str):
    raise HTTPException(status_code=501)


@app.get("/machines/{vm}/nics")
def getMachinesNodeNics(vm: str):
    raise HTTPException(status_code=501)


@app.get("/machines/{vm}/shares")
def getMachinesNodeShares(vm: str):
    raise HTTPException(status_code=501)


@app.get("/dhcpservers")
def getDhcpserversList():
    raise HTTPException(status_code=501)


@app.get("/dhcpservers/{server}")
def getDhcpserverInfo(server: str):
    raise HTTPException(status_code=501)


@app.get("/hostonlynets")
def getHostonlynetsList():
    raise HTTPException(status_code=501)


@app.get("/hostonlynets/{net}")
def getHostonlyInfo(net: str):
    raise HTTPException(status_code=501)


@app.get("/natnetworks")
def getNatnetworksList():
    raise HTTPException(status_code=501)


@app.get("/natnetworks/{net}")
def getNatnetworkInfo(net: str):
    raise HTTPException(status_code=501)
