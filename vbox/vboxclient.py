import os
import sys
import click


@click.group()
def cli():
    return None


@click.group(name="server")
def server_group():
    return None


@server_group.command(name="runserver")
def runserver_command():
    print("stub run server")


cli.add_command(server_group)
main = cli
