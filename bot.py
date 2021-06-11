""" usage: mediawiki-matrix-bot CONFIG

"""
import asyncio
import aiohttp
import aiofiles as aiof

from docopt import docopt
from nio import AsyncClient
import aiohttp

from pprint import pprint
import json
import feedparser
# from the original source: https://github.com/wikimedia/mediawiki/blob/master/includes/rcfeed/IRCColourfulRCFeedFormatter.php
		## see http://www.irssi.org/documentation/formats for some colour codes. prefix is \003,
		## no colour (\003) switches back to the term default

# $titleString = "\00314[[\00307$title\00314]]";
		#$fullString = "$titleString\0034 $flag\00310 " .
		#	"\00302$url\003 \0035*\003 \00303$user\003 \0035*\003 $szdiff \00310$comment\003\n";
#' Send a single feed item in one room in the RSS bot format

def color(text,color):
    return f"<font color={color}>{text}</font>"

def bold(text):
    return f"<b>{text}</b>"

def format_data(obj,udpinput=False):
    """ udpinput: set to True if the input arrived via UDP and not via HTTP
    """
    print(obj)
    typ = obj['type']
    if udpinput:
        newrev = obj['revision']['new']
        oldrev = obj['revision']['old']
        ident = obj['id']
        old_length = obj.get('length',{}).get('old',None)
        new_length = obj.get('length',{}).get('new',None)
        is_patrolled = obj['patrolled']
        is_bot = obj['bot']
    else:
        newrev = obj['revid']
        oldrev = obj['old_revid']
        ident = obj['rcid']
        old_length = obj.get('oldlen',None)
        new_length = obj.get('newlen',None)
        is_patrolled = False # does not work with http (need elevated permissions)
        is_bot = False # does not provide the info

    if  typ == "log":
        title = f"Special:Log/{obj['log_type'].capitalize()}"
        url = ""
        flag = obj['log_action']
        comment = obj['log_action_comment']
    else:
        title = obj['title']
        comment = obj['comment']
        flag = ""
        if is_patrolled:
            flag += '!'
        if typ == "new":
            query = f"?oldid={newrev}&rc_id={ident}"
            flag += "N"
        else:
            query = f"?diff={newrev}&oldid={oldrev}"

        if obj['minor']:
            flag += "M"

        if is_bot:
            flag += "B"

        url = f"{obj['server_url']}{obj['server_script_path']}/index.php{query}"

    if old_length is not None and new_length is not None:
        diff_length = new_length - old_length
        if diff_length < -500:
            diff_length = bold(diff_length) # make large removes bold
        else:
            diff_length = f"+{diff_length}" # add plus sign to additions
        diff_length = f"({diff_length})"
    else:
        diff_length = "" # otherwise do not add the

    user = obj['user']


    return  color('[[','gray') + bold(color(title,'yellow')) + color(']]','gray')  + \
         " " + color(flag,'red') + \
        f" <a href={url}>{url}</a> {color('*','red')}"  + \
        f" {color(user,'lightgreen')} {color('*','red')}" + \
        f" {bold(diff_length)} {color(comment,'cyan')}"


async def forward_news(client, room, message_obj):
    if not client:
        raise Exception("matrix_client must be set")
    html_message = format_data(message_obj)
    print(html_message)
    await client.room_send(
        room,
        message_type="m.room.message",
        content={
            "body": "message",
            "format": "org.matrix.custom.html",
            "formatted_body":html_message,
            "msgtype": "m.notice",
            }
        )

async def read_state(statepath = "state.json" ) -> dict:
    try:
        async with aiof.open(statepath, 'r+') as f:
            return json.loads( await f.read()) # contains 'seen': [ seen_id1, seen_id2]
    except:
        print(f"Cannot load contents of {statepath} as json object, falling back to empty")
        return { "seen": [] } # we start with an empty object

async def write_state(state,statepath = "state.json"):
    async with aiof.open(statepath, 'w+') as f:
        await f.write( json.dumps(state))


async def fetch_changes():
    async with aiohttp.ClientSession() as session:
        #|patrolled
        async with session.get('https://nixos.wiki/api.php?action=query&list=recentchanges&format=json&rcprop=user|comment|flags|title|sizes|loginfo|ids|revision') as response:
            return await response.json()

def get_new_rcs(rcs,state):
    for rc in rcs:
        if rc['rcid'] not in state['seen']:
            yield rc

async def check_recent_changes(client,room):
    while True:
        print("check recent changes")
        resp = await fetch_changes()
        rcs = resp['query']['recentchanges']
        print(rcs)
        state = await read_state()
        new_rcs = get_new_rcs(rcs,state)
        for rc in new_rcs:
            await forward_news(client,room,rc)
        await asyncio.sleep(10)

async def main():
    args = docopt(__doc__)
    #Load config
    config = args['CONFIG']

    with open(config) as config_file:
        config = json.load(config_file)

    #Login
    print("login")
    client = AsyncClient(config["server"], config["mxid"])
    print(await client.login(config["password"]))
    print("create listener")

    #transport, protocol = await loop.create_datagram_endpoint(
    #    lambda: RCForwarder(client,config["room"]),
    #    local_addr=('0.0.0.0', 5006))

    # with that we run check_recent_changes and sync_forever in parallel
    asyncio.create_task(check_recent_changes(client,config['room']))
    await client.sync_forever(timeout=30000)






#asyncio.get_event_loop().run_until_complete(main())
asyncio.run(main())

