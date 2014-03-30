# Copyright (c) 2013-2014 Marin Atanasov Nikolov <dnaeon@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer
#    in this position and unchanged.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR(S) ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR(S) BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
vPoller Connector Module

This module provides classes and methods for managing 
connections to VMware vSphere hosts and retrieving of object properties

"""

import logging
import sqlite3

import pyVmomi
import pyVim.connect

class VConnectorException(Exception):
    """
    Generic VConnector exception

    """
    pass

class VConnector(object):
    """
    VConnector class

    The VConnector class defines methods for connecting, disconnecting and
    retrieving objects from a VMware vSphere host

    Returns:
        VConnector object
    
    Raises:
        VConnectorException

    """
    def __init__(self, user, pwd, host):
        """
        Initializes a new VConnector object

        Args:
            user (str): Username to use when connecting
            pwd  (str): Password to use when connecting 
            host (str): VMware vSphere host to connect to

        """
        self.user = user
        self.pwd  = pwd
        self.host = host

    def connect(self):
        """
        Connect to the VMware vSphere host

        Raises:
             VPollerException
        
        """
        logging.info('Connecting vSphere Agent to %s', self.host)
        
        try:
            self.si = pyVim.connect.SmartConnect(
                host=self.host,
                user=self.user,
                pwd=self.pwd
            )
        except Exception as e:
            raise VConnectorException, 'Cannot connect to %s: %s' % (self.host, e)

    def disconnect(self):
        """
        Disconnect from the VMware vSphere host

        """
        logging.info('Disconnecting vSphere Agent from %s', self.host)
        pyVim.connect.Disconnect(self.si)

    def reconnect(self):
        """
        Reconnect to the VMware vSphere host

        """
        self.disconnect()
        self.connect()

    def get_datacenter_view(self):
        """
        Get a view ref to all pyVmomi.vim.Datacenter managed objects

        """
        return self.get_container_view(obj_type=[pyVmomi.vim.Datacenter])

    def get_cluster_view(self):
        """
        Get a view ref to all pyVmomi.vim.ClusterComputeResource managed objects

        """
        return self.get_container_view(obj_type=[pyVmomi.vim.ClusterComputeResource])

    def get_host_view(self):
        """
        Get a view ref to all pyVmomi.vim.HostSystem managed objects

        """
        return self.get_container_view(obj_type=[pyVmomi.vim.HostSystem])

    def get_vm_view(self):
        """
        Get a view ref to all pyVmomi.vim.VirtualMachine managed objects

        """
        return self.get_container_view(obj_type=[pyVmomi.vim.VirtualMachine])

    def get_datastore_view(self):
        """
        Get a view ref to all pyVmomi.vim.Datastore managed objects

        """
        return self.get_container_view(obj_type=[pyVmomi.vim.Datastore])

    def get_resource_pool_view(self):
        """
        Get a view ref to all pyVmomi.vim.ResourcePool managed objects

        """
        return self.get_container_view(obj_type=[pyVmomi.vim.ResourcePool])

    def collect_properties(self, view_ref, obj_type, path_set=[]):
        """
        Collect properties for managed objects from a view ref

        Check the vSphere API documentation for example on retrieving object properties:
    
            - http://pubs.vmware.com/vsphere-50/index.jsp#com.vmware.wssdk.pg.doc_50/PG_Ch5_PropertyCollector.7.2.html

        Args:
            view_ref (pyVmomi.vim.view.ContainerView): Starting point of inventory navigation
            obj_type                  (pyVmomi.vim.*): Type of managed object
            path_set                           (list): List of properties to retrieve

        Returns:
            A list of properties for the managed objects

        """
        logging.debug('[%s] Collecting properties for %s managed objects', self.host, obj_type.__name__)

        collector = self.si.content.propertyCollector
        
        # Create object specification to define the starting point of inventory navigation
        obj_spec = pyVmomi.vmodl.query.PropertyCollector.ObjectSpec()
        obj_spec.obj = view_ref
        obj_spec.skip = True

        # Create a traversal specification to identify the path for collection
        traversal_spec = pyVmomi.vmodl.query.PropertyCollector.TraversalSpec()
        traversal_spec.name = 'traverseEntities'
        traversal_spec.path = 'view'
        traversal_spec.skip = False
        traversal_spec.type = view_ref.__class__
        obj_spec.selectSet = [traversal_spec]

        # Identify the properties to the retrieved
        property_spec = pyVmomi.vmodl.query.PropertyCollector.PropertySpec()
        property_spec.type = obj_type
                
        if not path_set:
            logging.warning('[%s] Retrieving all properties for objects, this might take a while...'. self.host)
            property_spec.all = True
            
        property_spec.pathSet = path_set

        # Add the object and property specification to the property filter specification
        filter_spec = pyVmomi.vmodl.query.PropertyCollector.FilterSpec()
        filter_spec.objectSet = [obj_spec]
        filter_spec.propSet = [property_spec]

        # Retrieve properties
        props = collector.RetrieveContents([filter_spec])

        data = [{p.name:p.val for p in obj.propSet} for obj in props]

        return data

    def get_container_view(self, obj_type, container=None):
        """
        Get a vSphere Container View reference to all objects of type 'obj_type'

        Args:
            obj_type (list): A list of managed object types

        Returns:
            A container view refence to the discovered managed objects
        
        """
        if not container:
            container = self.si.content.rootFolder

        logging.debug('[%s] Getting container view ref to %s managed objects', self.host, [t.__name__ for t in obj_type])

        view_ref = self.si.content.viewManager.CreateContainerView(
            container=container,
            type=obj_type,
            recursive=True
        )

        return view_ref

class VConnectorDatabase(object):
    """
    VConnectorDatabase class

    Provides an SQLite database backend for storing information
    about vSphere Agents, such as hostname, username, password, etc.
    
    Returns:
        VConnectorDatabase object
    
    Raises:
        VConnectorException

    """
    def __init__(self, db):
        """
        Initializes a new VConnectorDatabase object

        Args:
            db (str): Path to the SQLite database file

        """
        self.db = db
        self.conn = sqlite3.connect(self.db)

    def init_db(self):
        """
        Initializes the vConnector Database backend

        """
        logging.info('Initializing vConnector database at %s', self.db)

        self.cursor = self.conn.cursor()

        sql = """
        CREATE TABLE hosts (
            host TEXT UNIQUE,
            user TEXT,
            pwd  TEXT,
            enabled INTEGER
        )
        """

        try:
            self.cursor.execute(sql)
        except sqlite3.OperationalError as e:
            raise VConnectorException, 'Cannot initialize database: %s' % e

        self.conn.commit()
        self.cursor.close()

    def add_update_agent(self, host, user, pwd, enabled=0):
        """
        Add/update a vSphere Agent in the vConnector database

        Args:
            host    (str): Hostname of the vSphere host
            user    (str): Username to use when connecting
            pwd     (str): Password to use when connecting
            enabled (int): If True mark this vSphere Agent as enabled

        """
        logging.info('Adding/updating vSphere Agent %s in database', host)

        self.cursor = self.conn.cursor()
        self.cursor.execute('INSERT OR REPLACE INTO hosts VALUES (?,?,?,?)', (host, user, pwd, enabled))
        self.conn.commit()
        self.cursor.close()

    def remove_agent(self, host):
        """
        Remove a vSphere Agent from the vConnector database

        Args:
            host (str): Hostname of the vSphere Agent to remove
        
        """
        logging.info('Removing vSphere Agent %s from database', host)

        self.cursor = self.conn.cursor()
        self.cursor.execute('DELETE FROM hosts WHERE host = ?', (host,))
        self.conn.commit()
        self.cursor.close()

    def get_agents(self, only_enabled=False):
        """
        Get the vSphere Agents from the vConnector database

        Args:
            only_enabled (bool): If True return only the Agents which are enabled

        """
        logging.debug('Getting vSphere Agents from database')

        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        if only_enabled:
            sql = 'SELECT * FROM hosts WHERE enabled = 1'
        else:
            sql = 'SELECT * FROM hosts'

        self.cursor.execute(sql)
        result = self.cursor.fetchall()
        self.cursor.close()

        return result

    def enable_agent(self, host):
        """
        Mark a vSphere Agent as enabled

        Args:
            host (str): Hostname of the vSphere Agent to enable

        """
        logging.info('Enabling vSphere Agent %s', host)

        self.cursor = self.conn.cursor()
        self.cursor.execute('UPDATE hosts SET enabled = 1 WHERE host = ?', (host,))
        self.conn.commit()
        self.cursor.close()
        
    def disable_agent(self, host):
        """
        Mark a vSphere Agent as disabled

        Args:
            host (str): Hostname of the vSphere Agent to disable

        """
        logging.info('Disabling vSphere Agent %s', host)

        self.cursor = self.conn.cursor()
        self.cursor.execute('UPDATE hosts SET enabled = 0 WHERE host = ?', (host,))
        self.conn.commit()
        self.cursor.close()
