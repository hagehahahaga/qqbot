from abstract.bases.importer import time, requests

from abstract.bot import BOT
from abstract.apis.table import GROUP_OPTION_TABLE
from abstract.message import *
from abstract.bases.exceptions import *

from extra.MaimaiDXStatus import MAIMAIDX_STATUS_SERVICE


@BOT.register_service('maimai_status_auto_notice', 20, True)
def maimai_status_auto_notice():
    try:
        result = MAIMAIDX_STATUS_SERVICE.update_status()
    except requests.exceptions.ConnectionError, requests.exceptions.JSONDecodeError:
        LOG.WAR('status.awmc.cc is now unavailable.')
        time.sleep(60)
        return

    text = '\n'.join(
        f'{name}好像{status}超过三分钟了.' for name, status in result.items()
    )
    if not text:
        return

    for group_id, city in GROUP_OPTION_TABLE.get_all('where maimai_notice = 1', attr="id, city"):
        try:
            GroupMessage(text, Group(int(group_id))).send()
        except GroupNotJoined:
            GROUP_OPTION_TABLE.set('id', group_id, 'maimai_notice', 0)
            LOG.WAR(f'Group {group_id} not joined, option maimai_notice set to 0.')

        except SendFailure as e:
            LOG.WAR(e)
        except Exception as e:
            LOG.ERR(e)
