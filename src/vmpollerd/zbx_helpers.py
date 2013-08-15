"""
Collection of functions to convert any Python values to Zabbix friendly ones

TODO: This here needs to be cleaned up
"""


def return_as_is(val):
    """
    Helper function, which returns property value as-is

    """
    return val

def return_as_time(val):
    """
    Helper function, which returns property value as time

    """
    return time.strftime('%Y-%m-%d %H:%M:%S', val)

def return_as_int(val):
    """
    Helper function, which returns property value as integer

    """
    return int(val)

def return_as_bytes(val):
    """
    Helper function, which returns property value as bytes

    """
    return val * 1048576

def return_as_hz(val):
    """
    Helper function, which returns property value as hz

    """
    return val * 1048576

def datastore_used_space_percentage(d):
    """
    Calculate the used datastore space in percentage

    """
    return round(100 - (float(d['summary.freeSpace']) / float(d['summary.capacity']) * 100), 2)
    
