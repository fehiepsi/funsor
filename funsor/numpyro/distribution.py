# Copyright Contributors to the Pyro project.
# SPDX-License-Identifier: Apache-2.0

from collections import OrderedDict

import numpyro.distributions as dist

from funsor.cnf import Contraction
from funsor.delta import Delta
from funsor.domains import bint
from funsor.numpyro.convert import DIM_TO_NAME, funsor_to_tensor, tensor_to_funsor
from funsor.terms import Funsor, to_funsor


class FunsorDistribution(dist.Distribution):
    # TODO: add docs
    """
    Like funsor.pyro.distribution.FunsorDistribution.
    """
    arg_constraints = {}

    def __init__(self, funsor_dist, batch_shape=(), event_shape=(),
                 dtype="real", validate_args=None):
        assert isinstance(funsor_dist, Funsor)
        assert isinstance(batch_shape, tuple)
        assert isinstance(event_shape, tuple)
        assert "value" in funsor_dist.inputs
        super(FunsorDistribution, self).__init__(batch_shape, event_shape, validate_args)
        self.funsor_dist = funsor_dist
        self.dtype = dtype

    @property
    def support(self):
        if self.dtype == "real":
            return dist.constraints.real
        else:
            return dist.constraints.integer_interval(0, self.dtype - 1)

    def log_prob(self, value):
        ndims = max(len(self.batch_shape), value.dim() - self.event_dim)
        value = tensor_to_funsor(value, event_output=self.event_dim, dtype=self.dtype)
        log_prob = self.funsor_dist(value=value)
        log_prob = funsor_to_tensor(log_prob, ndims=ndims)
        return log_prob

    def _sample_delta(self, key, sample_shape):
        sample_inputs = None
        if sample_shape:
            sample_inputs = OrderedDict()
            shape = sample_shape + self.batch_shape
            for dim in range(-len(shape), -len(self.batch_shape)):
                if shape[dim] > 1:
                    sample_inputs[DIM_TO_NAME[dim]] = bint(shape[dim])
        delta = self.funsor_dist.sample(frozenset({"value"}), sample_inputs, rng_key=key)
        if isinstance(delta, Contraction):
            assert len([d for d in delta.terms if isinstance(d, Delta)]) == 1
            delta = delta.terms[0]
        assert isinstance(delta, Delta)
        return delta

    def sample(self, key, sample_shape=()):
        delta = self._sample_delta(key, sample_shape)
        ndims = len(sample_shape) + len(self.batch_shape) + len(self.event_shape)
        value = funsor_to_tensor(delta.terms[0][1][0], ndims=ndims)
        return value


@to_funsor.register(FunsorDistribution)
def funsordistribution_to_funsor(pyro_dist, output=None, dim_to_name=None):
    raise NotImplementedError("TODO implement conversion for FunsorDistribution")
