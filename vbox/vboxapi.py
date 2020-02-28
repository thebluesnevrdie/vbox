import re, subprocess
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
    def _buildSharedFolders():
        # --machinereadable output does not include readonly and auto-mount details, so we must get
        shares_detail = _runVBoxManage(["showvminfo", vm])
        details = {}
        processing = False
        for line in shares_detail:
            if processing:
                # share detail lines look like:
                # Name: 'share1', Host path: '/srv/testshare1' (machine mapping), writable
                # Name: 'share2', Host path: '/srv/testshare2' (machine mapping), readonly, auto-mount
                # Name: 'share3', Host path: '/srv/testshare3' (machine mapping), writable, mount-point: '/media'
                # Name: 'share4', Host path: '/srv/testshare4' (machine mapping), readonly, auto-mount, mount-point: '/mnt'
                if line.startswith("Name: "):
                    split = line.split(",")
                    begin = split[0].find("'") + 1
                    key = split[0][begin:-1]
                    details[key] = {}
                    path_match = re.match(
                        " Host path\: '(.+)' \(machine mapping\)", split[1]
                    )
                    details[key]["Path"] = path_match.group(1)
                    if split[2] == " readonly":
                        details[key]["Readonly"] = "true"
                    else:
                        details[key]["Readonly"] = "false"

                    if len(split) > 3:
                        if "point" in split[-1]:
                            index = split[-1].find("'") + 1
                            details[key]["Mountpoint"] = split[-1][index:-1]
                            if len(split) == 5:
                                details[key]["Automount"] = "true"
                            else:
                                details[key]["Automount"] = "false"
                        else:
                            details[key]["Mountpoint"] = "none"
                            details[key]["Automount"] = "true"
                    else:
                        details[key]["Mountpoint"] = "none"
                        details[key]["Automount"] = "false"
            else:
                if line.startswith("Shared folders:"):
                    # skip all other lines until we get to the shares towards the end
                    processing = True
        return details

    def _buildVRDE(keys):
        vrde = {"properties": {}}
        for tmp_key, val in keys.items():
            if tmp_key == "vrde":
                if val == "off":
                    return {"enabled": "false"}
                else:
                    vrde["enabled"] = "true"
            elif tmp_key.startswith("vrdeproperty"):
                prop_key = tmp_key[13:-1]
                key, subkey = prop_key.split("/")
                if not vrde["properties"].get(key):
                    vrde["properties"][key] = {}
                vrde["properties"][key][subkey] = val.strip("<>")
            else:
                key = tmp_key[4:]
                vrde[key] = val
        return vrde

    nodeinfo = {}
    vrde_list = {}
    found_shares = False
    nodeinfo_list = _runVBoxManage(["showvminfo", vm, "--machinereadable"])
    for line in nodeinfo_list:
        tmp_key, tmp_val = line.split("=")
        key = tmp_key.strip('"')
        val = tmp_val.strip('"')
        if key.startswith("vrde"):
            vrde_list[key] = val
        elif key.startswith("SharedFolder"):
            found_shares = True
        else:
            nodeinfo[key] = val
    nodeinfo["vrde"] = _buildVRDE(vrde_list)
    if found_shares:
        nodeinfo["shares"] = _buildSharedFolders()
    return nodeinfo


@app.get("/dhcpservers")
def getDhcpserversList():
    dhcpserv = {}
    dhcpserv_list = _runVBoxManage(["list", "dhcpservers"])
    for line in dhcpserv_list:
        if len(line) == 0:
            continue
        if line.startswith("NetworkName"):
            globalopts = False
            key, val = line.split(": ")
            current_dhcp = val.strip()
            dhcpserv[current_dhcp] = {}
        elif globalopts:
            key, val = line.split(":")
            dhcpserv[current_dhcp]["Global opts"][key.strip()] = val.strip()
        elif line.startswith("Global options"):
            dhcpserv[current_dhcp]["Global opts"] = {}
            globalopts = True
        else:
            key, val = line.split(": ")
            dhcpserv[current_dhcp][key] = val.strip()
    return dhcpserv


@app.get("/hostonlynets")
def getHostonlynetsList():
    hostonly = {}
    hostonly_list = _runVBoxManage(["list", "hostonlyifs"])
    for line in hostonly_list:
        if len(line) == 0:
            continue
        if line.startswith("Name:"):
            current_hostonly = line[5:].strip()
            hostonly[current_hostonly] = {}
        else:
            key, val = line.split(": ")
            hostonly[current_hostonly][key] = val.strip()
    return hostonly


@app.get("/intnets")
def getInternalnetsList():
    intnets = []
    intnets_list = _runVBoxManage(["list", "intnets"])
    for line in intnets_list:
        key, val = line.split(":")
        intnets.append(val.strip())
    return intnets


@app.get("/natnetworks")
def getNatnetworksList():
    raise HTTPException(status_code=501)
