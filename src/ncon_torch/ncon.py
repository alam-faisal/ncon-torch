"""A module for the function ncon, which does contractions of several tensors.
"""
from collections.abc import Iterable
import numpy as np
from .backend import con, trace, permute, expand_dims

def ncon(L, v, order=None, forder=None, check_indices=True):
    """Contract a tensor network.

    Arguments:
        L = [A1, A2, ..., Ap]: A list of tensors to contract.

        v = [v1, v2, ..., vp]: A list of lists of indices e.g. v1 = [3, 4, -1]
        labels the three indices of tensor A1, with -1 indicating an
        uncontracted index (open leg) and 3 and 4 being the contracted indices.

        order: Optional. If present, contains a list of all contracted indices
        - if not [1, 2, 3, 4, ...] by default. This is the order in which they
        are contracted. If indices are not integers, order must be provided.

        forder: Optional. If present, contains the final ordering of the
        uncontracted indices - if not, [-1, -2, ...] by default. If indices are
        not integers, forder must be provided.

    Returns:
        A single tensor that is the result of the contraction.

    There is some leeway in the way the inputs are given. For example, instead
    of giving a list of tensors as the first argument one can give some
    different iterable of tensors, such as a tuple, or a single tensor by
    itself (anything that has the attribute "shape" will be considered a
    tensor).

    Indices can be integers or other objects that aren't iterable, with
    exception of strings which are allowed. With integers, we assume that
    positive indices are contracted and negative indices are uncontracted, and
    the contraction order and final ordering follow the ordering of the
    integers, unless the caller specifies otherwise. With any other types of
    index objects (e.g. strings) we assume that any repeated indices are
    contracted, and the contraction and final order have to be provided by the
    caller.
    """
    # Prepare the arguments into a standard format, with defaults filled in
    # as needed. Raise exceptions if the arguments don't make sense.
    L = preprocess_tensors(L)
    v = preprocess_indices(v)
    order = preprocess_forder_order(order, v, "order")
    forder = preprocess_forder_order(forder, v, "forder")

    if check_indices:
        # Raise a RuntimeError if the indices are wrong.
        do_check_indices(L, v, order, forder)

    # If the graph is disconnected, connect it with trivial indices that will
    # be contracted at the very end.
    connect_graph(L, v, order)

    while len(order) > 0:
        tcon = get_tcon(v, order[0])  # tcon = tensors to be contracted
        # Find the indices icon that are to be contracted.
        if len(tcon) == 1:
            tracing = True
            icon = [order[0]]
        else:
            tracing = False
            icon = get_icon(v, tcon)
        # Position in tcon[0] and tcon[1] of indices to be contracted.
        # In the case of trace, pos2 = []
        pos1, pos2 = get_pos(v, tcon, icon)
        if tracing:
            # Trace on a tensor
            new_A = trace(L[tcon[0]], axis1=pos1[0], axis2=pos1[1])
        else:
            # Contraction of 2 tensors
            new_A = con(L[tcon[0]], L[tcon[1]], (pos1, pos2))
        L.append(new_A)
        v.append(find_newv(v, tcon, icon))  # Add the v for the new tensor
        for i in sorted(tcon, reverse=True):
            # Delete the contracted tensors and indices from the lists.
            # tcon is reverse sorted so that tensors are removed starting from
            # the end of L, otherwise the order would get messed.
            del L[i]
            del v[i]
        order = renew_order(order, icon)  # Update order

    vlast = v[0]
    A = L[0]
    A = permute_final(A, vlast, forder)
    return A


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


def is_non_string_iterable(x):
    """Return True if x is an iterable but not a string, otherwise False."""
    return isinstance(x, Iterable) and not isinstance(x, str)


def indices_are_ints(v):
    """Return True if all indices are integers, False otherwise."""
    for lst in v:
        for element in lst:
            if not isinstance(element, int):
                return False
    return True


def preprocess_tensors(L):
    """Prepare the tensors argument into a canonical form.

    We want to handle the tensors as a list, regardless of what kind of
    iterable we are given. In addition, if only a single element is given, we
    make list out of it.
    """
    if hasattr(L, "shape"):
        L = [L]
    else:
        L = list(L)
    return L


def preprocess_indices(v):
    """Prepare the indices argument into a canonical form.

    We want to handle the indices as a nested list of lists.
    """
    if not is_non_string_iterable(v):
        raise ValueError("v must be a non-string Iterable.")
    v = list(v)
    if not is_non_string_iterable(v[0]):
        # v is not a list of lists, so make it such.
        v = [v]
    else:
        v = list(map(list, v))
    return v


def preprocess_forder_order(arg, v, name):
    """Prepare the order and forder arguments.

    Make sure they are both lists, and supply default values if appropriate.
    """
    int_indices = indices_are_ints(v)
    if arg is None:
        if not int_indices:
            msg = f"If non-int indices are used, {name} must be specified."
            raise ValueError(msg)
        default_creator = (
            create_order
            if name == "order"
            else create_forder
            if name == "forder"
            else None
        )
        arg = default_creator(v)
    else:
        if not is_non_string_iterable(arg):
            msg = f"If {name} is provided, it must be a non-string iterable."
            raise ValueError(msg)
        arg = list(arg)
    return arg


def create_order(v):
    """Identify all unique, positive indices and return them sorted."""
    flat_v = sum(v, [])
    x = [i for i in flat_v if i > 0]
    # Converting to a set and back removes duplicates
    x = list(set(x))
    return sorted(x)


def create_forder(v):
    """Identify all unique, negative indices and return them reverse sorted
    (-1 first).
    """
    flat_v = sum(v, [])
    x = [i for i in flat_v if i < 0]
    # Converting to a set and back removes duplicates
    x = list(set(x))
    return sorted(x, reverse=True)


def connect_graph(L, v, order):
    """Connect the graph of tensors to be contracted by trivial indices, if
    necessary. Add these trivial indices to the end of the contraction order.

    L, v and order are modified in place.
    """
    # Build ccomponents, a list of the connected components of the graph,
    # where each component is represented by a a set of indices.
    unvisited = set(range(len(L)))
    visited = set()
    ccomponents = []
    while unvisited:
        component = set()
        next_visit = unvisited.pop()
        to_visit = {next_visit}
        while to_visit:
            i = to_visit.pop()
            unvisited.discard(i)
            component.add(i)
            visited.add(i)
            # Get the indices of tensors neighbouring L[i].
            i_inds = set(v[i])
            neighs = (
                j for j, j_inds in enumerate(v) if i_inds.intersection(j_inds)
            )
            for neigh in neighs:
                if neigh not in visited:
                    to_visit.add(neigh)
        ccomponents.append(component)
    # If there is more than one connected component, take one of them, a take
    # an arbitrary tensor (called c) out of it, and connect that tensor with an
    # arbitrary tensor (called d) from all the other components using a trivial
    # index.
    c = ccomponents.pop().pop()
    while ccomponents:
        d = ccomponents.pop().pop()
        A_c = L[c]
        A_d = L[d]
        c_axis = len(v[c])
        d_axis = len(v[d])
        L[c] = expand_dims(A_c, c_axis)
        L[d] = expand_dims(A_d, d_axis)

        dim_num = 1
        while dim_num in order:
            dim_num += 1
        v[c].append(dim_num)
        v[d].append(dim_num)
        order.append(dim_num)
    return None

def get_tcon(v, index):
    """Gets the list indices in L of the tensors that have index as their
    leg.
    """
    tcon = []
    for i, inds in enumerate(v):
        if index in inds:
            tcon.append(i)
    l = len(tcon)
    # If check_indices is called and it does its work properly then these
    # checks should in fact be unnecessary.
    if l > 2:
        raise ValueError(
            "In ncon.get_tcon, more than two tensors share a contraction "
            "index."
        )
    elif l < 1:
        raise ValueError(
            "In ncon.get_tcon, less than one tensor share a contraction index."
        )
    elif l == 1:
        # The contraction is a trace.
        how_many = v[tcon[0]].count(index)
        if how_many != 2:
            # Only one tensor has this index but it is not a trace because it
            # does not occur twice for that tensor.
            raise ValueError(
                "In ncon.get_tcon, a trace index is listed != 2 times for the "
                "same tensor."
            )
    return tcon


def get_icon(v, tcon):
    """Returns a list of indices that are to be contracted when contractions
    between the two tensors numbered in tcon are contracted.
    """
    inds1 = v[tcon[0]]
    inds2 = v[tcon[1]]
    icon = set(inds1).intersection(inds2)
    icon = list(icon)
    return icon


def get_pos(v, tcon, icon):
    """Get the positions of the indices icon in the list of legs the tensors
    tcon to be contracted.
    """
    pos1 = [[i for i, x in enumerate(v[tcon[0]]) if x == e] for e in icon]
    pos1 = sum(pos1, [])
    if len(tcon) < 2:
        pos2 = []
    else:
        pos2 = [[i for i, x in enumerate(v[tcon[1]]) if x == e] for e in icon]
        pos2 = sum(pos2, [])
    return pos1, pos2


def find_newv(v, tcon, icon):
    """Find the list of indices for the new tensor after contraction of
    indices icon of the tensors tcon.
    """
    if len(tcon) == 2:
        newv = v[tcon[0]] + v[tcon[1]]
    else:
        newv = v[tcon[0]]
    newv = [i for i in newv if i not in icon]
    return newv


def renew_order(order, icon):
    """Returns the new order with the contracted indices removed from it."""
    return [i for i in order if i not in icon]


def permute_final(A, v, forder):
    perm = [v.index(i) for i in forder]
    return permute(A, perm)  # delegate to backend


def do_check_indices(L, v, order, forder):
    """Check that
    1) the number of tensors in L matches the number of index lists in v.
    2) every tensor is given the right number of indices.
    3) every contracted index is featured exactly twice and every free index
       exactly once.
    4) the dimensions of the two ends of each contracted index match.
    """

    # 1)
    if len(L) != len(v):
        raise ValueError(
            (
                "In ncon.do_check_indices, the number of tensors %i"
                " does not match the number of index lists %i"
            )
            % (len(L), len(v))
        )

    # 2)
    # Create a list of lists with the shapes of each A in L.
    shapes = list(map(lambda A: list(A.shape), L))
    for i, inds in enumerate(v):
        if len(inds) != len(shapes[i]):
            raise ValueError(
                (
                    "In ncon.do_check_indices, len(v[%i])=%i does not match "
                    "the numbers of indices of L[%i] = %i"
                )
                % (i, len(inds), i, len(shapes[i]))
            )

    # 3) and 4)
    # v_pairs = [[(0,0), (0,1), (0,2), ...], [(1,0), (1,1), (1,2), ...], ...]
    v_pairs = [[(i, j) for j in range(len(s))] for i, s in enumerate(v)]
    v_pairs = sum(v_pairs, [])
    v_sum = sum(v, [])
    # For t, o in zip(v_pairs, v_sum) t is the tuple of the number of
    # the tensor and the index and o is the contraction order of that
    # index. We group these tuples by the contraction order.
    order_groups = [
        [t for t, o in zip(v_pairs, v_sum) if o == e] for e in order
    ]
    forder_groups = [[1 for fo in v_sum if fo == e] for e in forder]
    for i, o in enumerate(order_groups):
        if len(o) != 2:
            raise ValueError(
                (
                    "In ncon.do_check_indices, the contracted index %i is not "
                    "featured exactly twice in v."
                )
                % order[i]
            )
        else:
            A0, ind0 = o[0]
            A1, ind1 = o[1]
            try:
                compatible = L[A0].compatible_indices(L[A1], ind0, ind1)
            except AttributeError:
                compatible = L[A0].shape[ind0] == L[A1].shape[ind1]
            if not compatible:
                raise ValueError(
                    "In ncon.do_check_indices, for the contraction index %i, "
                    "the leg %i of tensor number %i and the leg %i of tensor "
                    "number %i are not compatible."
                    % (order[i], ind0, A0, ind1, A1)
                )
    for i, fo in enumerate(forder_groups):
        if len(fo) != 1:
            raise ValueError(
                (
                    "In ncon.do_check_indices, the free index %i is not "
                    "featured exactly once in v."
                )
                % forder[i]
            )

    # All is well if we made it here.
    return True