"""
Ordination results format (:mod:`skbio.io.ordres`)
==================================================

.. currentmodule:: skbio.io.ordres

The ordination results file format (``ordres``) stores the results of an
ordination method in a human-readable, text-based format. The format supports
storing the results of various ordination methods available in scikit-bio,
including (but not necessarily limited to) PCoA, CA, RDA, and CCA.

Format Specification
--------------------
The format is text-based, consisting of six attributes that describe the
ordination results:

- ``Eigvals``
- ``Proportion explained``
- ``Species``
- ``Site``
- ``Biplot``
- ``Site constraints``

The attributes in the file *must* be in this order.

Each attribute is defined in its own section of the file, where sections are
separated by a blank (or whitespace-only) line. Each attribute begins with a
header line, which contains the attribute's name (as listed above), followed by
a tab character, followed by one or more tab-separated dimensions that describe
the shape of the attribute.

The attribute's data follows its header line, and is stored in tab-separated
format.

TODO add descriptions of each attribute

An example of this file format might look like::

    Eigvals<tab>2
    0.096<tab>0.040

    Proportion explained<tab>2
    0.512<tab>0.488

    Species<tab>3<tab>2
    Species1<tab>0.408<tab>0.069
    Species2<tab>-0.115<tab>-0.299
    Species3<tab>-0.309<tab>0.187

    Site<tab>3<tab>2
    Site1<tab>-0.848<tab>0.882
    Site2<tab>-0.220<tab>-1.344
    Site3<tab>1.666<tab>0.470

    Biplot<tab>4<tab>3
    0.422<tab>-0.559<tab>-0.713
    0.988<tab>0.150<tab>-0.011
    -0.556<tab>0.817<tab>0.147
    -0.404<tab>-0.905<tab>-0.127

    Site constraints<tab>3<tab>2
    Site1<tab>-0.848<tab>0.882
    Site2<tab>-0.220<tab>-1.344
    Site3<tab>1.666<tab>0.470

If a given result attribute is not present (e.g. ``Biplot``), it should still
be defined and declare its dimensions as 0::

    Biplot<tab>0<tab>0

"""

# ----------------------------------------------------------------------------
# Copyright (c) 2013--, scikit-bio development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------

from __future__ import absolute_import, division, print_function

import numpy as np

from skbio.stats.ordination import OrdinationResults
from skbio.io import (register_reader, register_writer, register_sniffer,
                      OrdResFormatError)


@register_sniffer('ordres')
def _ordres_sniffer(fh):
    # TODO finish implementation
    return False, {}


@register_reader('ordres', OrdinationResults)
def _ordres_to_ordination_results(fh):
    eigvals = _parse_eigvals(fh)
    _check_empty_line(fh)
    prop_expl = _parse_proportion_explained(fh)

    if prop_expl is not None:
        if len(prop_expl) != len(eigvals):
            raise OrdResFormatError(
                "There should be as many proportion explained values as "
                "eigvals: %d != %d" % (len(prop_expl), len(eigvals)))

    _check_empty_line(fh)
    species, species_ids = _parse_coords(fh, 'Species')

    if species is not None:
        if len(species[0]) != len(eigvals):
            raise OrdResFormatError(
                "There should be as many coordinates per species as eigvals: "
                "%d != %d" % (len(species[0]), len(eigvals)))

    _check_empty_line(fh)
    site, site_ids = _parse_coords(fh, 'Site')

    if site is not None:
        if len(site[0]) != len(eigvals):
            raise OrdResFormatError(
                "There should be as many coordinates per site as eigvals: "
                "%d != %d" % (len(site[0]), len(eigvals)))

    _check_empty_line(fh)
    biplot = _parse_biplot(fh)
    _check_empty_line(fh)
    cons, cons_ids = _parse_coords(fh, 'Site constraints')

    if cons_ids is not None and site_ids is not None:
        if cons_ids != site_ids:
            raise OrdResFormatError(
                "Site constraints ids and site ids must be equal: %s != %s" %
                (cons_ids, site_ids))

    return OrdinationResults(
        eigvals=eigvals, species=species, site=site, biplot=biplot,
        site_constraints=cons, proportion_explained=prop_expl,
        species_ids=species_ids, site_ids=site_ids)


def _parse_eigvals(fh):
    # The first line should contain the Eigvals header:
    # Eigvals<tab>NumEigvals
    header = next(fh).strip().split('\t')
    if len(header) != 2 or header[0] != 'Eigvals':
        raise OrdResFormatError("Eigvals header not found.")

    # Parse how many eigvals we are waiting for
    num_eigvals = int(header[1])
    if num_eigvals == 0:
        raise OrdResFormatError("At least one eigval should be present.")

    # Parse the eigvals, present on the next line
    # Eigval_1<tab>Eigval_2<tab>Eigval_3<tab>...
    eigvals = np.asarray(next(fh).strip().split('\t'), dtype=np.float64)
    if len(eigvals) != num_eigvals:
        raise OrdResFormatError("Expected %d eigvals, but found %d." %
                                (num_eigvals, len(eigvals)))
    return eigvals


def _check_empty_line(fh):
    """Check that the next line in `fh` is empty or whitespace-only."""
    if next(fh).strip():
        raise OrdResFormatError("Expected an empty line.")


def _parse_proportion_explained(fh):
    # Parse the proportion explained header:
    # Proportion explained<tab>NumPropExpl
    header = next(fh).strip().split('\t')
    if len(header) != 2 or header[0] != 'Proportion explained':
        raise OrdResFormatError("Proportion explained header not found.")

    # Parse how many prop expl values are we waiting for
    num_prop_expl = int(header[1])
    if num_prop_expl == 0:
        # The ordination method didn't generate the prop explained vector
        # set it to None
        prop_expl = None
    else:
        # Parse the line with the proportion explained values
        prop_expl = np.asarray(next(fh).strip().split('\t'), dtype=np.float64)
        if len(prop_expl) != num_prop_expl:
            raise OrdResFormatError(
                "Expected %d proportion explained values, but found %d." %
                (num_prop_expl, len(prop_expl)))
    return prop_expl


def _parse_coords(fh, header_id):
    """Parse a coordinates section of `fh` identified by `header_id`."""
    # Parse the coords header
    header = next(fh).strip().split('\t')
    if len(header) != 3 or header[0] != header_id:
        raise OrdResFormatError("%s header not found." % header_id)

    # Parse the dimensions of the coord matrix
    rows = int(header[1])
    cols = int(header[2])

    if rows == 0 and cols == 0:
        # The ordination method didn't generate the coords for 'header'
        # Set the results to None
        coords = None
        ids = None
    elif (rows == 0 and cols != 0) or (rows != 0 and cols == 0):
        # Both dimensions should be 0 or none of them are zero
        raise OrdResFormatError("One dimension of %s is 0: %d x %d" %
                                (header, rows, cols))
    else:
        # Parse the coords
        coords = np.empty((rows, cols), dtype=np.float64)
        ids = []
        for i in range(rows):
            # Parse the next row of data
            vals = next(fh).strip().split('\t')
            # The +1 comes from the row header (which contains the row id)
            if len(vals) != cols + 1:
                raise OrdResFormatError(
                    "Expected %d values, but found %d in row %d." %
                    (cols, len(vals) - 1, i))
            ids.append(vals[0])
            coords[i, :] = np.asarray(vals[1:], dtype=np.float64)
    return coords, ids


def _parse_biplot(fh):
    # Parse the biplot header
    header = next(fh).strip().split('\t')
    if len(header) != 3 or header[0] != 'Biplot':
        raise OrdResFormatError("Biplot header not found.")

    # Parse the dimensions of the Biplot matrix
    rows = int(header[1])
    cols = int(header[2])

    if rows == 0 and cols == 0:
        # The ordination method didn't generate the biplot matrix
        # Set the results to None
        biplot = None
    elif (rows == 0 and cols != 0) or (rows != 0 and cols == 0):
        # Both dimensions should be 0 or none of them are zero
        raise OrdResFormatError("One dimension of %s is 0: %d x %d" %
                                (header, rows, cols))
    else:
        # Parse the biplot matrix
        biplot = np.empty((rows, cols), dtype=np.float64)
        for i in range(rows):
            # Parse the next row of data
            vals = next(fh).strip().split('\t')
            if len(vals) != cols:
                raise OrdResFormatError(
                    "Expected %d values, but found %d in row %d." %
                    (cols, len(vals), i))
            biplot[i, :] = np.asarray(vals, dtype=np.float64)
    return biplot


@register_writer('ordres', OrdinationResults)
def _ordination_results_to_ordres(obj, fh):
    pass
