""" usage: mediawiki-matrix-bot CONFIG

"""
import asyncio
import aiohttp
import aiofiles as aiof
from typing import Any, Dict, Iterator, Awaitable
from io import StringIO
from html.parser import HTMLParser
from contextlib import contextmanager

from docopt import docopt
from nio import AsyncClient
import aiohttp

import json
import feedparser
import sys

import logging

log = logging.getLogger("bot")
logging.basicConfig(level=logging.INFO)


class MLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d: str) -> None:
        self.text.write(d)

    def get_data(self) -> str:
        return self.text.getvalue()


def strip_tags(html: str) -> str:
    s = MLStripper()
    s.feed(html)
    return s.get_data()


@contextmanager
def die_on_exception(context: str) -> Iterator[None]:
    try:
        yield
    except Exception as e:
        log.error(f"{context}:")
        log.error(e)
        sys.exit(1)


# from the original source: https://github.com/wikimedia/mediawiki/blob/master/includes/rcfeed/IRCColourfulRCFeedFormatter.php
## see http://www.irssi.org/documentation/formats for some colour codes. prefix is \003,
## no colour (\003) switches back to the term default
# $titleString = "\00314[[\00307$title\00314]]";
# $fullString = "$titleString\0034 $flag\00310 " .
# 	"\00302$url\003 \0035*\003 \00303$user\003 \0035*\003 $szdiff \00310$comment\003\n";


def color(text: str, color: str) -> str:
    return f'<font color="{color}">{text}</font>'


def bold(text: str) -> str:
    return f"<b>{text}</b>"


def format_data(obj: Dict[str, Any], baseurl: str, udpinput: bool = False) -> str:
    """udpinput: set to True if the input arrived via UDP and not via HTTP"""
    log.debug(obj)
    typ = obj["type"]
    if udpinput:
        newrev = obj["revision"]["new"]
        oldrev = obj["revision"]["old"]
        ident = obj["id"]
        old_length = obj.get("length", {}).get("old", None)
        new_length = obj.get("length", {}).get("new", None)
        is_patrolled = obj["patrolled"]
        is_bot = obj["bot"]
        is_minor = obj["minor"]
        log_type = obj.get("log_type", None)
        log_action = obj.get("log_action", None)
        baseurl = f"{obj['server_url']}{obj['server_script_path']}"
        log_action_comment = obj.get("log_action_comment", "")

    else:
        newrev = obj["revid"]
        oldrev = obj["old_revid"]
        ident = obj["rcid"]
        old_length = obj.get("oldlen", None)
        new_length = obj.get("newlen", None)
        is_patrolled = False  # does not work with http (need elevated permissions)
        is_bot = hasattr(obj, "bot")  # do not know if this even works
        is_minor = hasattr(obj, "minor")
        log_type = obj.get("logtype", None)
        log_action = obj.get("logaction", None)
        log_action_comment = obj["comment"]
        baseurl = f"{baseurl}/wiki"

        #  'logtype': 'move', 'logaction': 'move', 'logparams': {'target_ns': 0, 'target_title': 'Sandbox', 'suppressredirect': ''}},

    if typ == "log":
        title = f"Special:Log/{log_type.capitalize()}"
        url = ""
        flag = log_action
        comment = log_action_comment
    else:
        title = obj["title"]
        comment = obj["comment"]
        flag = ""
        if is_patrolled:
            flag += "!"
        if typ == "new":
            query = f"?oldid={newrev}&rc_id={ident}"
            flag += "N"
        else:
            query = f"?diff={newrev}&oldid={oldrev}"

        if is_minor:
            flag += "M"

        if is_bot:
            flag += "B"

        url = f"{baseurl}/index.php{query}"

    if old_length is not None and new_length is not None:
        diff_length = new_length - old_length
        if diff_length < -500:
            diff_length = bold(diff_length)  # make large removes bold
        elif diff_length > 0:
            diff_length = f"+{diff_length}"  # add plus sign to additions
        diff_length = f"({diff_length})"
    else:
        diff_length = ""  # otherwise do not add the

    user = obj["user"]

    return (
        color("[[", "#7F7F7F")
        + bold(color(title, "#FC7F00"))
        + color("]]", "#7F7F7F")
        + " "
        + color(flag, "#FF0000")
        + f" {url} {color('*','#7F0000')}"
        + f" {color(user,'#009300')} {color('*','#7F0000')}"
        + f" {bold(diff_length)} {color(comment,'#009393')}"
    )


async def forward_news(
    client: AsyncClient, room: str, message_obj: Dict[str, Any], baseurl: str
) -> None:
    if not client:
        raise Exception("matrix_client must be set")
    html_message = format_data(message_obj, baseurl)
    log.info(f"Sending message to {room}: {html_message}")
    await client.room_send(
        room,
        message_type="m.room.message",
        content={
            # fallback for clients not supporting html
            "body": strip_tags(html_message),
            "format": "org.matrix.custom.html",
            "formatted_body": html_message,
            "msgtype": "m.notice",
        },
    )


async def fetch_changes(baseurl: str, api_path: str = "/api.php") -> Any:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{baseurl}{api_path}?action=query&list=recentchanges&format=json&rcprop=user|comment|flags|title|sizes|loginfo|ids|revision"
        ) as response:
            return await response.json()


async def check_recent_changes(
        client: AsyncClient, room: str, baseurl: str, api_path: str, timeout: int
) -> None:
    # initial fetch of the last recent change, there is no state handling here,
    # we do not re-notify changes in case the bot is offline
    log.info("Fetching last changes initially")
    with die_on_exception("Something went wrong when fetching the the first change from the wiki"):
        resp = await fetch_changes(baseurl, api_path)
    last_rc = resp["query"]["recentchanges"][0]["rcid"]

    log.info(f"The last rc is {last_rc}")

    while True:
        log.info("check recent changes")
        with die_on_exception("Something went wrong when fetching the latest changes from the wiki"):
            resp = await fetch_changes(baseurl, api_path)
        rcs = resp["query"]["recentchanges"]
        new_rcs = list(filter(lambda x: x["rcid"] > last_rc, rcs))

        if not new_rcs:
            log.info("no new changes")

        for rc in new_rcs:
            with die_on_exception("Something went wrong when forwarding the news"):
                await forward_news(client, room, rc, baseurl)

        last_rc = rcs[0]["rcid"]  # update last rc
        log.info(f"sleeping for {timeout}")
        await asyncio.sleep(timeout)


async def main() -> None:
    args = docopt(__doc__)
    # Load config
    config = args["CONFIG"]

    with open(config) as config_file:
        config = json.load(config_file)

    # Login
    log.info(f'login to server {config["server"]} as {config["mxid"]}')
    client = AsyncClient(config["server"], config["mxid"])
    log.info(await client.login(config["password"]))
    log.info("create listener")

    asyncio.create_task(
        check_recent_changes(
            client, config["room"], config["baseurl"], config.get("api_path","/api.php"), config.get("timeout", 60)
        )
    )
    with die_on_exception("Something went wrong when sycing with matrix server"):
        await client.sync_forever(timeout=30000)

# asyncio.get_event_loop().run_until_complete(main())
sys.exit(asyncio.run(main()))
