
def extract_resource_type(resource_arn):
    """
    Extract the resource type from the ARN.
    """
    parts = resource_arn.split(':')
    if len(parts) > 5:
        return parts[5].split('/')[0]
    return None

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

def reconstruct_arn(service, account_id, region_id, resource_type, resource_id):
    """
    Reconstruct the ARN from the service, account ID, region ID, resource type, and resource ID.
    """
    return f"arn:aws:{service}:{region_id}:{account_id}:{resource_type}/{resource_id}"
    
