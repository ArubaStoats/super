import asyncio
import aiohttp
import ujson
from discord.ext import commands
from datetime import datetime
import time

from super import settings, utils
from super.utils import R

class np:
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
    
    def __exit__(self):
        self.session.close()

    def _lastfm_response_to_song(self, response):
        song = dict(is_playing=False)
        try:
            track = response['recenttracks']['track'][0]
            song['artist'] = track['artist']['#text']
            song['album'] = track['album']['#text'] or None
            song['name'] = track['name']

            if '@attr' in track and 'nowplaying' in track['@attr']:
                song['is_playing'] = True
        except (KeyError, IndexError):
            song = dict(is_playing=True, artist=None, album=None, name=None)

        return song

    def _lastfm_song_to_str(self, lfm, nick, song):
        nick = f'({nick})' if nick else ''
        return ' '.join([
            f'**{lfm}**{nick}',
            f"now playing: **{song['artist']} - {song['name']}**",
            f"from **{song['album']}**" if song['album'] else '',
        ])

    async def lastfm(self, lfm=None, ctx=None, member=None, nick=None):
        if not lfm:
            lfm, nick = await self._userid_to_lastfm(ctx, member)
        if not lfm:
            return

        url = 'https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks'
        params = dict(format='json', limit=1, user=lfm, api_key=settings.SUPER_LASTFM_API_KEY)

        async with self.session.get(url, params=params) as response:
            response = ujson.loads(await response.read())
        song = self._lastfm_response_to_song(response)
        return {
            'song': song,
            'formatted': self._lastfm_song_to_str(lfm, nick, song),
        }

    async def _userid_to_lastfm(self, ctx, member):
        lfm = await R.read(R.get_slug(ctx, 'np', id=member.id))
        return [lfm, member.display_name]

    @commands.command(no_pm=True, pass_context=True)
    async def np(self, ctx):
        """Get now playing song from last.fm"""
        utils.send_typing(self, ctx.message.channel)
        words = ctx.message.content.split(' ')
        slug = R.get_slug(ctx, 'np')
        try:
            lfm = words[1]
            await R.write(slug, lfm)
        except IndexError:
            lfm = await R.read(slug)

        if not lfm:
            await self.bot.say(f'Set an username first, e.g.: **{settings.SUPER_PREFIX}np joe**')
            return
        lastfm_data = await self.lastfm(lfm=lfm)
        await self.bot.say(lastfm_data['formatted'])

    @commands.command(no_pm=True, pass_context=True, name='wp')
    async def wp(self, ctx):
        """Get now playing song from last.fm, for the whole server"""
        utils.send_typing(self, ctx.message.channel)
        message = ['Users playing music in this server:']
        tasks = []
        for member in ctx.message.server.members:
            tasks.append(self.lastfm(ctx=ctx, member=member))

        tasks = tasks[::-1]  ## Theory: this will make it ordered by join date

        for data in await asyncio.gather(*tasks):
            if data and data['song']['is_playing']:
                message.append(data['formatted'])
        if len(message) == 1:
            message.append('Nobody. :disappointed:')
        await self.bot.say('\n'.join(message))


def setup(bot):
    bot.add_cog(np(bot))
