import json
from pyvis.network import Network
import networkx as nx
import os
from prot import read_proto_file
from te.service.cm.v1 import cm_snapshot_pb2 as cm
import argparse

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
    TRANSIT_GATEAWAY_NODE_SIZE = 60
    VPC_NODE_SIZE = 20
    VPN_NODE_SIZE = 10
    DIRECT_CONNECT_NODE_SIZE = 50

    def __init__(self):
        self.network = nx.Graph()

    def add_transit_gateway(self, tgw_id):
        """ 
        Add a transit gateway to the network.
        """
        self.network.add_node(tgw_id, label="TGW", title=tgw_id, image=TGW_URL, shape="image", resource_type="tgw", level=1, size=self.TRANSIT_GATEAWAY_NODE_SIZE)

    def add_vpc(self, vpc_arn):
        """ 
        Add a VPC to the network with data account and region.
        """
        vpc_id = vpc_arn.replace("garn:", "arn:").lower()
        # vpc_id = self.arn_group_by_account_region(vpc_id)
        account_id, region_id = self.extract_account_region_from_arn(vpc_arn)
        
        self.network.add_node(vpc_id, label="VPC", title=vpc_id, image="images/vpc.svg", shape="image", level=2, size=self.VPC_NODE_SIZE)
        if account_id and region_id:
            self.network.nodes[vpc_id]['resource_type'] = "vpc"
            self.network.nodes[vpc_id]['account'] = account_id
            self.network.nodes[vpc_id]['region'] = region_id
    
    def add_vpn_gateway(self, arn):
        """ 
        Add a VPN gateway to the network.
        """
        vpn_id = arn.replace("garn:", "arn:").lower()
        account_id, region_id = self.extract_account_region_from_arn(vpn_id)
        self.network.add_node(vpn_id, label="VPN", title=vpn_id, image="images/vpn-gateway.svg", shape="image", level=3, size=self.VPN_NODE_SIZE)
        if account_id and region_id:
            self.network.nodes[vpn_id]['resource_type'] = "vpn-gateway"
            self.network.nodes[vpn_id]['account'] = account_id
            self.network.nodes[vpn_id]['region'] = region_id
        
    def add_vpn_connection(self, arn):
        """ 
        Add a VPN connection to the network.
        """
        vpn_id = arn.replace("garn:", "arn:").lower()
        account_id, region_id = self.extract_account_region_from_arn(vpn_id)
        self.network.add_node(vpn_id, label="VPN", title=vpn_id, image="images/vpn-connection.svg", shape="image", level=3, size=self.VPN_NODE_SIZE)
        if account_id and region_id:
            self.network.nodes[vpn_id]['resource_type'] = "vpn-connection"
            self.network.nodes[vpn_id]['account'] = account_id
            self.network.nodes[vpn_id]['region'] = region_id

    def add_direct_connect_gateway(self, arn):
        """ 
        Add a Direct Connect gateway to the network.
        """
        dcg_id = arn.replace("garn:", "arn:").lower()
        account_id, region_id = self.extract_account_region_from_arn(dcg_id)
        self.network.add_node(dcg_id, label="DCG", title=dcg_id, image="images/direct-connect-gateway.svg", shape="image", level=0, size=self.DIRECT_CONNECT_NODE_SIZE)
        if account_id and region_id:
            self.network.nodes[dcg_id]['resource_type'] = "direct-connect-gateway"
            self.network.nodes[dcg_id]['account'] = account_id
            self.network.nodes[dcg_id]['region'] = region_id

    def add_vpc_peering(self, vpc_id, peer_vpc_id, connection_id):
        """ 
        Add a VPC peering connection to the network.
        """
        vpc_id = vpc_id.replace("garn:", "arn:").lower()
        peer_vpc_id = peer_vpc_id.replace("garn:", "arn:").lower()
        self.add_vpc(vpc_id)
        self.add_vpc(peer_vpc_id)
        self.network.add_edge(vpc_id, peer_vpc_id, color="green", title=connection_id)

    def _add_attachment_connection_node(self, node_id):
        resource_type = self.extract_resource_type(node_id)
        self.network.add_node(node_id, label=resource_type, title=node_id, color="blue", shape="image", image=f"images/{resource_type}.svg")

    def _add_attachment_edge(self, node_id, tgw_id, attachment_id, attachment_type=None):
        """
        Add an attachment connection to the network.
        """
        ATTACHMENT_TYPE_COLORS ={
            "TGW-Attach": "black",
            "VPC-Peering": "green",
            "TGW-Peering": "red"
        }
        self.network.add_edge(node_id, tgw_id,
                               title=attachment_id, color=ATTACHMENT_TYPE_COLORS[attachment_type])

    def add_attachment(self, node_id, tgw_id, attachment_id, attachment_type=None):
        """
        Add an attachment to the network.
        """
        node_id = node_id.replace("garn:", "arn:").lower()
        tgw_id = tgw_id.replace("garn:", "arn:").lower()
        if attachment_type == "TGW-Peering":
            self.add_transit_gateway(node_id)
            self.add_transit_gateway(tgw_id)
        else:
            self._add_attachment_connection_node(node_id)
            
            
        self._add_attachment_edge(node_id, tgw_id, attachment_id, attachment_type)

    def add_vpn_gateway_connection(self, node_id, vpc_id):
        """
        Add a VPN gateway to the network.
        """
        node_id = node_id.replace("garn:", "arn:").lower()
        vpc_id = vpc_id.replace("garn:", "arn:").lower()
        self.add_vpn_gateway(node_id)
        self.add_vpc(vpc_id)
        self.network.add_edge(node_id, vpc_id, color="black")

    def get_min_size_connected_componnents_subgraph(self, min_size=2):
        """
        Get the subgraph of connected components with a minimum size.
        """
        connected_components = list(nx.connected_components(self.network))
        filtered_nodes =  [node for component in connected_components if len(component) >= min_size for node in component]
        subgraph = self.network.subgraph(filtered_nodes)
        return subgraph

    def show(self, output_file="example.html"):
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

        orig_graph = Network(notebook=True, cdn_resources="remote", height="1440px", width="100%",select_menu=True, filter_menu=True)
        orig_graph.from_nx(self.get_min_size_connected_componnents_subgraph(6))
        orig_graph.toggle_physics(True)
        orig_graph.force_atlas_2based()
        orig_graph.show(output_file)


    @staticmethod
    def extract_resource_type(resource_arn):
        """
        Extract the resource type from the ARN.
        """
        parts = resource_arn.split(':')
        if len(parts) > 5:
            return parts[5].split('/')[0]
        return None

    @staticmethod
    def extract_account_region_from_arn(arn):
        """
        Extract the account ID and region from the ARN.
        """
        parts = arn.split(':')
        if len(parts) > 4:
            account_id = parts[4]
            region_id = parts[3]
            return account_id, region_id
        return None, None


    def add_tgw_attachment(self, transit_gateway_attachment):
        """
        Add a TGW attachment to the network.
        """
        tgw_id = transit_gateway_attachment.tgwArn.replace("garn:", "arn:").lower()
        self.add_transit_gateway(tgw_id)

        node_id = transit_gateway_attachment.resourceArn.replace("garn:", "arn:").lower()
        resource_types = cm.TgwAttachmentResourceType
        match transit_gateway_attachment.resourceType:
            case resource_types.TGW_RESOURCE_TYPE_VPC:
                self.add_vpc(node_id)
            case resource_types.TGW_RESOURCE_TYPE_VPN:
                self.add_vpn_connection(node_id)
            case resource_types.TGW_RESOURCE_TYPE_DIRECT_CONNECT_GATEWAY:
                self.add_direct_connect_gateway(node_id)
            case _:
                print(f"Unknown resource type: {transit_gateway_attachment.resourceType}")
            
        attachment_id = transit_gateway_attachment.transitGatewayAttachmentId.replace("garn:", "arn:").lower()
        self.network.add_edge(node_id, tgw_id,title=attachment_id, color='black')
    
    def add_tgw_peering(self, tgw_id, peer_tgw_id, attachment_id):
        """
        Add a TGW peering connection to the network.
        """
        tgw_id = tgw_id.replace("garn:", "arn:").lower()
        peer_tgw_id = peer_tgw_id.replace("garn:", "arn:").lower()
        self.add_transit_gateway(tgw_id)
        self.add_transit_gateway(peer_tgw_id)
        self.network.add_edge(tgw_id, peer_tgw_id, color="red", title=attachment_id)

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
                net.add_transit_gateway(tgw.assetId)

        for tgwa in assets.transitGatewayAttachments:
            if not tgwa.tgwArn:
                print(f"TGW ARN not found for {tgwa}")
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

    return net

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