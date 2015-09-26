import subprocess
import urlparse

import redis
from requests.adapters import HTTPAdapter
from structlog import get_logger
from bs4 import BeautifulSoup
from pyquery import PyQuery as pq

MAX_RETRIES = 3
TIMEOUT = 3


def do_request(url, session, use_cache=False, **kwargs):
    """Does an http request and optionally uses redis cache
    before doing the request.

    :param session obj: :class:`requests.Session` instance
    :param use_cache bool: use redis cache before doing a htpp request
    :param kwargs: passed to :meth:`requests.Session().request()` function
    :returns: response body
    :rtype: unicode
    """
    logger = get_logger(__name__)
    logger = logger.bind(url=url)

    # setup requests to be a bit less error prone
    kwargs['timeout'] = TIMEOUT
    session.mount('http://', HTTPAdapter(max_retries=MAX_RETRIES))
    session.mount('https://', HTTPAdapter(max_retries=MAX_RETRIES))

    # check redis for cached content
    rc = redis.StrictRedis()
    redis_key = 'responsecache|{}'.format(url)
    if use_cache:
        value = rc.get(redis_key)
        if value:
            return content_to_pyquery(value, url)
        else:
            logger.debug('No cache value', redis_key=redis_key)

    method = kwargs.pop('method', 'get')
    logger = logger.bind(method=method)
    logger.debug('fetching url')
    response = session.request(method, url, **kwargs)
    # TODO: can we do something about it?
    response.raise_for_status()
    rc.set(redis_key, response.content)
    return content_to_pyquery(response.content, url)


def content_to_pyquery(content, url):
    fixed_content = str(BeautifulSoup(content, "lxml"))
    doc = pq(fixed_content, parser="html")
    doc.remove_namespaces()
    doc.make_links_absolute(urlparse.urljoin(url, '/'))
    return doc


def debug_html(content):
    """Opens a browser with given html"""
    f = open('/tmp/test.html', 'w')
    f.write(str(content))
    f.flush()
    subprocess.check_output(['chromium-browser', f.name])
