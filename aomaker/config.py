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


if __name__ == '__main__':
    s = ['paris','join','addjob']
    for i in s:
        if 'job' in i:
            print('sssssss')