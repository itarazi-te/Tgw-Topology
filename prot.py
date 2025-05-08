import google.protobuf.json_format as MessageToDict
import json
from os import path

import sys
temp_dir = "./generated"
sys.path.append(temp_dir)
sys.path.append(temp_dir + '/te')
sys.path.append(temp_dir + '/te/service')
sys.path.append(temp_dir + '/te/service/cm')
sys.path.append(temp_dir + '/te/service/cm/v1')

from te.service.cm.v1 import cm_snapshot_file_response_pb2
import os

snapshot_files_response = cm_snapshot_file_response_pb2.SnapshotFilesResponse()
def convert_to_json_file(proto_message, output_file):
    """
    Convert a protobuf message to JSON and write it to a file.
    """
    json_output = MessageToDict.MessageToDict(proto_message)
    with open(output_file, "w") as json_file:
        json.dump(json_output, json_file, indent=4)
    print(f"JSON output written to {output_file}")


def read_proto_file(file_path):
    """
    Read a protobuf file and return the parsed message.
    """
    with open(file_path, "rb") as f:
        pb_data = f.read()
    snapshot_files_response.ParseFromString(pb_data)
    return snapshot_files_response

def convert_file(filepath):
    """
    Convert a protobuf file to JSON.
    """
    filename = path.basename(filepath)
    output_file = "output/huron/" + path.splitext(filename)[0] + ".json"
    pb_data = read_proto_file(filepath)
    convert_to_json_file(pb_data, output_file)

def discover_and_convert_files(directory):
    """
    Discover all .pb files in a specific directory and convert them to JSON.
    """
    if not os.path.exists("output"):
        os.makedirs("output")
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".pb"):
                file_path = os.path.join(root, file)
                print(f"Processing file: {file_path}")
                convert_file(file_path)

if __name__ == "__main__":
    discover_and_convert_files("source/562949953427311")
    