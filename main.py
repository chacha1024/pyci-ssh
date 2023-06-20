import asyncio
import os
import sys
import time

import aiosocks
import asyncssh


class SocksClientConnection:
    def __init__(self, proxy):
        user_pass, host_port = proxy.split('@')
        self.username, self.password = user_pass.split(':')
        self.host, self.port = host_port.split(':')

    async def create_connection(self, session_factory, host, port):
        socks5_addr = aiosocks.Socks5Addr(self.host, int(self.port))
        socks5_auth = aiosocks.Socks5Auth(self.username, self.password)
        return await aiosocks.create_connection(
            session_factory, proxy=socks5_addr, proxy_auth=socks5_auth, dst=(host, port)
        )


async def run_ssh(script, host, port, username, password=None, private_key=None, proxy=None) -> None:
    try:
        client_keys = [asyncssh.import_private_key(private_key)] if private_key else []
        time_start = time.monotonic()
        tunnel = SocksClientConnection(proxy) if proxy else ()
        async with asyncssh.connect(
                host,
                port=int(port),
                tunnel=tunnel,
                username=username,
                password=password,
                known_hosts=None,
                client_keys=client_keys
        ) as conn:
            cmds = script.split('\n')
            print(f'{host}: Starting run {len(cmds)} commands..')
            for cmd in cmds:
                print(f'start run: {cmd}')
                result = await conn.run(f'{cmd}')
                print(f'finish! result: {result.stdout}')
            print(f'{host}: run {len(cmds)} commands ok! cost: {time.monotonic() - time_start:.2f} s')
    except Exception as e:
        print(f'{host}: ERROR! {e} {type(e)}')


async def run(script, host_raw, username, password=None, private_key=None, proxy=None):
    tasks = []
    if not any((password, private_key)):
        raise ValueError('password and private_key must have one')
    host_raw_list = []
    if ',' in host_raw:
        host_raw_list = host_raw.split(',')
    else:
        host_raw_list.append(host_raw)
    for raw in host_raw_list:
        host, port = raw.split(':')
        print(f'SSHing: {host}:{port}')
        tasks.append(run_ssh(script, host, port, username, password, private_key, proxy))
    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == '__main__':
    try:
        host_raw = os.environ.get('INPUT_HOST')
        username = os.environ.get('INPUT_USERNAME')
        password = os.environ.get('INPUT_PASSWORD')
        private_key = os.environ.get('INPUT_KEY')
        proxy = os.environ.get('INPUT_PROXY')
        script = os.environ.get('INPUT_SCRIPT')
        asyncio.run(run(script, host_raw, username, password, private_key, proxy))
    except (OSError, asyncssh.Error) as exc:
        sys.exit(f'SSH connection failed: ' + str(exc))
