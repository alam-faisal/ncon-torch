# ncon-torch
![PyPI version](https://img.shields.io/pypi/v/ncon-torch)

ncon-torch is a fork of the ncon package, modified to include GPU and autograd support via PyTorch

## Installation

`pip install ncon-torch`

## Usage

See original package [repo](https://github.com/mhauru/ncon) for examples. 

## GPU Benchmark 

Below we compare NumPy and PyTorch based contractions of a two-qubit gate with an n-qubit state. The benchmark was done on Google Colab with a T4 GPU. 

![Benchmark: NumPy vs PyTorch](gpu_benchmark.png)

## Automatic differentiation 

`ncon-torch` is compatible with PyTorch's reverse-mode automatic differentiation (`autograd`). Any contraction involving tensors with `requires_grad=True` will propagate gradients as expected.

### Minimal Example

```python
import torch
from ncon_torch import ncon

A = torch.randn(2, 2, dtype=torch.float64, requires_grad=True)
B = torch.tensor([[1.0, 0.0], [0.0, -1.0]], dtype=torch.float64)

out = ncon([A, B], [[1, -1], [1, -2]])
loss = torch.sum(out**2)
loss.backward()

print("Gradient:", A.grad) 
```

To validate the efficiency of reverse-mode AD, we benchmarked the time to compute:
* The cost function (a scalar-valued tensor contraction)
* Gradients via reverse-mode AD (.backward())
* Gradients via finite-difference approximation (scipy.optimize.approx_fprime)

Despite increasing parameter count, reverse-mode AD maintains near-constant overhead relative to the forward cost, unlike finite differences which scale poorly.

![Benchmark: reverse mode AD vs finite differences](ad_benchmark.png)