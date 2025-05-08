import json
from pyvis.network import Network
import os
from prot import read_proto_file

TGW_URL = "images/tgw.svg"
def read_json_file(file_path):
    """
    Read a JSON file and return the parsed data.
    """
    with open(file_path, "r") as f:
        data = json.load(f)
    return data

def get_files(directory, extension=".json"):
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
        self.network = Network(notebook=True, cdn_resources="remote", height="1440px", width="100%",select_menu=True, filter_menu=True)
        #self.network.show_buttons()
        #self.network.toggle_physics(True)
        self.network.force_atlas_2based()
        #self.network.show_buttons(filter_='physics')

    def add_transit_gateway(self, tgw_id):
        """ 
        Add a transit gateway to the network.
        """
        self.network.add_node(tgw_id, label="TGW", title=tgw_id, image=TGW_URL, shape="image")

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
        else:
            self._add_attachment_connection_node(node_id)
        self.add_transit_gateway(tgw_id)
        self._add_attachment_edge(node_id, tgw_id, attachment_id, attachment_type)

    def add_vpn_gateway(self, node_id, vpc_id):
        """
        Add a VPN gateway to the network.
        """
        node_id = node_id.replace("garn:", "arn:").lower()
        vpc_id = vpc_id.replace("garn:", "arn:").lower()
        self.network.add_node(node_id, label="VPN", title=node_id, image="images/vpn-gateway.svg", shape="image")
        self.network.add_node(vpc_id, label="VPC", title=vpc_id, image="images/vpc.svg", shape="image")
        self.network.add_edge(node_id, vpc_id, color="black")

    # def add_tg_route(self):
        

    def show(self):
        """
        Display the network.
        """
        self.network.show("example2.html")


    @staticmethod
    def extract_resource_type(resource_arn):
        """
        Extract the resource type from the ARN.
        """
        parts = resource_arn.split(':')
        if len(parts) > 5:
            return parts[5].split('/')[0]
        return None




net = AwsTopology()
trasnsit_gateways = dict()

for filepath in get_files("./source/562949953427311/", ".pb"):
    
    data = read_proto_file(filepath)

    assets = data.snapshot[0].assets
    
    for tgw in assets.transitGateways:
        if tgw.assetId not in trasnsit_gateways:
            trasnsit_gateways[tgw.assetId] = tgw
            net.add_transit_gateway(tgw.assetId)

    for tgwa in assets.transitGatewayAttachments:


        if tgwa.tgwArn:
            net.add_attachment(tgwa.resourceArn, tgwa.tgwArn, tgwa.assetId, 'TGW-Attach')
        else:
            print(f"TGW ARN not found for {tgwa}")

    for peering in assets.transitGatewayPeeringAttachments:
        net.add_attachment(peering.requesterArn, peering.accepterArn, peering.assetId, "TGW-Peering")
        
    for vpc in assets.vpcPeeringConnections:
        net.add_attachment(vpc.requesterVpcInfo.vpcArn, vpc.accepterVpcInfo.vpcArn, vpc.vpcPeeringConnectionId, "VPC-Peering")    

    for vpngw in assets.vpnGateways:
        for vpc in vpngw.vpcAttachments:
            net.add_vpn_gateway(vpngw.assetId, vpc.vpcArn)


net.show()

