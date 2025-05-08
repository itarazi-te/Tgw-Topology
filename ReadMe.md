## Network topology viewer

## Generate python code from proto files:

You can use the files from the repo or generate again by running the following command:

```bash
for file in ./proto/te/service/cm/v1/*.proto; do
    protoc --python_out=.generated/ --proto_path=./proto/ "$file"
done
```

## Generate Topology:

1. Download the snapshots from the inventory page and unzip them/
2. Download pip packages:

```bash
pip install -r requirements.txt
```

3. Run the script:

```bash
python3 snapshot.py --input_dir <path to pb files dir> --output <path to output html file>
```
