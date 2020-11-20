#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.node import OVSController
from mininet.cli import CLI
import time
import os

#
#           h2      h4       h6
#           |       |        |
#           |       |        |
#           |       |        |
#   h1 ---- S1 ---- S2 ----- S3 ---- h8
#           |   0ms |   5ms  |
#           |       |        |
#           |       |        |
#           h3      h5       h7
#
#

class ParkingLotTopo( Topo ):
    "Three switches connected to hosts. n is number of hosts connected to switch 1 and 3"
    def build( self, settings, n=3 ):
        switch1 = self.addSwitch('s1')
        switch2 = self.addSwitch('s2')
        switch3 = self.addSwitch('s3')

        # Setting the bottleneck link parameters (htb -> Hierarchical token bucket rate limiting)
        self.addLink( switch1, switch2, 
            bw=settings['myBandwidth'], 
            delay=settings['myDelay'], 
            loss=settings['myLossPercentage'], 
            use_htb=True,
            max_queue_size=settings['myQueueSize'],
            )
        self.addLink( switch2, switch3, 
            bw=settings['myBandwidth'], 
            delay=settings['myDelay'], 
            loss=settings['myLossPercentage'], 
            use_htb=True,
            max_queue_size=settings['myQueueSize'], 
            )
        for h in range(3*n - 1):
            host = self.addHost('h%s' % (h + 1))
            if h < n:
                self.addLink(host, switch1) # one host to switch 1 (h1, h2, h3)
            elif h < 2*n - 1:
                self.addLink(host, switch2) # n hosts to switch 2 (h4, h5)
            else:
                self.addLink(host, switch3) # n hosts to switch 3 (h6, h7, h8)


def perfTest():
    queueSizes = [1] + list(range(50, 550, 50))
    cong_types = ["cubic", "bbr"]
    for queueSize in queueSizes:
        settings = {
            'myBandwidth': 50,
            'myDelay': '10ms',
            'myQueueSize': queueSize,
            'myLossPercentage': 0
        }
        "Create network and run simple performance test"
        topo = ParkingLotTopo(settings=settings, n=3)
        net = Mininet( topo=topo,
                       host=CPULimitedHost, link=TCLink, controller = OVSController)
        net.start()
        print("Dumping host connections")
        dumpNodeConnections( net.hosts )
        print("Testing network connectivity")
        net.pingAll()
        
        h1, h2, h3, h4, h5, h6, h7, h8 = net.get('h1','h2','h3','h4','h5','h6','h7','h8')
        
        h6.cmd('iperf3 -s -i 1 > 4/s3/h6_client_%s &' % (queueSize))
        h7.cmd('iperf3 -s -i 1 > 4/s3/h7_client_%s &' % (queueSize))
        h1.cmd('iperf3 -c 10.0.0.6 -t 110 -C %s > 4/s3/h1_h6_server_%s_%s &' % ('cubic', 'cubic', queueSize))
        time.sleep(10)
        h1.cmd('iperf3 -c 10.0.0.7 -t 100 -C %s > 4/s3/h1_h7_server_%s_%s &' % ('bbr', 'bbr', queueSize))
        h3.cmd('ping 10.0.0.8 > 4/s3/h3_h8_ping_%s &' % (queueSize))
        time.sleep(120)
        net.stop() # exit mininet

if __name__ == '__main__':
    os.system("sudo mn -c")
    os.system("killall /usr/bin/ovs-testcontroller")
    setLogLevel( 'info' )
    print("\n\n\n ------Start Mininet ----- \n\n")
    perfTest()
    print("\n\n\n ------End Mininet ----- \n\n")


