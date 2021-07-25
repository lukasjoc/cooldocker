from typing import List, Dict
from dataclasses import dataclass
from datetime import (datetime as dt, timedelta)
from tabulate import tabulate
from termcolor import colored
from docker import from_env, DockerClient # type: ignore

@dataclass
class CoolDockerEntity:
    # defines the dat fro a single entity
    # for cooldocker entities
    name: str
    cols: List[str]
    data: Dict[str, Dict[str, str]]
    count: int

class CoolDockerParser:
    def __init__(self, client):
        self.client: DockerClient = client
        self.ctx: Dict[str, CoolDockerEntity] = {}

    # calc the delta from a given time string to current time
    # following a given format
    def __timedelta(self, time: str, pattern: str="%Y-%m-%dT%H:%M:%S") -> str:
        delta = abs(
            dt.strptime(dt.strftime(dt.today(), pattern), pattern)
            - dt.strptime(time.split(".")[0], pattern)
        )
        delta_secs_total = int(delta.total_seconds()) - (60*60)
        delta_time_str: str = str(timedelta(seconds=delta_secs_total))
        return (f"> {delta.days} days ago"
                if delta.days >= 1
                else f"{delta_time_str} ago")

    # print the table data in a tabulated way and
    # also print the count of the entity in a header line
    def print(self, entity: CoolDockerEntity, color: str=None) -> None:
        entity_name: str = entity.name
        entity_count: str = str(len(entity.data.keys()))
        print(f"[{colored(entity_count, color=color)}] {colored(entity_name, color=color)}:")
        print(tabulate([a.values() for a in entity.data.values()], headers=entity.cols))

    def containers(self) -> CoolDockerEntity:
        data = {}
        container_list: list = self.client.containers.list()
        cols = [ "CONTAINER ID", "IMAGE", "CREATED", "STATUS", "PORTS", "NAMES", "IP ADDRESS" ]

        for container in container_list:
            attrs: dict = container.attrs
            ns: dict = attrs["NetworkSettings"]
            config: dict = attrs["Config"]

            # get container base data
            name = config["Hostname"]
            image = config["Image"]
            names = attrs["Name"][1:]
            created = self.__timedelta(time=attrs["Created"])

            # get all the ports and port mappings
            # from host to container
            # and vice versa
            cports = ns["Ports"].items()
            ports: str = ""
            for port, mapping in cports:
                ports += f"{port}"
                if mapping:
                    for item in mapping:
                        host_ip = item["HostIp"]
                        host_port = item["HostPort"]
                        ports += f"{host_ip}:{host_port}->{port} "

            # get the container ip
            ip = ns["IPAddress"]
            network_mode = attrs["HostConfig"]["NetworkMode"]
            if network_mode != "default":
                ip = ns["Networks"][network_mode]["IPAddress"]

            # get the current container status
            state = attrs["State"]
            status = state["Status"]
            if "Health" in state:
                health_state = state["Health"]["Status"]
                status = f"{status} ({health_state})"

            data[name] = {
                "name": name,
                "image": image,
                "created": created,
                "status": status,
                "ports": ports,
                "names": names,
                "ip": ip,
            }

        count = len(data)
        name = "CONTAINER" if count <= 1 else "CONTAINERS"
        self.ctx["containers"] = CoolDockerEntity(
            name=name,
            cols=cols,
            data=data,
            count=count,
        )
        return self.ctx["containers"]


#         def image_info(client):
#             image_data = []
#             for image in client.images.list(filters={"dangling": False}):
#                 attrs = image.attrs
#                 def get_image_repo():
#                     if len(attrs["RepoTags"]) >= 1:
#                         return attrs["RepoTags"][0].split(":")[0]
#
#                 def get_image_tag():
#                     if len(attrs["RepoTags"]) >= 1:
#                         return attrs["RepoTags"][0].split(":")[1]
#
#                 def get_image_size():
#                     return attrs["Size"]/8/(1024**2)
#
#                 image_data.append([
#                     get_image_repo(),
#                     get_image_tag(),
#                     __format_timedelta(time_str=attrs["Created"]),
#                     get_image_size(),
#                     ])
#
#             image_cols = [ "REPOSITORY", "TAG", "CREATED", "SIZE(MiB)" ]
#             return image_data, image_cols
#
#         def net_info(client):
#             net_data = []
#             for net in client.networks.list(filters={"dangling": True}):
#                 attrs = net.attrs
#                 net_data.append([
#                     attrs['Id'][:7],
#                     attrs["Name"],
#                     attrs["Driver"],
#                     __format_timedelta(time_str=attrs["Created"]),
#                     attrs["Scope"],
#                     attrs["Internal"],
#                     attrs["Attachable"],
#                     ])
#
#             net_cols = [ "NET ID", "NAME", "DRIVER", "CREATED", "SCOPE", "INTERNAL", "ATTACHABLE"]
#             return net_data, net_cols
#
#         def vol_info(client):
#             vol_data = []
#             for vol in client.volumes.list():
#                 attrs = vol.attrs
#                 vol_data.append([
#                     attrs["Name"],
#                     attrs["Driver"],
#                     attrs["Scope"],
#                     ])
#
#             vol_cols = [ "NAME", "DRIVER", "VOLUME", "SCOPE"]
#             return vol_data, vol_cols

if __name__ == "__main__":
    try:
	# print the data count in the right color
	#def print_counts(what: str, color: str, count: int) -> None:
        # print(f"[{colored(str(count), color=color)}] {colored(what, color=color)}:")

        docker_client = from_env()
        cooldocker = CoolDockerParser(client=docker_client)

        cooldocker.print(entity=cooldocker.containers(), color="cyan")


        #container_data, container_cols = container_info(client=cl)
        #print(f"[{colored(str(len(container_data)), color='cyan')}] {colored('CONTAINER', color='cyan')}:")
        #print(tabulate(container_data, headers=container_cols))

        #image_data, image_cols = image_info(client=cl)
        #print(f"\n[{colored(str(len(image_data)), color='green')}] {colored('IMAGES', color='green')}:")
        #print(tabulate(image_data, headers=image_cols))

        #net_data, net_cols = net_info(client=cl)
        #print(f"\n[{colored(str(len(net_data)), color='blue')}] {colored('NETS', color='blue')}:")
        #print(tabulate(net_data, headers=net_cols))

        #vol_data, vol_cols = vol_info(client=cl)
        #if len(vol_data) >= 1:
        #    print(f"\n[{colored(str(len(net_data)), color='yellow')}] {colored('VOLUMES', color='yellow')}:")
        #    print(tabulate(vol_data, headers=vol_cols))
    except Exception as err:
        print(f"Docker Engine/Daemon not running. Please start it. ERR: {err}")

