""""""

import re
from functools import partial

import arrow
import toolz
from toolz import curried
from structlog import get_logger
from pyquery import PyQuery as pq

from utils import debug_html  # noqa


logger = get_logger(__name__)

VIOLATION_URL = 'http://stevec-krsitev.si'
DZ_RS_URL = 'https://www.dz-rs.si'
DZ_RS_SESSIONS_URL = DZ_RS_URL + '/wps/portal/Home/deloDZ/seje/sejeDrzavnegaZbora/PoDatumuSeje'
DZ_RS_PEOPLE_URL = DZ_RS_URL + '/wps/portal/Home/ODrzavnemZboru/KdoJeKdo/PoslankeInPoslanci/PoAbecedi'


def parse_violations(do_request):
    """"""
    logger.info('Parsing violations')

    return toolz.compose(
        # filter out meaningless values
        curried.filter(lambda x: x not in ('IME PREDPISA', '')),
        # extract data from each row
        curried.map(lambda tr: pq(tr).find('td').eq(1).text()),
        # get all rows in tables
        curried.mapcat(lambda page: page('table.MsoNormalTable tr')),
        # get all subpages
        curried.map(do_request),
        # let's skip empty urls/strings
        curried.filter(lambda a: a),
        # get menu links
        curried.map(lambda a: pq(a).attr('href')),
        # get menu elements
        lambda doc: doc('.moduletable_menu a'),
        # get main page
        do_request,
    )(VIOLATION_URL + '/index.php')


def parse_people(do_request):
    logger.info('Parsing people')

    def parse_representative(doc):
        doc = doc('div.wpsPortletBody')
        raw_birth_date = doc('fieldset table').eq(0).find('td').eq(1).text().replace(' ', '')
        return {
            'name': doc.find('h3').eq(0).text(),
            'birthDate': arrow.get(raw_birth_date, 'D.M.YYYY') if raw_birth_date else None,
            'image': DZ_RS_URL + doc.find('img').eq(0).attr('src'),
            'group': doc('.panelBox100 a').attr('href'),
            'location': doc(u'*:contains("Volilno okro")').parent().text().split(':')[1].strip(),
            'gender': "F" if 'Poslanka' in str(doc) else "M",
        }

    # get all people
    return toolz.compose(
        # get back metadata
        curried.map(parse_representative),
        # visit person's link
        curried.map(do_request),
        # get a link for each person
        lambda doc: doc("p.podnaslovOsebaLI a").map(lambda i, r: pq(r).attr('href')),
        # get page with a list of people
        do_request,
    )(DZ_RS_PEOPLE_URL)


def parse_sessions(do_request):
    """"""
    logger.info('Parsing sessions')

    def get_votings(voting_page):
        # parse transcripts for a session
        transcript_urls = voting_page(':contains("Zapisi seje")')\
            .closest('td')\
            .find('a')\
            .map(lambda i, r: pq(r).attr('href'))
        # TODO: parse transcript_urls

        # parse votings in a session
        epas_and_votes_urls = toolz.compose(
            lambda p: p('table.dataTableExHov > tbody tr')
                     # we're interested into those with more than one link
                     .filter(lambda i, r: len(pq(r).find('a')) > 1)
                     .map(lambda i, r: {'epa_url': pq(r).find('td').eq(0).find('a').attr('href'),
                                        'vote_url': pq(r).find('td').eq(3).find('a').attr('href')}),
        )(voting_page)
        # arrow.get('(23.09.2015)', 'DD.MM.YYYY')
        import pdb; pdb.set_trace()
        return {}

    return toolz.compose(
        # parse voting from session url
        curried.map(get_votings),
        # paginate all votings per session
        curried.mapcat(partial(paginate_url, do_request=do_request)),
        # get all session urls
        curried.map(lambda r: pq(r).attr('href')),
        # get all anchor elements per page
        curried.map(lambda p: p('table.dataTableExHov tbody a')),
        # get a list of all pages
        partial(paginate_url, do_request=do_request),
    )(DZ_RS_SESSIONS_URL)


def paginate_url(url, do_request):
    """Given a DZ_RS_URL crawl through pages using pagination logic"""
    # we can't cache yet cookies and POST requests
    do_request = partial(do_request, use_cache=False)

    def request_page(prefix, url, page_number):
        data = {
            prefix: prefix,
            '{}:menu1'.format(prefix): 'VII',
            '{}:menu2'.format(prefix): 'SEJ_ZAP_KON | MAG | DOK | fa_dokument | fa_sklicSeje | fa_program | fa_sklep',
            '{}:txtQueryString'.format(prefix): '',
            '{}:tableEx1:goto1__pagerGoText'.format(prefix): str(page_number),
            '{}:tableEx1:goto1__pagerGoButton'.format(prefix): 'Go',
            '{}:tableEx1:goto1__pagerGoButton.x'.format(prefix): '8',
            '{}:tableEx1:goto1__pagerGoButton.y'.format(prefix): '10',
            'javax.faces.ViewState': doc('input#javax\.faces\.ViewState').attr('value'),
        }
        return do_request(url, method='post', data=data)

    # get first page
    doc = do_request(url)
    num_pages = int(re.search(r'(\d+)$', doc('.pagerDeluxe_text').text()).groups()[0])
    logger.info('paginating', url=url, num_pages=num_pages)

    # prepare data for pagination
    pagination_form = doc('form')
    prefix = pagination_form.attr('id')
    url = DZ_RS_URL + pagination_form.attr('action')
    request_page = partial(request_page, prefix, url)

    # get the 2nd and the rest of the pages using pagination
    return toolz.concatv([doc], map(request_page, range(2, num_pages + 1)))
