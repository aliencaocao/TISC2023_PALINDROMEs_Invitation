import nextcord
from nextcord.ext import application_checks, commands

intents = nextcord.Intents.default()
intents.message_content = True
bot = commands.Bot(intents=intents)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    for server in bot.guilds:
        for channel in server.text_channels:
            print(channel)
            if channel.name == 'meeting-records':
                async for thread in channel.archived_threads():
                    print(thread.name)
                    async for msg in thread.history():
                        print(msg.content)
        async for log in server.audit_logs():
            if log.action == nextcord.AuditLogAction.invite_create and log.changes.after.channel.name == 'flag':
                print(log.target, log.changes)
                # choose the one that only appeared once because those that appeared twice means it was created then deleted. This might be a nextcord bug though, as it is supposed to reflect as a 'invite deleted' event. Nonetheless, it doesn't take long to just try all of them.


bot.run('MTEyNTk4MjE2NjM3MTc5NDk5NQ.G343Lq.kLfsWpQ_ositx9LOKTeS_LF6WecgRD5Vy0MIxs')  # get this from password checking website
