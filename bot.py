""" usage: mediawiki-matrix-bot CONFIG

"""
import asyncio
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

def format_data(obj):
    print(obj)
    typ = obj['type']
    if  typ == "log":
        title = f"Special:Log/{obj['log_type'].capitalize()}"
        url = ""
        flag = obj['log_action']
        comment = obj['log_action_comment']
    else:
        title = obj['title']
        comment = obj['comment']
        flag = ""
        if obj['patrolled']:
            flag += '!'

        if typ == "new":
            query = f"?oldid={obj['revision']['new']}&rc_id={obj['id']}"
            flag += "N"
        else:
            query = f"?diff={obj['revision']['new']}&oldid={obj['revision']['old']}"

        if obj['minor']:
            flag += "M"

        if obj['bot']:
            flag += "B"

        url = f"{obj['server_url']}{obj['server_script_path']}/index.php{query}"

    old_length = obj.get('length',{}).get('old',None)
    new_length = obj.get('length',{}).get('new',None)
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


class RCForwarder:
    matrix_client = None
    def __init__(self,matrix_client,room):
        print("init rcforwarder")
        super().__init__()
        self.matrix_client = matrix_client
        self.room = room

    def connection_made(self, transport):
        print(f"connection made from {transport}")
        self.transport = transport

    def datagram_received(self, data, addr):
        print("Data received")
        data = data.decode().strip()

        for line in data.split("\n"):
            try:
                obj = json.loads(line)
                print(obj)
                asyncio.create_task(
                    self.forward_news(self.matrix_client,self.room,obj)
                )
                self.transport.sendto("ok".encode(), addr)
            except Exception as e:
                print(e)
                self.transport.sendto("not ok".encode(), addr)

    def connection_lost(self,transport):
        pass


    async def forward_news(self,client, room, message_obj):
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

async def check_recent_changes(client):
    while True:
        print("check recent changes")
        print(client)
        await asyncio.sleep(10)
        await forward_news(

async def main():
    args = docopt(__doc__)
    #Load config
    config = args['CONFIG']

    with open(config) as config_file:
        config = json.load(config_file)

    #loop = asyncio.get_running_loop()

    #Login
    print("login")
    client = AsyncClient(config["server"], config["mxid"])
    print(await client.login(config["password"]))
    #loop.run_until_complete(server)
    print("create listener")
    #transport, protocol = await loop.create_datagram_endpoint(
    #    lambda: RCForwarder(client,config["room"]),
    #    local_addr=('0.0.0.0', 5006))

    #server.matrix_client = client
    #loop.run_forever()
    #while True:
    #    await asyncio.sleep(1)
    asyncio.create_task(check_recent_changes(client))

    await client.sync_forever(timeout=30000)






#asyncio.get_event_loop().run_until_complete(main())
asyncio.run(main())

