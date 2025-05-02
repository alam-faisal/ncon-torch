# ncon-torch
![PyPI version](https://img.shields.io/pypi/v/qaravan)

ncon-torch is a fork of the ncon package, modified to include GPU and autograd support via PyTorch

## Installation

`pip install ncon-torch`

## Usage

See original package [repo](https://github.com/mhauru/ncon) for examples. 

## Benchmark 

Below we compare NumPy and PyTorch based contractions of a two-qubit gate with an n-qubit state. The benchmark was done on Google Colab with a T4 GPU. 