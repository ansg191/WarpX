# Copyright 2017-2023 The WarpX Community
#
# This file is part of WarpX.
#
# Authors: David Grote, Roelof Groenewald
#
# License: BSD-3-Clause-LBNL

import numpy as np

from ._libwarpx import libwarpx


class ParticleContainerWrapper(object):
    """Wrapper around particle containers.
    This provides a convenient way to query and set data in the particle containers.

    Parameters
    ----------
    species_name: string
        The name of the species to be accessed.
    """

    def __init__(self, species_name):
        self.name = species_name

        # grab the desired particle container
        mypc = libwarpx.warpx.multi_particle_container()
        self.particle_container = mypc.get_particle_container_from_name(self.name)

    def add_particles(self, x=None, y=None, z=None, ux=None, uy=None,
                      uz=None, w=None, unique_particles=True, **kwargs):
        '''
        A function for adding particles to the WarpX simulation.

        Parameters
        ----------

        species_name     : str
            The type of species for which particles will be added

        x, y, z          : arrays or scalars
            The particle positions (default = 0.)

        ux, uy, uz       : arrays or scalars
            The particle momenta (default = 0.)

        w                : array or scalars
            Particle weights (default = 0.)

        unique_particles : bool
            Whether the particles are unique or duplicated on several processes
            (default = True)

        kwargs           : dict
            Containing an entry for all the extra particle attribute arrays. If
            an attribute is not given it will be set to 0.
        '''

        # --- Get length of arrays, set to one for scalars
        lenx = np.size(x)
        leny = np.size(y)
        lenz = np.size(z)
        lenux = np.size(ux)
        lenuy = np.size(uy)
        lenuz = np.size(uz)
        lenw = np.size(w)

        # --- Find the max length of the parameters supplied
        maxlen = 0
        if x is not None:
            maxlen = max(maxlen, lenx)
        if y is not None:
            maxlen = max(maxlen, leny)
        if z is not None:
            maxlen = max(maxlen, lenz)
        if ux is not None:
            maxlen = max(maxlen, lenux)
        if uy is not None:
            maxlen = max(maxlen, lenuy)
        if uz is not None:
            maxlen = max(maxlen, lenuz)
        if w is not None:
            maxlen = max(maxlen, lenw)

        # --- Make sure that the lengths of the input parameters are consistent
        assert x is None or lenx==maxlen or lenx==1, "Length of x doesn't match len of others"
        assert y is None or leny==maxlen or leny==1, "Length of y doesn't match len of others"
        assert z is None or lenz==maxlen or lenz==1, "Length of z doesn't match len of others"
        assert ux is None or lenux==maxlen or lenux==1, "Length of ux doesn't match len of others"
        assert uy is None or lenuy==maxlen or lenuy==1, "Length of uy doesn't match len of others"
        assert uz is None or lenuz==maxlen or lenuz==1, "Length of uz doesn't match len of others"
        assert w is None or lenw==maxlen or lenw==1, "Length of w doesn't match len of others"
        for key, val in kwargs.items():
            assert np.size(val)==1 or len(val)==maxlen, f"Length of {key} doesn't match len of others"

        # --- Broadcast scalars into appropriate length arrays
        # --- If the parameter was not supplied, use the default value
        if lenx == 1:
            x = np.full(maxlen, (x or 0.))
        if leny == 1:
            y = np.full(maxlen, (y or 0.))
        if lenz == 1:
            z = np.full(maxlen, (z or 0.))
        if lenux == 1:
            ux = np.full(maxlen, (ux or 0.))
        if lenuy == 1:
            uy = np.full(maxlen, (uy or 0.))
        if lenuz == 1:
            uz = np.full(maxlen, (uz or 0.))
        if lenw == 1:
            w = np.full(maxlen, (w or 0.))
        for key, val in kwargs.items():
            if np.size(val) == 1:
                kwargs[key] = np.full(maxlen, val)

        # --- The number of built in attributes
        # --- The three velocities
        built_in_attrs = 3
        if libwarpx.geometry_dim == 'rz':
            # --- With RZ, there is also theta
            built_in_attrs += 1

        # --- The number of extra attributes (including the weight)
        nattr = self.particle_container.num_real_comps() - built_in_attrs
        attr = np.zeros((maxlen, nattr))
        attr[:,0] = w

        # --- Note that the velocities are handled separately and not included in attr
        # --- (even though they are stored as attributes in the C++)
        for key, vals in kwargs.items():
            attr[:,self.particle_container.get_comp_index(key) - built_in_attrs] = vals

        nattr_int = 0
        attr_int = np.empty([0],  dtype=np.int32)

        # TODO: expose ParticleReal through pyAMReX
        # and cast arrays to the correct types, before calling add_n_particles
        # x = x.astype(self._numpy_particlereal_dtype, copy=False)
        # y = y.astype(self._numpy_particlereal_dtype, copy=False)
        # z = z.astype(self._numpy_particlereal_dtype, copy=False)
        # ux = ux.astype(self._numpy_particlereal_dtype, copy=False)
        # uy = uy.astype(self._numpy_particlereal_dtype, copy=False)
        # uz = uz.astype(self._numpy_particlereal_dtype, copy=False)

        self.particle_container.add_n_particles(
            0, x.size, x, y, z, ux, uy, uz,
            nattr, attr, nattr_int, attr_int, unique_particles
        )

    def get_particle_count(self, local=False):
        '''
        Get the number of particles of this species in the simulation.

        Parameters
        ----------

        local        : bool
            If True the particle count on this processor will be returned.
            Default False.

        Returns
        -------

        int
            An integer count of the number of particles
        '''
        return self.particle_container.total_number_of_particles(True, local)
    nps = property(get_particle_count)

    def add_real_comp(self, pid_name, comm=True):
        '''
        Add a real component to the particle data array.

        Parameters
        ----------

        pid_name       : str
            Name that can be used to identify the new component

        comm           : bool
            Should the component be communicated
        '''
        self.particle_container.add_real_comp(pid_name, comm)

    def get_particle_structs(self, level):
        '''
        This returns a list of numpy arrays containing the particle struct data
        on each tile for this process. The particle data is represented as a structured
        numpy array and contains the particle 'x', 'y', 'z', and 'idcpu'.

        The data for the numpy arrays are not copied, but share the underlying
        memory buffer with WarpX. The numpy arrays are fully writeable.

        Parameters
        ----------

        level        : int
            The refinement level to reference

        Returns
        -------

        List of numpy arrays
            The requested particle struct data
        '''
        particle_data = []
        for pti in libwarpx.libwarpx_so.WarpXParIter(self.particle_container, level):
            aos_arr = np.array(pti.aos(), copy=False)
            particle_data.append(aos_arr)
        return particle_data

    def get_particle_arrays(self, comp_name, level):
        '''
        This returns a list of numpy arrays containing the particle array data
        on each tile for this process.

        The data for the numpy arrays are not copied, but share the underlying
        memory buffer with WarpX. The numpy arrays are fully writeable.

        Parameters
        ----------

        comp_name      : str
            The component of the array data that will be returned

        level        : int
            The refinement level to reference

        Returns
        -------

        List of numpy arrays
            The requested particle array data
        '''
        comp_idx = self.particle_container.get_comp_index(comp_name)

        data_array = []
        for pti in libwarpx.libwarpx_so.WarpXParIter(self.particle_container, level):
            soa = pti.soa()
            data_array.append(np.array(soa.GetRealData(comp_idx), copy=False))
        return data_array

    def get_particle_id(self, level=0):
        '''

        Return a list of numpy arrays containing the particle 'id'
        numbers on each tile.

        '''
        structs = self.get_particle_structs(level)
        return [libwarpx.amr.unpack_ids(struct['cpuid']) for struct in structs]

    def get_particle_cpu(self, level=0):
        '''

        Return a list of numpy arrays containing the particle 'cpu'
        numbers on each tile.

        '''
        structs = self.get_particle_structs(level)
        return [libwarpx.amr.unpack_cpus(struct['cpuid']) for struct in structs]

    def get_particle_x(self, level=0):
        '''

        Return a list of numpy arrays containing the particle 'x'
        positions on each tile.

        '''
        structs = self.get_particle_structs(level)
        if libwarpx.geometry_dim == '3d' or libwarpx.geometry_dim == '2d':
            return [struct['x'] for struct in structs]
        elif libwarpx.geometry_dim == 'rz':
            return [struct['x']*np.cos(theta) for struct, theta in zip(structs, self.get_particle_theta())]
        elif libwarpx.geometry_dim == '1d':
            raise Exception('get_particle_x: There is no x coordinate with 1D Cartesian')
    xp = property(get_particle_x)

    def get_particle_y(self, level=0):
        '''

        Return a list of numpy arrays containing the particle 'y'
        positions on each tile.

        '''
        structs = self.get_particle_structs(level)
        if libwarpx.geometry_dim == '3d':
            return [struct['y'] for struct in structs]
        elif libwarpx.geometry_dim == 'rz':
            return [struct['x']*np.sin(theta) for struct, theta in zip(structs, self.get_particle_theta())]
        elif libwarpx.geometry_dim == '1d' or libwarpx.geometry_dim == '2d':
            raise Exception('get_particle_y: There is no y coordinate with 1D or 2D Cartesian')
    yp = property(get_particle_y)

    def get_particle_r(self, level=0):
        '''

        Return a list of numpy arrays containing the particle 'r'
        positions on each tile.

        '''
        structs = self.get_particle_structs(level)
        if libwarpx.geometry_dim == 'rz':
            return [struct['x'] for struct in structs]
        elif libwarpx.geometry_dim == '3d':
            return [np.sqrt(struct['x']**2 + struct['y']**2) for struct in structs]
        elif libwarpx.geometry_dim == '2d' or libwarpx.geometry_dim == '1d':
            raise Exception('get_particle_r: There is no r coordinate with 1D or 2D Cartesian')
    rp = property(get_particle_r)

    def get_particle_theta(self, level=0):
        '''

        Return a list of numpy arrays containing the particle
        theta on each tile.

        '''
        if libwarpx.geometry_dim == 'rz':
            return self.get_particle_arrays('theta', level)
        elif libwarpx.geometry_dim == '3d':
            structs = self.get_particle_structs(level)
            return [np.arctan2(struct['y'], struct['x']) for struct in structs]
        elif libwarpx.geometry_dim == '2d' or libwarpx.geometry_dim == '1d':
            raise Exception('get_particle_theta: There is no theta coordinate with 1D or 2D Cartesian')
    thetap = property(get_particle_theta)

    def get_particle_z(self, level=0):
        '''

        Return a list of numpy arrays containing the particle 'z'
        positions on each tile.

        '''
        structs = self.get_particle_structs(level)
        if libwarpx.geometry_dim == '3d':
            return [struct['z'] for struct in structs]
        elif libwarpx.geometry_dim == 'rz' or libwarpx.geometry_dim == '2d':
            return [struct['y'] for struct in structs]
        elif libwarpx.geometry_dim == '1d':
            return [struct['x'] for struct in structs]
    zp = property(get_particle_z)

    def get_particle_weight(self, level=0):
        '''

        Return a list of numpy arrays containing the particle
        weight on each tile.

        '''
        return self.get_particle_arrays('w', level)
    wp = property(get_particle_weight)

    def get_particle_ux(self, level=0):
        '''

        Return a list of numpy arrays containing the particle
        x momentum on each tile.

        '''
        return self.get_particle_arrays('ux', level)
    uxp = property(get_particle_ux)

    def get_particle_uy(self, level=0):
        '''

        Return a list of numpy arrays containing the particle
        y momentum on each tile.

        '''
        return self.get_particle_arrays('uy', level)
    uyp = property(get_particle_uy)

    def get_particle_uz(self, level=0):
        '''

        Return a list of numpy arrays containing the particle
        z momentum on each tile.

        '''

        return self.get_particle_arrays('uz', level)
    uzp = property(get_particle_uz)

    def get_species_charge_sum(self, local=False):
        '''
        Returns the total charge in the simulation due to the given species.

        Parameters
        ----------

        local          : bool
            If True return total charge per processor
        '''
        raise NotImplementedError()
        return self.libwarpx_so.warpx_sumParticleCharge(
            ctypes.c_char_p(species_name.encode('utf-8')), local
        )

    def getex(self):
        raise NotImplementedError('Particle E fields not supported')
    ex = property(getex)

    def getey(self):
        raise NotImplementedError('Particle E fields not supported')
    ey = property(getey)

    def getez(self):
        raise NotImplementedError('Particle E fields not supported')
    ez = property(getez)

    def getbx(self):
        raise NotImplementedError('Particle B fields not supported')
    bx = property(getbx)

    def getby(self):
        raise NotImplementedError('Particle B fields not supported')
    by = property(getby)

    def getbz(self):
        raise NotImplementedError('Particle B fields not supported')
    bz = property(getbz)


class ParticleBoundaryBufferWrapper(object):
    """Wrapper around particle boundary buffer containers.
    This provides a convenient way to query data in the particle boundary
    buffer containers.
    """

    def __init__(self):
        self.particle_buffer = libwarpx.warpx.get_particle_boundary_buffer()

    def get_particle_boundary_buffer_size(self, species_name, boundary, local=False):
        '''
        This returns the number of particles that have been scraped so far in the simulation
        from the specified boundary and of the specified species.

        Parameters
        ----------

        species_name   : str
            Return the number of scraped particles of this species

        boundary       : str
            The boundary from which to get the scraped particle data in the
            form x/y/z_hi/lo

        local          : bool
            Whether to only return the number of particles in the current
            processor's buffer
        '''
        return self.particle_buffer.get_num_particles_in_container(
            species_name, self._get_boundary_number(boundary),
            local=local
        )

    def get_particle_boundary_buffer_structs(self, species_name, boundary, level):
        '''
        This returns a list of numpy arrays containing the particle struct data
        for a species that has been scraped by a specific simulation boundary. The
        particle data is represented as a structured numpy array and contains the
        particle 'x', 'y', 'z', and 'idcpu'.

        The data for the numpy arrays are not copied, but share the underlying
        memory buffer with WarpX. The numpy arrays are fully writeable.

        Parameters
        ----------

        species_name : str
            The species name that the data will be returned for

        boundary     : str
            The boundary from which to get the scraped particle data in the
            form x/y/z_hi/lo or eb.

        level        : int
            Which AMR level to retrieve scraped particle data from.
        '''

        particles_per_tile = _LP_c_int()
        num_tiles = ctypes.c_int(0)
        data = self.libwarpx_so.warpx_getParticleBoundaryBufferStructs(
                ctypes.c_char_p(species_name.encode('utf-8')),
                self._get_boundary_number(boundary), level,
                ctypes.byref(num_tiles), ctypes.byref(particles_per_tile)
        )

        particle_data = []
        for i in range(num_tiles.value):
            if particles_per_tile[i] == 0:
                continue
            arr = self._array1d_from_pointer(data[i], self._p_dtype, particles_per_tile[i])
            particle_data.append(arr)

        _libc.free(particles_per_tile)
        _libc.free(data)
        return particle_data

    def get_particle_boundary_buffer(self, species_name, boundary, comp_name, level):
        '''
        This returns a list of numpy arrays containing the particle array data
        for a species that has been scraped by a specific simulation boundary.

        The data for the numpy arrays are not copied, but share the underlying
        memory buffer with WarpX. The numpy arrays are fully writeable.

        Parameters
        ----------

            species_name   : str
                The species name that the data will be returned for.

            boundary       : str
                The boundary from which to get the scraped particle data in the
                form x/y/z_hi/lo or eb.

            comp_name      : str
                The component of the array data that will be returned. If
                "step_scraped" the special attribute holding the timestep at
                which a particle was scraped will be returned.

            level          : int
                Which AMR level to retrieve scraped particle data from.
        '''
        part_container = self.particle_buffer.get_particle_container(
            species_name, self._get_boundary_number(boundary)
        )
        data_array = []
        if comp_name == 'step_scraped':
            # the step scraped is always the final integer component
            comp_idx = part_container.num_int_comps() - 1
            for ii, pti in enumerate(libwarpx.libwarpx_so.BoundaryBufferParIter(part_container, level)):
                soa = pti.soa()
                data_array.append(np.array(soa.GetIntData(comp_idx), copy=False))
        else:
            mypc = libwarpx.warpx.multi_particle_container()
            sim_part_container_wrapper = mypc.get_particle_container_from_name(species_name)
            comp_idx = sim_part_container_wrapper.get_comp_index(comp_name)
            for ii, pti in enumerate(libwarpx.libwarpx_so.BoundaryBufferParIter(part_container, level)):
                soa = pti.soa()
                data_array.append(np.array(soa.GetRealData(comp_idx), copy=False))

        return data_array

    def clear_buffer(self):
        '''

        Clear the buffer that holds the particles lost at the boundaries.

        '''
        self.particle_buffer.clear_particles()

    def _get_boundary_number(self, boundary):
        '''

        Utility function to find the boundary number given a boundary name.

        Parameters
        ----------

        boundary       : str
            The boundary from which to get the scraped particle data. In the
            form x/y/z_hi/lo or eb.

        Returns
        -------
        int
            Integer index in the boundary scraper buffer for the given boundary.
        '''
        if libwarpx.geometry_dim == '3d':
            dimensions = {'x' : 0, 'y' : 1, 'z' : 2}
        elif libwarpx.geometry_dim == '2d' or libwarpx.geometry_dim == 'rz':
            dimensions = {'x' : 0, 'z' : 1}
        elif libwarpx.geometry_dim == '1d':
            dimensions = {'z' : 0}
        else:
            raise RuntimeError(f"Unknown simulation geometry: {libwarpx.geometry_dim}")

        if boundary != 'eb':
            boundary_parts = boundary.split("_")
            dim_num = dimensions[boundary_parts[0]]
            if boundary_parts[1] == 'lo':
                side = 0
            elif boundary_parts[1] == 'hi':
                side = 1
            else:
                raise RuntimeError(f'Unknown boundary specified: {boundary}')
            boundary_num = 2 * dim_num + side
        else:
            if libwarpx.geometry_dim == '3d':
                boundary_num = 6
            elif libwarpx.geometry_dim == '2d' or libwarpx.geometry_dim == 'rz':
                boundary_num = 4
            elif libwarpx.geometry_dim == '1d':
                boundary_num = 2
            else:
                raise RuntimeError(f"Unknown simulation geometry: {libwarpx.geometry_dim}")

        return boundary_num
