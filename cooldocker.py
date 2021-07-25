#!/usr/bin/env python3

""" CoolDocker || list docker entities with color and count """

__version__ = "1.0.0"

from argparse import (
    ArgumentParser,
    ArgumentTypeError
)
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass
from datetime import (
    datetime as dt,
    timedelta
)
from tabulate import tabulate as tab
from termcolor import colored as co
from docker.errors import ( #type: ignore
    APIError, #type: ignore
    DockerException, #type: ignore
)
from docker.models.images import Image #type: ignore
from docker.models.containers import Container #type: ignore
from docker.models.volumes import Volume #type: ignore
from docker.models.networks import Network #type: ignore
from docker import ( #type: ignore
    from_env, #type: ignore
    DockerClient #type: ignore
)

@dataclass
class CoolDockerEntity:
    """
    defines the dat for a single entity
    for cooldocker entities
    """
    name: str
    cols: List[str]
    data: Dict[str, Tuple[str, ...]]
    count: int

class CoolDockerParser:
    """
    Parser for Docker Entities
    Currently supporting:
    - Containers
    - Images
    - Volumes
    - Networks
    """
    def __init__(self, client):
        self.client: DockerClient = client
        self.ctx: Dict[str, CoolDockerEntity] = {}

    # calc the delta from a given time string to current time
    # following a given format
    @staticmethod
    def __timedelta(time: str, pattern: str = "%Y-%m-%dT%H:%M:%S") -> str:
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
    @staticmethod
    def print(entity: CoolDockerEntity, want: bool = True, color: str = None) -> None:
        if not want:
            return
        print(f"[{co(str(entity.count), color=color)}] {co(entity.name, color=color)}:")
        print(tab(entity.data.values(), headers=entity.cols) + "\n")

    def containers(self) -> CoolDockerEntity:
        data: Dict[str, Tuple[str, ...]] = {}
        cols: List[str] = [ "CONTAINER ID", "IMAGE", "CREATED",
                            "STATUS", "PORTS", "NAMES", "IP ADDRESS" ]

        container_list: List[Container] = self.client.containers.list()
        for container in container_list:
            attrs: Dict[str, Any] = container.attrs
            config: Dict[str, Any] = attrs["Config"]

            # get container base data
            container_name: str = config["Hostname"]
            image: str = config["Image"]
            names: str = attrs["Name"][1:]
            created: str = self.__timedelta(time=attrs["Created"])


            ns: dict = attrs["NetworkSettings"]

            # get all the ports and port mappings
            # from host to container and vice versa
            network_ports: Dict[Any, Any] = ns["Ports"].items()
            ports: str = ""
            for port, mapping in network_ports:
                ports += f"{port}"
                if mapping:
                    for item in mapping:
                        host_ip = item["HostIp"]
                        host_port = item["HostPort"]
                        ports += f"{host_ip}:{host_port}->{port} "

            # get the container ip
            ip: str = ns["IPAddress"]
            network_mode = attrs["HostConfig"]["NetworkMode"]
            if network_mode != "default":
                ip = ns["Networks"][network_mode]["IPAddress"]

            # get the current container status
            state = attrs["State"]
            status: str = state["Status"]
            if "Health" in state:
                health_state = state["Health"]["Status"]
                status = f"{status} ({health_state})"

            data[container_name] = container_name, image, created, status, ports, names, ip

        count: int = len(data)
        name: str = "CONTAINER" if count <= 1 else "CONTAINERS"
        self.ctx["containers"] = CoolDockerEntity(
            name=name,
            cols=cols,
            data=data,
            count=count,
        )
        return self.ctx["containers"]

    def images(self, filters: Dict[str, bool] = None) -> CoolDockerEntity:
        data: Dict[str, Tuple[str, ...]] = {}
        cols: List[str] = [ "ID", "REPO", "TAG", "CREATED", "SIZE (MiB)" ]

        filters = filters if filters else { "dangling": False }
        filtered_images: List[Image] = self.client.images.list(filters=filters)
        for image in filtered_images:
            attrs: Dict[str, Any] = image.attrs

            image_id: str = attrs["Id"]
            created: str = self.__timedelta(time=attrs["Created"])
            mib_image_size = f"{attrs['Size']/8/1024**2:07.3f} MiB"
            repo_tags: List[str] = attrs["RepoTags"]
            first_tag: List[str] = repo_tags[0].split(":")
            tags_count: int = len(repo_tags)
            repo: str = first_tag[0] if tags_count >= 1 else ""
            tags: str = first_tag[1] if tags_count >= 1 else ""

            data[image_id] = image_id, repo, tags, created, mib_image_size

        count: int = len(data)
        name: str = "IMAGE" if count <= 1 else "IMAGES"
        self.ctx["images"] = CoolDockerEntity(
            name=name,
            cols=cols,
            data=data,
            count=count,
        )
        return self.ctx["images"]

    def networks(self, filters: Dict[str, bool] = None) -> CoolDockerEntity:
        data: Dict[str, Tuple[str, ...]] = {}
        cols: List[str] = [ "NET ID", "NAME", "DRIVER", "CREATED",
                            "SCOPE", "INTERNAL", "ATTACHABLE"]

        filters = filters if filters else { "dangling": True }
        filtered_networks: List[Network] = self.client.networks.list(filters=filters)
        for network in filtered_networks:
            attrs: Dict[str, Any] = network.attrs

            network_id: str = attrs['Id']
            network_name: str = attrs["Name"]
            driver: str = attrs["Driver"]
            created: str = self.__timedelta(time=attrs["Created"])
            scope: str = attrs["Scope"]
            is_internal: str = attrs["Internal"]
            is_attachable: str = attrs["Attachable"]

            data[network_id] = (network_id, network_name, driver, created,
                                scope, is_internal, is_attachable )
        count: int = len(data)
        name: str = "NETWORK" if count <= 1 else "NETWORKS"
        self.ctx["networks"] = CoolDockerEntity(
            name=name,
            cols=cols,
            data=data,
            count=count,
        )
        return self.ctx["networks"]

    def volumes(self) -> CoolDockerEntity:
        data: Dict[str, Tuple[str, ...]] = {}
        cols: List[str] = [ "NAME", "DRIVER", "VOLUME", "SCOPE"]

        volumes: List[Volume] = self.client.volumes.list()
        for volume in volumes:
            attrs: Dict[str, Any] = volume.attrs
            volume_name: str = attrs["Name"]
            driver: str = attrs["Driver"]
            scope: str = attrs["Scope"]

            data[volume_name] = volume_name, driver, scope

        count: int = len(data)
        name: str = "VOLUME" if count <= 1 else "VOLUMES"
        self.ctx["volumes"] = CoolDockerEntity(
            name=name,
            cols=cols,
            data=data,
            count=count,
        )
        return self.ctx["volumes"]

def main(args=None):
    try:
        docker_client = from_env()
        cooldocker = CoolDockerParser(client=docker_client)

        args.all = not any([args.c, args.i, args.n, args.v])
        cooldocker.print(want=args.all or args.c, entity=cooldocker.containers(), color="cyan")
        cooldocker.print(want=args.all or args.i, entity=cooldocker.images(), color="red")
        cooldocker.print(want=args.all or args.n, entity=cooldocker.networks(), color="green")
        cooldocker.print(want=args.all or args.v, entity=cooldocker.volumes(), color="magenta")

    except (APIError, DockerException) as err:
        print(f"Docker Engine might not be running. Please check if it is and run this again. \nMessage: {err}")


# https://stackoverflow.com/questions/15008758/parsing-boolean-values-with-argparse
def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise ArgumentTypeError('Boolean value expected.')

if __name__ == "__main__":
    __version__ = "1.0.0"

    parser = ArgumentParser(
        description="list docker entities with color and count",
        epilog="For issues visit https://github.com/lukasjoc/cooldocker/issues"
    )

    parser.add_argument("--all", type=str2bool, nargs='?', const=True,
    			      default=True, help="Show Everything")

    parser.add_argument("-c", type=str2bool, nargs='?', const=True,
    			      default=False, help="Show containers")

    parser.add_argument("-i", type=str2bool, nargs='?', const=True,
    		              default=False, help="Show images")

    parser.add_argument("-n", type=str2bool, nargs='?', const=True,
    			      default=False, help="Show networks")

    parser.add_argument("-v", type=str2bool, nargs='?', const=True,
			      default=False, help="Show volumes")

    parser.add_argument('--version', action='version',
                                     version='%(prog)s 1.0.0')
    args = parser.parse_args()
    main(args=args)

