import json
from pyvis.network import Network
import os

TGW_URL = "images/tgw.svg"
def read_json_file(file_path):
    """
    Read a JSON file and return the parsed data.
    """
    with open(file_path, "r") as f:
        data = json.load(f)
    return data

def get_files(directory):
    """
    Discover all .json files in a specific directory and return their paths.
    """
    file_paths = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                file_paths.append(file_path)
    return file_paths


class AwsTopology:
    def __init__(self):
        self.network = Network(notebook=True, cdn_resources="remote", width="100%")
        self.network.show_buttons(filter_='physics')

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

    def show(self):
        """
        Display the network.
        """
        self.network.show("example.html")


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

count_transit_gateways_peering = 0
for filepath in get_files("./output/huron/"):
    data = read_json_file(filepath)

    assets = data['snapshot'][0]['assets']
    
    if 'transitGateways' in assets:
        for item in assets['transitGateways']:
            if item['assetId'] not in trasnsit_gateways:
                trasnsit_gateways[item['assetId']] = item
                net.add_transit_gateway(item['assetId'])

    if 'transitGatewayAttachments' in assets:
        for item in assets['transitGatewayAttachments']:
            if 'tgwArn' in item:
                net.add_attachment(item['resourceArn'], item['tgwArn'], item['assetId'], 'TGW-Attach')

    if 'transitGatewayPeeringAttachments' in assets:
        for item in assets['transitGatewayPeeringAttachments']:
            net.add_attachment(item['requesterArn'], item['accepterArn'], item['assetId'], "TGW-Peering")
            count_transit_gateways_peering += 1

    if "vpcPeeringConnections" in assets:
        for item in assets["vpcPeeringConnections"]:
            net.add_attachment(item['requesterVpcInfo']['vpcArn'], item['accepterVpcInfo']['vpcArn'], item['vpcPeeringConnectionId'], "VPC-Peering")

# print(json.dumps(trasnsit_gateways, indent=2))

net.show()

print(f"Total number of TGW Peering Attachments: {count_transit_gateways_peering}")