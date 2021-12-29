API = {
    'Volume': 'Volume',
    'Instance': 'Instance',
    'Nic': 'Nic',
    'Vxnet': 'Vxnet',
    'Route': 'Route',
    'Eip': 'Eip',
    'SecurityGroup': 'SecurityGroup',
    'KeyPair': 'KeyPair',
    'NFV': 'NFV',
    'Balancer': 'Balancer',
    'Alarm': 'Alarm',
    'Snapshot': 'Snapshot',
    'DNSAlia': 'DNSAlia',
    'Tag': 'Tag',
    'Common': ['DescribeZone','DescribeJobs','UserData'],
    'S2': 'S2',
    'Notification': 'Notification',
    'Span': 'Span',
    'SubUser': 'SubUser',
    'Balance': ['Balance', 'Charge','Lease'],
    'Wan': 'Wan',
    'Border': 'Border',
    'Quota': 'Quota',
    'ResourceGroup': ['ResourceGroup','UserGroup','GroupRole'],
    'Summary': 'Summary'
}

EXCLUDE_HEADER = [
            'User-Agent',
            'Origin',
            'Referer',
            'Accept-Encoding',
            'Accept-Language',
            'Proxy-Connection',
            'Content-Length',
            'Connection',
            'Cache-Control',
            'Pragma',
            'sec-ch-ua-mobile',
            'sec-ch-ua-platform',
            'Sec-Fetch-Site',
            'Sec-Fetch-Mode',
            'Sec-Fetch-Dest',
            'sec-ch-ua'
        ]

EXCLUDE_SUFFIX = ['.js', '.css', '.woff', '.woff2', '.png', '.svg', '.ico', '.vue', '.jpeg']