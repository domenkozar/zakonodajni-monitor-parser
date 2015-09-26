"""
Separation of concerns:

- cli interface
- http download (with offline cache)
- parsing
- populating the database

"""
import pdb

import click
import functools
import requests

from utils import do_request
import parsers


@click.command()
@click.option(
    '--disable-pdb',
    default=False,
    is_flag=True,
)
@click.option(
    '--skip-http-cache',
    default=False,
    is_flag=True,
)
def cli(skip_http_cache, disable_pdb):
    """
    """
    session = requests.Session()
    new_do_request = functools.partial(
        do_request,
        session=session,
        use_cache=not skip_http_cache,
    )

    try:
        violations = list(parsers.parse_violations(new_do_request))
        people = list(parsers.parse_people(new_do_request))
        sessions = list(parsers.parse_sessions(new_do_request))
    except:
        if not disable_pdb:
            pdb.post_mortem()

    # write to mongodb: Representatives, VotingSessions, Laws, Quotes, Lobbying
