"""
arg_transforms methods for use in decorators
"""

def dos_transform(dos, fmt="%Y%m"):
    """
    Transform a datetime.date object into a string of the form YYYYMM
    """
    return dos.strftime(fmt) if dos else None
    
def dos_transform_YYYYMM(dos):
    """
    Transform a datetime.date object into a string of the form YYYYMM
    """
    return dos_transform(dos, fmt="%Y%m")

def zipcode_4(zipcode):
    return str(zipcode)[:4] if zipcode else None
    