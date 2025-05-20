import json
from pyvis.network import Network
import networkx as nx
import os
from prot import read_proto_file
from te.service.cm.v1 import cm_snapshot_pb2 as cm
import argparse

from utils.arn_utils import extract_account_region_from_arn, reconstruct_arn
from constants import *

TGW_URL = "images/tgw.svg"
def read_json_file(file_path):
    """
    Read a JSON file and return the parsed data.
    """
    with open(file_path, "r") as f:
        data = json.load(f)
    return data

def get_files(directory, extension=".pb"):
    """
    Discover all .json files in a specific directory and return their paths.
    """
    file_paths = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(extension):
                file_path = os.path.join(root, file)
                file_paths.append(file_path)
    return file_paths


class AwsTopology:
    def __init__(self):
        self.network = nx.Graph()

    def __init__(self, network=None):
        if network is None:
            self.network = nx.Graph()
        else:
            self.network = network.copy()

    def add_transit_gateway(self, tgw_id, name=None):
        """ 
        Add a transit gateway to the network.
        """
        if tgw_id in self.network.nodes and name is None:
            return
        
        self.network.add_node(tgw_id, label="TGW", title=f"{tgw_id}\n{name}", name=name, image=TGW_URL, shape="image", resource_type="tgw", level=1, size=TRANSIT_GATEAWAY_NODE_SIZE)

    def add_vpc(self, vpc_arn, name=None):
        """ 
        Add a VPC to the network with data account and region.
        """
        vpc_id = vpc_arn.replace("garn:", "arn:").lower()
        # vpc_id = self.arn_group_by_account_region(vpc_id)
        if vpc_id in self.network.nodes and name is None:
            return
        account_id, region_id = extract_account_region_from_arn(vpc_arn)
        
        self.network.add_node(vpc_id, label="VPC",resource_type="vpc", title=f"{vpc_id}\n{name}", image="images/vpc.svg", shape="image", level=2, size=VPC_NODE_SIZE)
        if account_id and region_id:
            self.network.nodes[vpc_id]['account'] = account_id
            self.network.nodes[vpc_id]['region'] = region_id
    
    def add_vpn_gateway(self, arn, name=None):
        """ 
        Add a VPN gateway to the network.
        """
        vpn_id = arn.replace("garn:", "arn:").lower()
        account_id, region_id = extract_account_region_from_arn(vpn_id)
        self.network.add_node(vpn_id, label="VPN", resource_type="vpn-gateway", title=vpn_id, image="images/vpn-gateway.svg", shape="image", level=3, size=VPN_NODE_SIZE)
        if account_id and region_id:
            self.network.nodes[vpn_id]['account'] = account_id
            self.network.nodes[vpn_id]['region'] = region_id
        
    def add_vpn_connection(self, arn):
        """ 
        Add a VPN connection to the network.
        """
        vpn_id = arn.replace("garn:", "arn:").lower()
        account_id, region_id = extract_account_region_from_arn(vpn_id)
        self.network.add_node(vpn_id, label="VPN", resource_type="vpn-connection", title=vpn_id, image="images/vpn-connection.svg", shape="image", level=3, size=VPN_NODE_SIZE)
        if account_id and region_id:
            self.network.nodes[vpn_id]['account'] = account_id
            self.network.nodes[vpn_id]['region'] = region_id

    def add_direct_connect_gateway(self, arn, name=None):
        """ 
        Add a Direct Connect gateway to the network.
        """
        if arn in self.network.nodes and name is None:
            return
        dcg_id = arn.replace("garn:", "arn:").lower()
        account_id, region_id = extract_account_region_from_arn(dcg_id)
        self.network.add_node(dcg_id, label="DCG", resource_type="direct-connect-gateway", title=dcg_id, image="images/direct-connect-gateway.svg", shape="image", level=0, size=DIRECT_CONNECT_NODE_SIZE)
        if account_id and region_id:
            self.network.nodes[dcg_id]['account'] = account_id
            self.network.nodes[dcg_id]['region'] = region_id

    def add_direct_connect_connection(self, arn, name=None):
        """ 
        Add a Direct Connect connection to the network.
        """
        dc_id = arn.replace("garn:", "arn:").lower()
        account_id, region_id = extract_account_region_from_arn(dc_id)
        self.network.add_node(dc_id, label="DC", resource_type="direct-connect-connection", title=f"{dc_id}\n{name}", image="images/direct-connect-connection.svg", shape="image", level=0, size=DIRECT_CONNECT_NODE_SIZE)
        if account_id and region_id:
            self.network.nodes[dc_id]['resource_type'] = "direct-connect-connection"
            self.network.nodes[dc_id]['account'] = account_id
            self.network.nodes[dc_id]['region'] = region_id

    def add_vpc_peering(self, vpc_id, peer_vpc_id, connection_id):
        """ 
        Add a VPC peering connection to the network.
        """
        vpc_id = vpc_id.replace("garn:", "arn:").lower()
        peer_vpc_id = peer_vpc_id.replace("garn:", "arn:").lower()
        self.add_vpc(vpc_id)
        self.add_vpc(peer_vpc_id)
        self.network.add_edge(vpc_id, peer_vpc_id, color="green", title=connection_id, weight=VPC_PEER_WIDTH)


    def add_vpn_gateway_connection(self, node_id, vpc_id):
        """
        Add a VPN gateway to the network.
        """
        node_id = node_id.replace("garn:", "arn:").lower()
        vpc_id = vpc_id.replace("garn:", "arn:").lower()
        self.add_vpn_gateway(node_id)
        self.add_vpc(vpc_id)
        self.network.add_edge(node_id, vpc_id, color="black",weight=VPC_VPN_EDGE_WIDTH)

    def add_direct_connect_virtual_interface(self, dcvif):
        if not self.network.has_node(dcvif.connectionId):
            self.add_direct_connect_connection(dcvif.connectionId)
        if dcvif.virtualGatewayId:    
            vgw_arn = reconstruct_arn('ec2', dcvif.accountId, dcvif.region, 'vpn-gateway', dcvif.virtualGatewayId)
            self.add_vpn_gateway(vgw_arn)
            self.network.add_edge(dcvif.connectionId, vgw_arn, color="blue", title=dcvif.assetId)
        elif dcvif.directConnectGatewayId:
            self.network.add_edge(dcvif.connectionId, dcvif.directConnectGatewayId, color="blue", title=dcvif.assetId, weight=DIRECT_CONNECT_CONNECTION_GATEWAY_WIDTH)
        else:
            print(f"Unknown virtual interface type: {dcvif.virtualInterfaceType}")

    def get_min_size_connected_componnents_subgraph(self, min_size=2):
        """
        Get the subgraph of connected components with a minimum size.
        """
        connected_components = list(nx.connected_components(self.network))
        filtered_nodes =  [node for component in connected_components if len(component) >= min_size for node in component]
        subgraph = self.network.subgraph(filtered_nodes)
        return subgraph

    def show(self, output_file="example.html", min_size_connected_components=10):
        """
        Display the network.
        """
        
        # displaygraph = Network(notebook=True, cdn_resources="remote", height="1440px", width="100%",select_menu=True, filter_menu=True)
        # #displaygraph.from_nx(self.network)
        # #displaygraph.force_atlas_2based()
        # displaygraph.from_nx(self.get_acount_region_groupped_graph())
        
        # displaygraph.toggle_physics(True)
        # #displaygraph.show_buttons(filter_=['layout'])

        # displaygraph.show("example_groupped.html")
        graph = self.get_min_size_connected_componnents_subgraph(min_size_connected_components)
        pyvis_graph = Network(notebook=True, cdn_resources="remote", height="1440px", width="100%",select_menu=True, filter_menu=True)
        pyvis_graph.from_nx(graph)
        pyvis_graph.toggle_physics(True)
        pyvis_graph.force_atlas_2based()
        pyvis_graph.show(output_file)



    def add_tgw_attachment(self, transit_gateway_attachment):
        """
        Add a TGW attachment to the network.
        """
        tgw_id = transit_gateway_attachment.tgwArn.replace("garn:", "arn:").lower()
        self.add_transit_gateway(tgw_id)

        node_id = transit_gateway_attachment.resourceArn.replace("garn:", "arn:").lower()
        resource_types = cm.TgwAttachmentResourceType
        weight = 1
        match transit_gateway_attachment.resourceType:
            case resource_types.TGW_RESOURCE_TYPE_VPC:
                self.add_vpc(node_id)
                weight=TGW_VPC_ATTCH_WIDTH
            case resource_types.TGW_RESOURCE_TYPE_VPN:
                self.add_vpn_connection(node_id)
                weight=TGW_VPN_ATTACH_WIDTH
            case resource_types.TGW_RESOURCE_TYPE_DIRECT_CONNECT_GATEWAY:
                node_id = transit_gateway_attachment.resourceId.lower()
                self.add_direct_connect_gateway(node_id)
                weight=TGW_DIRECT_CONNECT_WIDTH

            case _:
                print(f"Unknown resource type: {transit_gateway_attachment.resourceType}")
            
        attachment_id = transit_gateway_attachment.transitGatewayAttachmentId.replace("garn:", "arn:").lower()
        self.network.add_edge(node_id, tgw_id,title=attachment_id, color='black', weight=weight)
    
    def add_tgw_peering(self, tgw_id, peer_tgw_id, attachment_id):
        """
        Add a TGW peering connection to the network.
        """
        tgw_id = tgw_id.replace("garn:", "arn:").lower()
        peer_tgw_id = peer_tgw_id.replace("garn:", "arn:").lower()
        self.add_transit_gateway(tgw_id)
        self.add_transit_gateway(peer_tgw_id)
        self.network.add_edge(tgw_id, peer_tgw_id, color="red", title=attachment_id, weight=TRANSIT_GATEWAY_PEER_WIDTH)

    def get_acount_region_groupped_graph(self):
        """
        Get the account-region grouped graph.
        """
        new_graph = nx.Graph()
        for node in self.network.nodes(data=True):
            node_id, data = node
            if data['resource_type'] == "vpc":
                account_id = data['account']
                region_id = data['region']
                new_node_id = f"{account_id}:{region_id}"
                if not new_graph.has_node(new_node_id):
                    new_graph.add_node(new_node_id, label="VPC", title=new_node_id, image="images/vpc.svg", shape="image")
                    new_graph.nodes[new_node_id]['resource_type'] = "vpc"
                    new_graph.nodes[new_node_id]['vpcs'] = [node_id]
                else:
                    new_graph.nodes[new_node_id]['vpcs'].append(node_id)
            else:
                new_graph.add_node(node_id, **data)
        for edge in self.network.edges(data=True):
            node1, node2, data = edge
            if self.network.nodes[node1]['resource_type'] == "vpc":
                account_id = self.network.nodes[node1]['account']
                region_id = self.network.nodes[node1]['region']
                node1 = f"{account_id}:{region_id}"
            if self.network.nodes[node2]['resource_type'] == "vpc":
                account_id = self.network.nodes[node2]['account']
                region_id = self.network.nodes[node2]['region']
                node2 = f"{account_id}:{region_id}"
            # if node1 != node2:
            new_graph.add_edge(node1, node2, **data)
        return new_graph


def create_graph(dir_path):

    net = AwsTopology()
    trasnsit_gateways = dict()

    for filepath in get_files(dir_path, ".pb"):
        data = read_proto_file(filepath)
        assets = data.snapshot[0].assets
        
        for tgw in assets.transitGateways:
            if tgw.assetId not in trasnsit_gateways:
                trasnsit_gateways[tgw.assetId] = tgw
                net.add_transit_gateway(tgw.assetId, tgw.name)

        for vpc in assets.vpcs:
            net.add_vpc(vpc.assetId, vpc.name)

        for tgwa in assets.transitGatewayAttachments:
            if not tgwa.tgwArn:
                #print(f"TGW ARN not found for {tgwa}")
                continue
            else:
                net.add_tgw_attachment(tgwa)

        for peering in assets.transitGatewayPeeringAttachments:
            net.add_tgw_peering(peering.requesterArn, peering.accepterArn, peering.assetId)
            
        for vpc in assets.vpcPeeringConnections:
            net.add_vpc_peering(vpc.requesterVpcInfo.vpcArn, vpc.accepterVpcInfo.vpcArn, vpc.vpcPeeringConnectionId)    

        for vpngw in assets.vpnGateways:
            for vpc in vpngw.vpcAttachments:
                net.add_vpn_gateway_connection(vpngw.assetId, vpc.vpcArn)

        for dcg in assets.awsDirectConnectGateway:
            net.add_direct_connect_gateway(dcg.directConnectGatewayId, dcg.directConnectGatewayName)
            for association in dcg.directConnectGatewayAssociations:
                if association.associatedGateway.type == cm.DirectConnectGatewayGatewayType.DIRECT_CONNECT_GATEWAY_GATEWAY_TYPE_VIRTUAL_PRIVATE_GATEWAY:
                    vgw = association.associatedGateway
                    vgw_arn = reconstruct_arn('ec2', vgw.ownerAccount, vgw.region, 'vpn-gateway', vgw.id)
                    net.add_vpn_gateway(vgw_arn)
                    net.network.add_edge(dcg.directConnectGatewayId, vgw_arn, color="blue", title=association.associationId, weight=DIRECT_CONNECT_VPN_CONNECTION_WIDTH)
                

        for dcc in assets.directConnectConnections:
            net.add_direct_connect_connection(dcc.connectionId, dcc.connectionName)
        
        for dcvif in assets.directConnectVirtualInterfaces:
            net.add_direct_connect_virtual_interface(dcvif)
            
    return net

def count_resource_type(graph,resource_type):
    count = 0
    for node in graph.nodes(data=True):
        if node[1].get("resource_type", "") == resource_type:
            count+=1

    return count

def main():
    parser = argparse.ArgumentParser(description="Generate AWS topology graph.")
    parser.add_argument("--input_dir", dest="dir_path", type=str, required=True,
                        help="Path to the directory containing .pb files.")
    parser.add_argument("--output", dest="output_file", type=str, default="example.html",
                        help="Path to the output HTML file.")
    args = parser.parse_args()
    dir_path = args.dir_path
    output_file = args.output_file
    if not os.path.exists(dir_path):
        print(f"Directory {dir_path} does not exist.")
        return
    if not os.path.isdir(dir_path):
        print(f"{dir_path} is not a directory.")
        return
    net = create_graph(dir_path)
    net.show(output_file)

if __name__ == "__main__":
    main()