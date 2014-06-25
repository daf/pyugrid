#!/usr/bin/env python

"""
code to read the netcdf unstructured grid standard:

https://github.com/ugrid-conventions/ugrid-conventions/

This code is called by the UGrid class to load inot a UGRID object.

"""

import numpy as np

from .data_set import DataSet

def find_mesh_names( nc ):
    """
    find all the meshes in an open netcCDF4.DataSet
    
    :param nc: the netCDF4 Dataset object to look for mesh names in

    NOTE: checks for 2-d topology_dimension
    """
    mesh_names = []
    for varname in nc.variables.iterkeys():
        if is_valid_mesh(nc, varname):
                    mesh_names.append(varname)
    return mesh_names            

def is_valid_mesh(nc, varname):
    """
    determine if the given variable name is a valid mesh definition
    
    :param nc: a netCDF4 Dataset to check

    :param varname: name of the candidate mesh variable
    
    """
    try:
        mesh_var = nc.variables[varname]
    except KeyError:
        return False
    try:
        if  ( mesh_var.cf_role.strip() == 'mesh_topology'  and
              int( mesh_var.topology_dimension ) == 2
              ):
            return True
    except AttributeError:
            # not a valid mesh variable
        return False

## defining properties of various connectivity arrays
##   so that the same code can load all of them.
grid_defs = [{'grid_attr':'faces', # attribute name in UGrid object
              'role': 'face_node_connectivity', # attribute name in mesh variable
              'num_ind': 3, # number of indexes expect (3 for faces, 2 for segments)
              },
             {'grid_attr':'face_face_connectivity', # attribute name in UGrid object
              'role': 'face_face_connectivity', # attribute name in mesh variable
              'num_ind': 3, # number of indexes expect (3 for faces, 2 for segments)
              },
             {'grid_attr':'boundaries', # attribute name in UGrid object
              'role': 'boundary_node_connectivity', # attribute name in mesh variable
              'num_ind': 2, # number of indexes expect (3 for faces, 2 for segments)
              },
             {'grid_attr':'edges', # attribute name in UGrid object
              'role': 'edge_node_connectivity', # attribute name in mesh variable
              'num_ind': 2, # number of indexes expect (3 for faces, 2 for segments)
              },

             ]
# defintions for various coordinate arrays
coord_defs = [ {'grid_attr':'nodes', # attribute name in UGrid object
                'role': 'node_coordinates', # attribute name in mesh variable
                'required': True, # is this required?
               },
               {'grid_attr':'face_coordinates', # attribute name in UGrid object
                'role': 'face_coordinates', # attribute name in mesh variable
                'required': False, # is this required?
               },
               {'grid_attr':'edge_coordinates', # attribute name in UGrid object
                'role': 'edge_coordinates', # attribute name in mesh variable
                'required': False, # is this required?
               },
               {'grid_attr':'boundary_coordinates', # attribute name in UGrid object
                'role': 'boundary_coordinates', # attribute name in mesh variable
                'required': False, # is this required?
               }
             ]


def load_grid_from_nc(filename, grid, mesh_name=None):
    """
    loads UGrid object from a netcdf file, adding the data
    to the passed-in grid object.

    It will load the mesh specified, or look
    for the first one it finds if none is specified

    :param filename: filename or OpenDAP url of dataset.
    
    :param grid: ther gird object to put the mesh and data into.
    :type grid: UGrid object.

    :param mesh_name=None: name of the mesh to load
    :type mesh_name: string

    NOTE: passing the UGrid object in to avoid circular references,
    while keeping the netcdf reading code in its own file.
    """

    import netCDF4
    nc = netCDF4.Dataset(filename, 'r')
    ncvars = nc.variables

    ## get the mesh_name
    if mesh_name is None:
        # find the mesh
        meshes = find_mesh_names( nc )
        if len(meshes) == 0:
            raise ValueError("There are no standard-conforming meshes in %s"%filename)
        if len(meshes) > 1:
            raise ValueError("There is more than one mesh in the file: %s"%(meshes,) )
        mesh_name = meshes[0]
    else:
        if not is_valid_mesh(nc, mesh_name):
            raise ValueError("Mesh: %s is not in %s"%(mesh_name, filename))
    
    grid.mesh_name = mesh_name

    mesh_var = ncvars[mesh_name]


    ## Load the coordinate variables
    for defs in coord_defs:
        try:
            coord_names = mesh_var.getncattr(defs['role']).strip().split()
            coord_vars = [nc.variables[name] for name in coord_names]
        except AttributeError:
            if defs['required']:
                raise ValueError("Mesh variable must include %s attribute"%defs['role'])
            continue
        except KeyError:
            raise ValueError("file must include %s variables for %s named in mesh variable"%(coord_names, defs['role']))

        coord_vars = [nc.variables[name] for name in coord_names]
        num_node = len(coord_vars[0])
        nodes = np.empty((num_node, 2), dtype=np.float64)
        for var in coord_vars:
            try:
                standard_name = var.standard_name
            except AttributeError:
                raise ValueError("%s variable doesn't contain standard_name attribute"%var)
            if standard_name == 'latitude':
                nodes[:,1] = var[:]
            elif standard_name == 'longitude':
                nodes[:,0] = var[:]
            else:
                raise ValueError('Node coordinates standard_name is neither "longitude" nor "latitude" ') 
        
        setattr(grid, defs['grid_attr'], nodes)


    ## Load assorted connectivity arrays
    for defs in grid_defs:
        try:
            var = nc.variables[mesh_var.getncattr(defs['role'])]
            array = var[:,:]
            # if [3,faces] instead of [faces,3], transpose the array
            # logic below will fail for 3 edge grids
            if array.shape[0] == defs['num_ind']:
                array = array.T
            try:
                start_index = var.start_index
            except AttributeError:
                start_index = 0
            if start_index  >= 1:
                array -= start_index
                # check for flag value
                try:
                    ## fixme: this won't work for more than one flag value
                    flag_value = var.flag_values
                    array[array==flag_value-start_index] = flag_value
                except AttributeError:
                    pass
            setattr(grid, defs['grid_attr'], array)
        except KeyError:
            pass ## OK not to have this...

    ## Load the associated data:

    ## look for data arrays -- they should have a "location" attribute
    for name, var in nc.variables.items():

        #Data Arrays should have "location" and "mesh" attributes
        try:
            location = var.location
            # the mesh attribute should match the mesh we're loading:
            if var.mesh != mesh_name:
                continue
        except AttributeError:
            continue

        print "found:", name, location

        #get the attributes
        ## fixme: is there a way to get the attributes a dict directly?
        attributes = { n: var.getncattr(n) for n in var.ncattrs() if n not in ('location' 'coordinates')}

        # trick with the name: fixme: is this a good idea?
        name = name.lstrip(mesh_name).lstrip('_')
        ds = DataSet(name, data=var[:], location=location, attributes=attributes)

        grid.add_data(ds)



    # ### NEED TO LOAD:
    #              face_edge_connectivity=None,
    #              edge_coordinates=None,
    #              face_coordinates=None,
    #              boundary_coordinates=None,

    ## time to load data!
