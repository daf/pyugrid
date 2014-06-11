#!/usr/bin/env python

"""
ugrid classes

set of classes for working with unstructured model grids

The "ugrid" class is the base class: it stores eveything in memory

subclasses include a nc_ugrid, which points to a netcdf file (Or opendap url).

It provides the same API, but does not store the data in memory, rather
reading it on demand

NOTE: only full support for triangular mesh grids at the moment

"""

import numpy as np

# used for simple locate_face test
#from py_geometry.cy_point_in_polygon import point_in_poly as point_in_tri
from .util import point_in_tri

IND_DT = np.int32 ## datatype used for indexes -- might want to change for 64 bit some day.
NODE_DT = np.float64 ## datatype used for node coordinates


class DataSet(object):
    """
    A class to hold the data assocated with nodes, edges, etc.

    It holds an array of the data, as well as the attributes associated
     with that data (attributes get stored in the netcdf file)

    """
    def __init__(self, name, location='node', data=None, attributes=None):
        """
        create a data_set object
        :param name: the name of the data (depth, u_velocity, etc.)
        :type name: string

        :param location: the type of grid element: 'node', 'edge', or 'face' the data is assigned to

        :param data: the data
        :type data: 1-d numpy array, or somthing compatible (list, etc.)        

        """
        self.name = name

        if location not in ['node', 'edge', 'face']:
            raise ValueError("location must be one of: 'node', 'edge', 'face'")
        self.location = location # must be 'node', 'edge', of 'face' (eventually 'volume')

        if data is None:
            self._data = np.zeros((0,), dtype=np.float64) # could be any data type
        else:
            self._data = np.asarray(data)

        self.attributes = {} if attributes is None else attributes

    @property
    def data(self):
        return self._data
    @data.setter
    def data(self, data):
        self._data = np.asarray(data)
    @data.deleter
    def data(self):
        self._data = self._data = np.zeros((0,), dtype=np.float64)

    def __str__(self):
        return "DataSet object: {0:s}, on the {1:s}s, and {2:d} data points\nAttributes: {3}".format(self.name, self.location, len(self.data), self.attributes)


class DataSetIndexed(DataSet):
    """
    a class to hold the arrays used to map data to indexes of the nodes, edges
    or faces they are assigned to, if there is not that data on all of the objects
    do we ever need this?

    """
    ## fixme: do we want a special case for when there is data on all the nodes, edges, etc?

    def __init__(self, name, type='node', indexes=None, data=None):
        """
        create a data_set object

        name: the name of the data (depth, u_velocity, etc)

        type: the type of grid element: node, edge, or face the data is assigned to

        """
        self.name = name
        self.type = type # must be 'node', 'edge', of 'face' (eventually 'volume')
        if (indexes is None) ^  (data is None):
            raise ValueError("indexes and data both need to be either None or have values")
        if indexes is None:
            self.indexes = np.zeros((0,), dtype=IND_DT) 
        else:
            self.indexes = indexes
        if data is None:
            self.data = np.zeros((0,), dtype=np.float) # could be any data type
        else:
            self.data = data

    def check_consistent(self):
        """
        check if the indexes match the data, etc.
        """
        raise NotImplimentedError


class UGrid(object):
    """
    a basic class to hold an unstructred grid (triangular mesh)

    the internal structure mirrors the netcdf data standard.
    """

    def __init__(self,
                 nodes=None,
                 faces=None,
                 edges=None,
                 face_face_connectivity=None):
        """
        ugrid class -- holds, saves, etc an unstructured grid

        :param nodes=None : the coordinates of the nodes -- (NX2) float array
        :param faces=[] : the faces of the grid -- (NX3) integer array of indexes into the nodes array
        :param edges=[] : the edges of the grid -- (NX2) integer array of indexes into the nodes array

        often this is too much data to pass in a literal -- so usually
        specialized constructors will be used instead (load from file, etc.)
        """

        if nodes is None:
            self._nodes = np.zeros((0,2), dtype=NODE_DT)
        else:
            self._nodes = np.asarray(nodes, dtype=NODE_DT).reshape((-1, 2))

        if faces is None:
            self._faces = None
        else:
            self._faces = np.asarray(faces, dtype=IND_DT).reshape((-1, 3))

        if edges is None:
            self._edges = None
        else:
            self._edges = np.asarray(edges, dtype=IND_DT).reshape((-1, 2))

        if face_face_connectivity is None:
            self._face_face_connectivity = None
        else:
            self._face_face_connectivity = np.asarray(face_face_connectivity, dtype=IND_DT).reshape((-1, self.num_vertices))

        # the data associated with the grid
        # should be a dict of DataSet objects
        self._data = {} # the data associated with the grid
        # self._node_data = {}
        # self._edge_data = {}
        # self._face_data = {}

    @classmethod
    def from_ncfile(klass, nc_url, mesh_name=None):
        """
        create a UGrid object from a netcdf file (or opendap url)

        :param nc_url: the filename or OpenDap url you want to load

        :param mesh_name=None: the name of the mesh you want. If None, then
                               you'll get an arbitrary mesh (which is good if
                               there is only one in the file)
        """
        ## fixme: this really should only load the mesh that is looked for.
        ##        requires changes to open_cf_todict
        data = open_cf_todict(nc_url)
        if mesh_name is None:
            ug = data[data.keys()[0]]
        else:
            ug = data[mesh_name]
        return ug

    def check_consistent(self):
        """
        check if the various data is consistent: the edges and faces reference
        existing nodes, etc.
        """
        raise NotImplimentedError
    
    @property
    def num_vertices(self):
        """
        number of vertices in a face
        """
        if self._faces is None:
            return None
        else:
            return self._faces.shape[1]

    @property
    def nodes(self):
        return self._nodes
    @nodes.setter
    def nodes(self, nodes_coords):
        # room here to do consistency checking, etc.
        # for now -- simply make sure it's a numpy array
        self._nodes = np.asarray(nodes_coords, dtype=NODE_DT).reshape((-1, 2))
    @nodes.deleter
    def nodes(self):
        ## if there are no nodes, there can't be any faces or edges
        self._nodes = np.zeros((0,2), dtype=NODE_DT)
        self._edges = None
        self._faces = None

    @property
    def faces(self):
        return self._faces
    @faces.setter
    def faces(self, faces_indexes):
        # room here to do consistency checking, etc.
        # for now -- simply make sure it's a numpy array
        self._faces = np.asarray(faces_indexes, dtype=IND_DT).reshape((-1, 3))
    @faces.deleter
    def faces(self):
        self._faces = None

    @property
    def edges(self):
        return self._edges
    @edges.setter
    def edges(self, edges_indexes):
        # room here to do consistency checking, etc.
        # for now -- simply make sure it's a numpy array
        self._edges = np.asarray(edges_indexes, dtype=IND_DT).reshape((-1, 2))
    @edges.deleter
    def edges(self):
        self._edges = None

    @property
    def face_face_connectivity(self):
        return self._face_face_connectivity
    @face_face_connectivity.setter
    def face_face_connectivity(self, face_face_connectivity):
        ## add more checking?
        face_face_connectivity = np.asarray(face_face_connectivity, dtype=IND_DT).reshape((-1, self.num_vertices))
    @face_face_connectivity.deleter
    def face_face_connectivity(self):
        self._face_face_connectivity = None

    @property
    def data(self):
        """
        dict of data associated with the data arrays

        you can't set this -- msut use UGrid.add_data()

        """
        return self._data

    def add_data(self, data_set):
        """
        Add a dataset to the data dict

        :param data_set: the DataSet object to add. its name will be the key in the data dict.
        :type data_set: a ugrid.DataSet object

        some sanity checking is done to make sure array sizes are correct.

        """
        # do a size check:
        if data_set.location == 'node':
            if len(data_set.data) != len(self.nodes):
                raise ValueError("length of data array much match the number of nodes")
        elif data_set.location == 'edge':
            if len(data_set.data) != len(self.edges):
                raise ValueError("length of data array much match the number of edges")
        elif data_set.location == 'face':
            if len(data_set.data) != len(self.faces):
                raise ValueError("length of data array much match the number of faces")
        print self._data
        self._data[data_set.name] = data_set


# ##fixme: repeated code here -- should these methods be combined?
#          is there any need for this at all?
#     def set_node_data(self, name, data, indexes=None):
#         if indexes is None:
#             data = np.asarray(data)
#             if not data.shape == (self.num_nodes,):
#                 raise ValueError("size of data should match number of nodes") # shape should match edges, data type can be anything
#             self._node_data[name] = data
#         else:
#             indexes = np.array(indexes, dtype=IND_DT).reshape((-1,))
#             self._node_data[name][indexes] = data

#     def get_node_data(self, name, indexes=None):
#         if indexes is None:
#             return self._node_data[name]
#         else:
#             indexes = np.array(indexes, dtype=IND_DT).reshape((-1,))
#             return self._node_data[name][indexes]

#     def set_edge_data(self, name, data, indexes=None):
#         if indexes is None:
#             data = np.asarray(data)
#             if not data.shape == (self.num_edges,):
#                 raise ValueError("size of data shold match number of edges") # shape should match edges, data type can be anything
#             self._edge_data[name] = data
#         else:
#             indexes = np.array(indexes, dtype=IND_DT).reshape((-1,))
#             self._edge_data[name][indexes] = data

#     def get_edge_data(self, name, indexes=None):
#         if indexes is None:
#             return self._edge_data[name]
#         else:
#             indexes = np.array(indexes, dtype=IND_DT).reshape((-1,))
#             return self._edge_data[name][indexes]

#     def set_face_data(self, name, data, indexes=None):
#         if indexes is None:
#             data = np.asarray(data)
#             if not data.shape == (self.num_faces,):
#                 raise ValueError("size of data shold match number of faces") # shape should match faces, data type can be anything
#             self._face_data[name] = data
#         else:
#             indexes = np.array(indexes, dtype=IND_DT).reshape((-1,))
#             self._face_data[name][indexes] = data

#     def get_face_data(self, name, indexes=None):
#         if indexes is None:
#             return self._face_data[name]
#         else:
#             indexes = np.array(indexes, dtype=IND_DT).reshape((-1,))
#             return self._face_data[name][indexes]


    def locate_face_simple(self, point):
        """
        returns the index of the face that the point is in

        returns None if the point is not in the mesh

        : param point :  the point that you want to locate -- (x, y)

        this is a very simple, look through all the faces search.
        It is slow ( O(N) ), but should be robust
        """
        for i, face in enumerate(self._faces):
            f = self._nodes[face]
            if point_in_poly(f, point):
                return i
        return None

    def build_face_face_connectivity(self):
        """
        builds the face_face_connectivity array:
        essentially giving the neighbors of each triangle
        """        
        num_vertices = self.num_vertices
        num_faces = self.faces.shape[0]
        face_face = np.zeros( (num_faces, num_vertices), dtype=IND_DT )
        face_face += -1 # fill with -1

        # loop through all the triangles to find the matching edges:
        edges = {} # dict to store the edges in 
        for i, face in enumerate(self.faces):
            # loop through edges:
            for j in range(num_vertices):
                edge = (face[j-1], face[j])
                if edge[0] > edge[1]: # sort the node numbers
                    edge = (edge[1], edge[0]) 
                # see if it is already in there
                prev_edge = edges.pop(edge, None)
                if prev_edge is not None:
                    face_num, edge_num = prev_edge
                    face_face[i,j] = face_num
                    face_face[face_num, edge_num] = i
                else:
                    edges[edge] = (i, j)
        self._face_face_connectivity = face_face

    def build_edges(self):
        """
        builds the edges array: all the edges defined by the triangles

        NOTE: arbitrary order -- should the order be preserved?
        """        
        num_vertices = self.num_vertices
        num_faces = self.faces.shape[0]
        face_face = np.zeros( (num_faces, num_vertices), dtype=IND_DT )
        face_face += -1 # fill with -1

        # loop through all the faces to find all the edges:
        edges = set() # use a set so no duplicates
        for i, face in enumerate(self.faces):
            # loop through edges:
            for j in range(num_vertices):
                edge = (face[j-1], face[j])
                if edge[0] > edge[1]: # flip them
                    edge = (edge[1], edge[0]) 
                edges.add(edge)
        self._edges = np.array(list(edges), dtype=IND_DT)


    def save_as_netcdf(self, filepath):
        """
        save the ugrid object as a netcdf file

        :param filepath: path to file you want o save to.
                         An existing one will be clobbered if it already exists.

        follows the convernsion established by the netcdf UGRID working group:

        http://publicwiki.deltares.nl/display/NETCDF/Deltares+CF+proposal+for+Unstructured+Grid+data+model

        """

        from netCDF4 import Dataset as ncDataset
        from netCDF4 import num2date, date2num
        # create a new netcdf file
        nclocal = ncDataset(filepath, mode="w", clobber=True)

        # dimensions:
        # nMesh2_node = 4 ; // nNodes
        # nMesh2_edge = 5 ; // nEdges
        # nMesh2_face = 2 ; // nFaces
        # nMesh2_face_links = 1 ; // nFacePairs

        nclocal.createDimension('num_nodes', len(self.nodes) )
        nclocal.createDimension('num_edges', len(self.edges) )
        nclocal.createDimension('num_faces', len(self.faces) )
        nclocal.createDimension('num_vertices', self.faces.shape[1] )
        nclocal.createDimension('two', 2)

        #mesh topology
        mesh = nclocal.createVariable('mesh', IND_DT, (), )
        mesh.cf_role = "mesh_topology" 
        mesh.long_name = "Topology data of 2D unstructured mesh" 
        mesh.topology_dimension = 2 
        mesh.node_coordinates = "node_lon node_lat" 
        mesh.face_node_connectivity = "mesh_face_nodes" 

        mesh.edge_node_connectivity = "mesh_edge_nodes"  ## attribute required if variables will be defined on edges
        mesh.edge_coordinates = "mesh_edge_lon mesh_edge_lat"  ## optional attribute (requires edge_node_connectivity)
        mesh.face_coordinates = "mesh_face_lon mesh_face_lat" ##  optional attribute
        mesh.face_edge_connectivity = "mesh_face_edges"  ## optional attribute (requires edge_node_connectivity)
        mesh.face_face_connectivity = "mesh_face_links"  ## optional attribute

        face_nodes = nclocal.createVariable("mesh_face_nodes",
                                            IND_DT,
                                            ('num_faces', 'num_vertices'),
                                            )
        face_nodes[:] = self.faces

        face_nodes.cf_role = "face_node_connectivity"
        face_nodes.long_name = "Maps every triangular face to its three corner nodes."
        face_nodes.start_index = 0 ;

        edge_nodes = nclocal.createVariable("mesh_edge_nodes",
                                            IND_DT,
                                            ('num_edges', 'two'),
                                            )
        edge_nodes[:] = self.edges

        edge_nodes.cf_role = "edge_node_connectivity"
        edge_nodes.long_name = "Maps every edge to the two nodes that it connects."
        edge_nodes.start_index = 0 ;

        node_lon = nclocal.createVariable('node_lon',
                                     self._nodes.dtype,
                                     ('num_nodes',),
                                     chunksizes=(len(self.nodes), ),
                                     #zlib=False,
                                     #complevel=0,
                                     )
        node_lon[:] = self.nodes[:,0]
        node_lon.standard_name = "longitude"
        node_lon.long_name = "Longitude of 2D mesh nodes."
        node_lon.units = "degrees_east"
        node_lat = nclocal.createVariable('node_lat',
                                     self._nodes.dtype,
                                     ('num_nodes',),
                                     chunksizes=(len(self.nodes), ),
                                     #zlib=False,
                                     #complevel=0,
                                     )
        node_lat[:] = self.nodes[:,1]
        node_lat.standard_name = "latitude"
        node_lat.long_name = "Latitude of 2D mesh nodes."
        node_lat.units = "degrees_north"

        # // Mesh node coordinates
        # double Mesh2_node_x(nMesh2_node) ;
        #         Mesh2_node_x:standard_name = "longitude" ;
        #         Mesh2_node_x:long_name = "Longitude of 2D mesh nodes." ;
        #         Mesh2_node_x:units = "degrees_east" ;
        nclocal.sync()

## this code moved here to fix circular import issues:
##  reading code needs the UGrid object, and UGRid object needs the reading code...
def open_cf_todict( filename ):
    """
    read a netcdf or opendap url, and load it into a dict of ugrid objects.
    """
    import netCDF4
    nc = netCDF4.Dataset(filename, 'r')
    ncvars = nc.variables
    meshes = {}
    for varname in ncvars.iterkeys():
        try:
            meshname = ncvars[varname].getncattr('mesh')
        except AttributeError:
            meshname = None
        if (meshname != None) and (meshname not in set(meshes.viewkeys())):
            meshatt_names = ncvars[meshname].ncattrs()
            
            ## Make sure that this mesh style is supported in this codebase
            meshatts = {}
            for attname in meshatt_names:
                meshatts[attname] = ncvars[meshname].getncattr(attname)
            assert meshatts['cf_role'] == 'mesh_topology'
            #if meshatts['topology_dimension'] != '2':
            #    raise ValueError("Unfortuntely, only meshes that are unstructured in 2 dimensions are supported")
            
            ## Grab node coordinates from mesh meta-variable, and pull out the coord values
            node_coordinates = meshatts.get('node_coordinates', None)
            num_nodes = len(nc.dimensions['n'+meshname+'_node'])
            if node_coordinates == None:
                raise AttributeError("Unstructured meshes must include node coordinates, specified with the 'node_coordinates' attribute")
            node_coordinates = node_coordinates.split(" ")
            nodes = np.empty((num_nodes, 2), dtype=np.float64)
            for coord in node_coordinates:
                units = ncvars[coord].units
                if 'north' in units:
                    nodes[:,1] = ncvars[coord][:]
                elif ('east' in units) or ('west' in units):
                    nodes[:,0] = ncvars[coord][:]
                else:
                    raise AttributeError("Node coordinates don't contain 'units' attribute!") 

            ## Grab Face and Edge node connectivity arrays
            face_node_conn_name = meshatts.get('face_node_connectivity', None)
            edge_node_conn_name = meshatts.get('edge_node_connectivity', None)
            faces = []
            edges = []
            if face_node_conn_name != None:
                faces = ncvars[face_node_conn_name][:,:]
                # if [3,nodes] instead of [nodes,3], transpose the array
                # logic below will fail for 3 element grids
                if faces.shape[0] == 3:
                    faces = faces.T
            index_base = np.min(np.min(faces))
            if index_base  >= 1:
                faces = faces - index_base
            try:
                if edge_node_conn_name != None:
                    edges = ncvars[edge_node_conn_name][:,:]
                    index_base = np.min(np.min(edges))
                    if index_base >= 1:
                        edges = edges - index_base
            except:
                pass #TODO: Generate edge node topology if none exists, perhaps optional
  
            ## Add to dictionary of meshes
            meshes[meshname] = UGrid(nodes, faces, edges)
    return meshes # Return dictionary of ugrid objects
    






