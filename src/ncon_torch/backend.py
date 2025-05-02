import numpy as np
import torch

def is_tensor(x):
    return torch.is_tensor(x)

def expand_dims(A, axis):
    if is_tensor(A):
        return A.unsqueeze(axis)
    elif isinstance(A, np.ndarray):
        return np.expand_dims(A, axis)
    else:
        raise TypeError(f"expand_dims: unsupported type {type(A)}")

def permute(A, perm):
    if is_tensor(A):
        return A.permute(*perm)
    elif isinstance(A, np.ndarray):
        return np.transpose(A, perm)
    else:
        raise TypeError("permute: unsupported tensor type")

def trace(A, axis1, axis2):
    return torch.trace(A.transpose(axis1, axis2).contiguous()) if is_tensor(A) else A.trace(axis1=axis1, axis2=axis2)

def con(A, B, inds):
    if is_tensor(A) and is_tensor(B):
        return torch.tensordot(A, B, dims=inds)
    elif isinstance(A, np.ndarray) and isinstance(B, np.ndarray):
        return np.tensordot(A, B, inds)
    else:
        raise TypeError("con: both inputs must be either PyTorch tensors or NumPy arrays")