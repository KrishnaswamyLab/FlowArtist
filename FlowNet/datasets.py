# AUTOGENERATED! DO NOT EDIT! File to edit: 01c Plotting Utils.ipynb (unless otherwise specified).

__all__ = ['EmailEuNetwork', 'SourceSink', 'SmallRandom', 'DirectedStochasticBlockModel', 'source_graph', 'sink_graph',
           'ChainGraph', 'ChainGraph2', 'ChainGraph3', 'CycleGraph', 'HalfCycleGraph', 'xy_tilt', 'add_noise',
           'directed_circle', 'directed_spiral', 'directed_spiral_uniform', 'directed_spiral_sklearn', 'generate_prism',
           'directed_cylinder', 'directed_swiss_roll', 'directed_swiss_roll_uniform', 'directed_swiss_roll_sklearn',
           'add_labels', 'pancreas_rnavelo_load_data', 'pancreas_rnavelo', 'pancreas_rnavelo_pcs',
           'd_rnavelo_load_data', 'd_rnavelo', 'd_rnavelo_pcs', 'plot_directed_2d', 'plot_origin_3d',
           'plot_directed_3d', 'plot_3d', 'visualize_graph', 'visualize_heatmap']

# Cell
import os
import torch
from torch_geometric.data import Data, InMemoryDataset, download_url, extract_gz
from torch_geometric.utils import sort_edge_index


class EmailEuNetwork(InMemoryDataset):
    """ "
    email-Eu-core network from Stanford Large Network Dataset Collection

    The network was generated from the email exchanges within a large European research institution.
    Each node represents an individual, and a directional edge from one individual to another represents some email exchanges between them in the specified direction.
    Each individual belongs to exactly one of 42 departments in the institution.
    """

    def __init__(self, transform=None, pre_transform=None):
        super().__init__("./datasets/email_Eu_network", transform, pre_transform)
        self.data, self.slices = torch.load(self.processed_paths[0])

    @property
    def raw_file_names(self):
        return ["email-Eu-core.txt", "email-Eu-core-department-labels.txt"]

    @property
    def processed_file_names(self):
        pre_transformed = "" if self.pre_transform is None else "_pre-transformed"
        return [f"email-Eu-network{pre_transformed}.pt", "never-skip-processing"]

    def download(self):
        for filename in self.raw_file_names:
            download_url(f"https://snap.stanford.edu/data/{filename}.gz", self.raw_dir)
            extract_gz(f"{self.raw_dir}/{filename}.gz", self.processed_dir)
            os.remove(f"{self.raw_dir}/{filename}.gz")

    def process(self):
        # Graph connectivity
        with open(self.raw_paths[0], "r") as f:
            edge_array = [
                [int(x) for x in line.split()] for line in f.read().splitlines()
            ]
        edge_index = torch.t(torch.tensor(edge_array))
        edge_index = sort_edge_index(edge_index)
        # Ground-truth label
        with open(self.raw_paths[1], "r") as f:
            label_array = [
                [int(x) for x in line.split()] for line in f.read().splitlines()
            ]
        y = torch.tensor(label_array)
        # Node identity features
        x = torch.eye(y.size(0), dtype=torch.float)
        # Build and save data
        data = Data(x=x, edge_index=edge_index, y=y)
        if self.pre_transform is not None:
            data = self.pre_transform(data)
        self.data, self.slices = self.collate([data])
        torch.save((self.data, self.slices), self.processed_paths[0])

# Cell
import warnings
from torch_geometric.transforms import BaseTransform
from torch_geometric.utils import sort_edge_index


class SourceSink(BaseTransform):
    """
    Transform a (directed or undirected) graph into a directed graph
    with a proportion of the nodes with mostly out-edges
    and a porportion of the nodes with mostly in-edges

    Parameters
    ----------
    prob_source : float
        must be between 0 and 1
        Proportion of nodes/communities to turn into source nodes/communities
        (with mostly out-edges)
    prob_sink : float
        must be between 0 and 1
        prob_source and prob_sink must add up to no more than 1
        Proportion of nodes/communities to turn into sink nodes/communities
        (with mostly in-edges)
    adv_prob : float
        must be between 0 and 1
        Probability of in-edges for source nodes and/or out-edges for sink nodes
    remove_prob : float
        must be between 0 and 1
        Probability of removing an in-edge for source nodes and/or out-edges for sink nodes
        1 - remove_prob is the probability of reversing the direction of in-edge for source nodes and/or out-edges for sink nodes
    """

    def __init__(self, prob_source=0.1, prob_sink=0.1, adv_prob=0, remove_prob=0):
        if prob_source + prob_sink > 1:
            warnings.warn("Total probability of source and sink exceeds 1")
            excess = prob_source + prob_sink - 1
            prob_source -= excess / 2
            prob_sink -= excess / 2
            warnings.warn(
                f"Adjusted: prob_source = {prob_source}, prob_sink = {prob_sink}"
            )
        self.prob_source = prob_source
        self.prob_sink = prob_sink
        self.adv_prob = adv_prob
        self.remove_prob = remove_prob

    def _has_ground_truth(self, data):
        return data.y is not None and data.y.shape == (data.num_nodes, 2)

    def _wrong_direction(self, labels, sources, sinks, tail, head):
        return (labels[head] in sources and labels[tail] not in sources) or (
            labels[tail] in sinks and labels[head] not in sinks
        )

    def __call__(self, data):
        if self._has_ground_truth(data):
            # get ground truth labels
            y = data.y[torch.argsort(data.y[:, 0]), :]
            classes = y[:, 1].unique()
            # randomly choose source and sink classes
            mask = torch.rand(len(classes))
            source_classes = classes[mask < self.prob_source]
            sink_classes = classes[mask > 1 - self.prob_sink]
            # add source/sink ground-truth label
            y = torch.hstack(
                (
                    y,
                    torch.t(
                        torch.tensor(
                            [
                                [
                                    1
                                    if c in source_classes
                                    else -1
                                    if c in sink_classes
                                    else 0
                                    for c in y[:, 1]
                                ]
                            ]
                        )
                    ),
                )
            )
            labels = y[:, 1]
            sources = source_classes
            sinks = sink_classes
        else:
            warnings.warn("Data has no ground-truth labels")
            # randomly choose source and sink nodes
            nodes = torch.arange(data.num_nodes)
            mask = torch.rand(data.num_nodes)
            source_nodes = nodes[mask < self.prob_source]
            sink_nodes = nodes[mask > 1 - self.prob_sink]
            # add source/sink ground-truth label
            y = torch.tensor(
                [
                    [n, 1 if n in source_nodes else -1 if n in sink_nodes else 0]
                    for n in nodes
                ]
            )
            labels = nodes
            sources = source_nodes
            sinks = sink_nodes

        # correct improper edges
        edge_array = []
        for e in range(data.num_edges):
            tail, head = data.edge_index[:, e]
            if (
                self._wrong_direction(labels, sources, sinks, tail, head)
                and torch.rand(1)[0] > self.adv_prob
            ):
                if torch.rand(1)[0] < self.remove_prob:  # remove the improper edge
                    continue
                else:  # reverse the improper edge
                    edge_array.append([head, tail])
            else:  # keep proper edge
                edge_array.append([tail, head])
        edge_index = torch.t(torch.tensor(edge_array))
        data.edge_index = sort_edge_index(edge_index)
        data.y = y
        return data.coalesce()

# Cell
import warnings
import torch
from torch_geometric.data import Data, InMemoryDataset
from torch_sparse import SparseTensor
from torch_geometric.utils import remove_self_loops


class SmallRandom(InMemoryDataset):
    def __init__(self, num_nodes=5, prob_edge=0.2, transform=None, pre_transform=None):
        super().__init__(".", transform, pre_transform)

        if num_nodes > 300:
            num_nodes = 300
            warnings.warn(
                f"Number of nodes is too large for SmallRandom dataset. Reset num_nodes =  {num_nodes}"
            )

        dense_adj = (torch.rand((num_nodes, num_nodes)) < prob_edge).int()
        sparse_adj = SparseTensor.from_dense(dense_adj)
        row, col, _ = sparse_adj.coo()
        edge_index, _ = remove_self_loops(torch.stack([row, col]))

        x = torch.eye(num_nodes, dtype=torch.float)
        data = Data(x=x, edge_index=edge_index)
        if self.pre_transform is not None:
            data = self.pre_transform(data)
        self.data, self.slices = self.collate([data])

# Cell
import warnings
import torch
import numpy as np
from torch_geometric.data import Data, InMemoryDataset
from torch_sparse import SparseTensor
from torch_geometric.utils import remove_self_loops


class DirectedStochasticBlockModel(InMemoryDataset):
    def __init__(self, num_nodes, num_clusters, aij, bij, transform=None):
        """Directed SBM

        Parameters
        ----------
        num_nodes : int
            _description_
        num_clusters : int
            must evenly divide num_nodes
        aij : num_nodes x num_nodes ndarray
            Probabilities of (undirected) connection between clusters i and j.
            Must be symmetric.
        bij : num_nodes x num_nodes ndarray
            Probabilities with which the edges made via aij are converted to directed edges.
            bij + bji = 1
        transform : _type_, optional
            _description_, by default None
        """
        super().__init__(".", transform)
        cluster = np.repeat(list(range(num_clusters)), num_nodes / num_clusters)
        # print(cluster)
        rand_matrix = torch.rand((num_nodes, num_nodes))
        dense_adj = torch.empty((num_nodes, num_nodes))
        ## Draw inter-cluster undirected edges
        # inefficiently traverse the dense matrix, converting probabilities
        for i in range(num_nodes):
            for j in range(i, num_nodes):
                # print("cluster of i is",cluster[i],"cluster of j is",cluster[j])
                dense_adj[i, j] = (
                    1 if rand_matrix[i, j] < aij[cluster[i], cluster[j]] else 0
                )
                dense_adj[j, i] = dense_adj[i, j]  # it's symmetric
        ## Convert undirected edges to directed edges
        rand_matrix = torch.rand((num_nodes, num_nodes))
        for i in range(num_nodes):
            for j in range(i, num_nodes):
                # if an edge exists, assign it a direction
                if dense_adj[i, j] == 1:
                    # print('adding direction')
                    if rand_matrix[i, j] < bij[cluster[i], cluster[j]]:
                        dense_adj[i, j] = 1
                        dense_adj[j, i] = 0
                    else:
                        dense_adj[i, j] = 0
                        dense_adj[j, i] = 1
        #
        # print("The adjacency is currently symmetric ",torch.allclose(dense_adj,dense_adj.T))

        sparse_adj = SparseTensor.from_dense(dense_adj)
        row, col, _ = sparse_adj.coo()
        edge_index, _ = remove_self_loops(torch.stack([row, col]))

        x = torch.eye(num_nodes, dtype=torch.float)
        data = Data(x=x, edge_index=edge_index)
        self.data, self.slices = self.collate([data])

# Cell
def source_graph(n_points=700, num_clusters=7):
    # we'll start with 7 clusters; six on the outside, one on the inside
    aij = np.zeros((num_clusters, num_clusters))
    aij[0, :] = 0.9
    aij[:, 0] = 0.9
    np.fill_diagonal(aij, 0.9)
    # aij = np.array(
    #   [[0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9],
    #    [0.9, 0.9, 0, 0, 0, 0, 0],
    #    [0.9, 0, 0.9, 0, 0, 0, 0],
    #    [0.9, 0, 0, 0.9, 0, 0, 0],
    #    [0.9, 0, 0, 0, 0.9, 0, 0],
    #    [0.9, 0, 0, 0, 0, 0.9, 0],
    #    [0.9, 0, 0, 0, 0, 0, 0.9]]
    # )
    bij = np.zeros((num_clusters, num_clusters))
    bij[0, :] = 1.0
    bij[:, 0] = 0.0
    np.fill_diagonal(bij, 0.5)
    # bij = np.array(
    #   [[0.5, 1, 1, 1, 1, 1, 1],
    #    [0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    #    [0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    #    [0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    #    [0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    #    [0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    #    [0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]]
    # )
    dataset = DirectedStochasticBlockModel(
        num_nodes=n_points, num_clusters=num_clusters, aij=aij, bij=bij
    )
    return dataset

# Cell
def sink_graph(n_points=700, num_clusters=7):
    # we'll start with 7 clusters; six on the outside, one on the inside
    aij = np.zeros((num_clusters, num_clusters))
    aij[0, :] = 0.9
    aij[:, 0] = 0.9
    np.fill_diagonal(aij, 0.9)
    # aij = np.array(
    #   [[0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9],
    #    [0.9, 0.9, 0, 0, 0, 0, 0],
    #    [0.9, 0, 0.9, 0, 0, 0, 0],
    #    [0.9, 0, 0, 0.9, 0, 0, 0],
    #    [0.9, 0, 0, 0, 0.9, 0, 0],
    #    [0.9, 0, 0, 0, 0, 0.9, 0],
    #    [0.9, 0, 0, 0, 0, 0, 0.9]]
    # )
    bij = np.zeros((num_clusters, num_clusters))
    bij[0, :] = 0.0
    bij[:, 0] = 1.0
    np.fill_diagonal(bij, 0.5)
    # bij = np.array(
    #   [[0.5,0, 0, 0, 0, 0, 0],
    #    [1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    #    [1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    #    [1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    #    [1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    #    [1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    #    [1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]]
    # )
    dataset = DirectedStochasticBlockModel(
        num_nodes=n_points, num_clusters=num_clusters, aij=aij, bij=bij
    )
    return dataset

# Cell
class ChainGraph(InMemoryDataset):
    def __init__(self, num_nodes=2, transform=None):
        super().__init__(".", transform)
        dense_adj = torch.tensor([[0, 1], [0, 0]])
        sparse_adj = SparseTensor.from_dense(dense_adj)
        row, col, _ = sparse_adj.coo()
        edge_index, _ = remove_self_loops(torch.stack([row, col]))

        x = torch.eye(num_nodes, dtype=torch.float)
        data = Data(x=x, edge_index=edge_index)
        self.data, self.slices = self.collate([data])

# Cell
class ChainGraph2(InMemoryDataset):
    def __init__(self, num_nodes=3, transform=None):
        super().__init__(".", transform)
        dense_adj = torch.tensor([[0, 1, 0], [0, 0, 1], [0, 0, 0]])
        sparse_adj = SparseTensor.from_dense(dense_adj)
        row, col, _ = sparse_adj.coo()
        edge_index, _ = remove_self_loops(torch.stack([row, col]))

        x = torch.eye(num_nodes, dtype=torch.float)
        data = Data(x=x, edge_index=edge_index)
        self.data, self.slices = self.collate([data])

# Cell
class ChainGraph3(InMemoryDataset):
    def __init__(self, num_nodes=3, transform=None):
        super().__init__(".", transform)
        dense_adj = torch.tensor([[0, 1, 0], [0, 0, 0], [0, 1, 0]])
        sparse_adj = SparseTensor.from_dense(dense_adj)
        row, col, _ = sparse_adj.coo()
        edge_index, _ = remove_self_loops(torch.stack([row, col]))

        x = torch.eye(num_nodes, dtype=torch.float)
        data = Data(x=x, edge_index=edge_index)
        self.data, self.slices = self.collate([data])

# Cell
class CycleGraph(InMemoryDataset):
    def __init__(self, num_nodes=3, transform=None):
        super().__init__(".", transform)
        dense_adj = torch.tensor([[0, 1, 0], [0, 0, 1], [1, 0, 0]])
        sparse_adj = SparseTensor.from_dense(dense_adj)
        row, col, _ = sparse_adj.coo()
        edge_index, _ = remove_self_loops(torch.stack([row, col]))

        x = torch.eye(num_nodes, dtype=torch.float)
        data = Data(x=x, edge_index=edge_index)
        self.data, self.slices = self.collate([data])

# Cell
class HalfCycleGraph(InMemoryDataset):
    def __init__(self, num_nodes=3, transform=None):
        super().__init__(".", transform)
        dense_adj = torch.tensor([[0, 1, 0], [1, 0, 1], [1, 0, 0]])
        sparse_adj = SparseTensor.from_dense(dense_adj)
        row, col, _ = sparse_adj.coo()
        edge_index, _ = remove_self_loops(torch.stack([row, col]))

        x = torch.eye(num_nodes, dtype=torch.float)
        data = Data(x=x, edge_index=edge_index)
        self.data, self.slices = self.collate([data])

# Cell
# Tilt 2d plane into 3d space
import numpy as np
def xy_tilt(X, flows, xtilt=0, ytilt=0):
    xrotate = np.array([[1,              0,             0],
                        [0,  np.cos(xtilt), np.sin(xtilt)],
                        [0, -np.sin(xtilt), np.cos(xtilt)]])
    yrotate = np.array([[np.cos(ytilt), 0, -np.sin(ytilt)],
                        [            0, 1,              0],
                        [np.sin(ytilt), 0,  np.cos(ytilt)]])
    X = X @ xrotate @ yrotate
    flows = flows @ xrotate @ yrotate
    return X, flows

# Cell
def add_noise(X, sigma=0):
    return X + np.random.normal(0, sigma, X.shape)

# Cell
def directed_circle(num_nodes=500, radius=1, xtilt=0, ytilt=0, sigma=0, inverse=False):
    # sample random angles between 0 and 2pi
    thetas = np.random.uniform(0, 2*np.pi, num_nodes)
    thetas = np.sort(thetas)
    labels = thetas
    # calculate x and y coordinates
    x = np.cos(thetas) * radius
    y = np.sin(thetas) * radius
    z = np.zeros(num_nodes)
    X = np.column_stack((x, y, z))
    # calculate the angle of the tangent
    alphas = thetas + np.pi/2
    # calculate the coordinates of the tangent
    u = np.cos(alphas)
    v = np.sin(alphas)
    w = np.zeros(num_nodes)
    flows = np.column_stack((u, v, w))
    flows = -flows if inverse else flows
    # tilt and add noise
    X, flows = xy_tilt(X, flows, xtilt, ytilt)
    X = add_noise(X, sigma)
    return X, flows, labels

# Cell
def directed_spiral(num_nodes=500, num_spirals=1.5, radius=1, xtilt=0, ytilt=0, sigma=0, inverse=False):
    # sample random angles between 0 and num_spirals * 2pi
    thetas = np.random.uniform(0, num_spirals*2*np.pi, num_nodes)
    thetas = np.sort(thetas)
    labels = thetas
    # calculate x and y coordinates
    x = np.cos(thetas) * thetas * radius
    y = np.sin(thetas) * thetas * radius
    z = np.zeros(num_nodes)
    X = np.column_stack((x, y, z))
    # calculate the angle of the tangent
    alphas = thetas + np.pi/2
    # calculate the coordinates of the tangent
    u = np.cos(alphas) * thetas
    v = np.sin(alphas) * thetas
    w = np.zeros(num_nodes)
    flows = np.column_stack((u, v, w))
    flows = -flows if inverse else flows
    # tilt and add noise
    X, flows = xy_tilt(X, flows, xtilt, ytilt)
    X = add_noise(X, sigma)
    return X, flows, labels

# Cell
def directed_spiral_uniform(num_nodes=500, num_spirals=1.5, radius=1, xtilt=0, ytilt=0, sigma=0, inverse=False):
    # sample random angles between 0 and num_spirals * 2pi
    t1 = np.random.uniform(0, num_spirals*2*np.pi, num_nodes)
    t2 = np.random.uniform(0, num_spirals*2*np.pi, num_nodes)
    thetas = np.maximum(t1, t2)
    thetas = np.sort(thetas)
    labels = thetas
    # calculate x and y coordinates
    x = np.cos(thetas) * thetas * radius
    y = np.sin(thetas) * thetas * radius
    z = np.zeros(num_nodes)
    X = np.column_stack((x, y, z))
    # calculate the angle of the tangent
    alphas = thetas + np.pi/2
    # calculate the coordinates of the tangent
    u = np.cos(alphas)
    v = np.sin(alphas)
    w = np.zeros(num_nodes)
    flows = np.column_stack((u, v, w))
    flows = -flows if inverse else flows
    # tilt and add noise
    X, flows = xy_tilt(X, flows, xtilt, ytilt)
    X = add_noise(X, sigma)
    return X, flows, labels

# Cell
def directed_spiral_delayed(num_nodes=500, num_spirals=1.5, radius=1, xtilt=0, ytilt=0, sigma=0, inverse=False):
    # sample random angles between 0 and num_spirals * 2pi
    thetas = np.random.uniform(num_spirals*np.pi, num_spirals*3*np.pi, num_nodes)
    thetas = np.sort(thetas)
    labels = thetas
    # calculate x and y coordinates
    x = np.cos(thetas) * thetas * radius
    y = np.sin(thetas) * thetas * radius
    z = np.zeros(num_nodes)
    X = np.column_stack((x, y, z))
    # calculate the angle of the tangent
    alphas = thetas + np.pi/2
    # calculate the coordinates of the tangent
    u = np.cos(alphas) * thetas
    v = np.sin(alphas) * thetas
    w = np.zeros(num_nodes)
    flows = np.column_stack((u, v, w))
    flows = -flows if inverse else flows
    # tilt and add noise
    X, flows = xy_tilt(X, flows, xtilt, ytilt)
    X = add_noise(X, sigma)
    return X, flows, labels

# Cell
def generate_prism(num_nodes, X, height=20):
    z_noise = np.random.uniform(-height/2, height/2, num_nodes)
    X[:,2] = X[:,2] + z_noise
    return X

# Cell
def directed_cylinder(num_nodes=1000, radius=1, height=20, xtilt=0, ytilt=0, sigma=0, inverse=False):
    X, flows, labels = directed_circle(num_nodes, radius, xtilt, ytilt, sigma, inverse)
    X = generate_prism(num_nodes, X, height)
    return X, flows, labels

# Cell
def directed_swiss_roll(num_nodes=1000, num_spirals=1.5, height=20, radius=1, xtilt=0, ytilt=0, sigma=0, inverse=False):
    X, flows, labels = directed_spiral(num_nodes, num_spirals, radius, xtilt, ytilt, sigma, inverse)
    X = generate_prism(num_nodes, X, height)
    return X, flows, labels

# Cell
def directed_swiss_roll_uniform(num_nodes=1000, num_spirals=1.5, height=20, radius=1, xtilt=0, ytilt=0, sigma=0, inverse=False):
    X, flows, labels = directed_spiral_uniform(num_nodes, num_spirals, radius, xtilt, ytilt, sigma, inverse)
    X = generate_prism(num_nodes, X, height)
    return X, flows, labels

# Cell
def directed_swiss_roll_delayed(num_nodes=1000, num_spirals=1.5, height=20, radius=1, xtilt=0, ytilt=0, sigma=0, inverse=False):
    X, flows, labels = directed_spiral_delayed(num_nodes, num_spirals, radius, xtilt, ytilt, sigma, inverse)
    X = generate_prism(num_nodes, X, height)
    return X, flows, labels

# Cell
def directed_one_variable_function(func, deriv, xlow, xhigh, num_nodes=100, xtilt=0, ytilt=0, sigma=0, inverse=False):
    # positions
    x = np.random.uniform(xlow, xhigh, num_nodes)
    x = np.sort(x)
    y = func(x)
    z = np.zeros(num_nodes)
    X = np.column_stack((x, y, z))
    labels = x
    # vectors
    u = np.ones(num_nodes)
    v = deriv(x)
    w = np.zeros(num_nodes)
    flows = np.column_stack((u, v, w))
    flows = -flows if inverse else flows
    # tilt and add noise
    X, flows = xy_tilt(X, flows, xtilt, ytilt)
    X = add_noise(X, sigma)
    return X, flows, labels

# Cell
def directed_sine(num_nodes=500, xscale=1, yscale=1, xlow=-2*np.pi, xhigh=2*np.pi, xtilt=0, ytilt=0, sigma=0, inverse=False):
    X, flows, labels = directed_one_variable_function(
        lambda x: np.sin(x / xscale) * yscale,
        lambda x: np.cos(x / xscale) / xscale * yscale,
        xlow, xhigh,
        num_nodes, xtilt, ytilt, sigma, inverse
    )
    return X, flows, labels

# Cell
def directed_sine_ribbon(num_nodes=1000, xscale=1, yscale=1, xlow=-2*np.pi, xhigh=2*np.pi, height=20, xtilt=0, ytilt=0, sigma=0, inverse=False):
    X, flows, labels = directed_sine(num_nodes, xscale, yscale, xlow, xhigh, xtilt, ytilt, sigma, inverse)
    X = generate_prism(num_nodes, X, height)
    return X, flows, labels

# Cell
def directed_sinh(num_nodes=500, xscale=1, yscale=1, xlow=-2*np.pi, xhigh=2*np.pi, xtilt=0, ytilt=0, sigma=0, inverse=False):
    X, flows, labels = directed_one_variable_function(
        lambda x: np.sinh(x / xscale) * yscale,
        lambda x: np.cosh(x / xscale) / xscale * yscale,
        xlow, xhigh,
        num_nodes, xtilt, ytilt, sigma, inverse
    )
    return X, flows, labels

# Cell
def directed_sinh_branch(num_nodes=1000, xscale=1, yscale=1, xtilt=0, ytilt=0, sigma=0, inverse=False):
    num_nodes_per_branch = num_nodes//3
    X_root, flows_root, labels_root = directed_sinh(num_nodes-2*num_nodes_per_branch, xscale, yscale, -xscale*np.pi*0.84, 0, xtilt, ytilt, sigma, inverse)
    X_branch1, flows_branch1, labels_branch1 = directed_sinh(num_nodes_per_branch, xscale, yscale, 0, xscale*np.pi*0.84, xtilt, ytilt, sigma, inverse)
    X_branch2, flows_branch2, labels_branch2 = directed_sine(num_nodes_per_branch, xscale, yscale, 0, xscale*np.pi*2, xtilt, ytilt, sigma, inverse)
    # concatenate
    X = np.concatenate((X_root, X_branch1, X_branch2))
    flows = np.concatenate((flows_root, flows_branch1, flows_branch2))
    labels = np.concatenate((labels_root - np.pi*3, labels_branch1, labels_branch2 + np.pi*3))
    return X, flows, labels


# Cell
def directed_sine_moons(num_nodes=500, xscale=0.5, yscale=1, xtilt=0, ytilt=0, sigma=0, inverse=False):
    num_nodes_per_moon = num_nodes // 2
    X_moon1, flows_moon1, labels_moon1 = directed_sine(num_nodes_per_moon, xscale, yscale, 0, xscale*np.pi, xtilt, ytilt, sigma, inverse)
    X_moon2, flows_moon2, labels_moon2 = X, flows, labels = directed_one_variable_function(
        lambda x: np.cos(x / xscale) * yscale + 0.3,
        lambda x: -np.sin(x / xscale) / xscale * yscale,
        xscale*np.pi/2, xscale*np.pi*3/2,
        num_nodes_per_moon, xtilt, ytilt, sigma, inverse
    )
    # concatenate
    X = np.concatenate((X_moon1, X_moon2))
    flows = np.concatenate((flows_moon1, flows_moon2))
    labels = np.concatenate((labels_moon1 - np.pi, labels_moon2))
    return X, flows, labels

# Cell
def angle_x(X):
    """Returns angle in [0, 2pi] corresponding to each point X"""
    X_complex = X[:,0] + np.array([1j])*X[:,1]
    return np.angle(X_complex)

# Cell
def whirlpool(X):
    """Generates a whirlpool for flow assignment. Works in both 2d and 3d space.

    Parameters
    ----------
    X : ndarray
        input data, 2d or 3d
    """
    # convert X into angles theta, where 0,0 is 0, and 0,1 is pi/2
    X_angles = angle_x(X)
    # create flows
    flow_x = np.sin(2*np.pi - X_angles)
    flow_y = np.cos(2*np.pi - X_angles)
    output = np.column_stack([flow_x,flow_y])
    if X.shape[1] == 3:
        # data is 3d
        flow_z = np.zeros(X.shape[0])
        output = np.column_stack([output,flow_z])
    return output

# Cell
def rejection_sample_for_torus(n, r, R):
    # Rejection sampling torus method [Sampling from a torus (Revolutions)](https://blog.revolutionanalytics.com/2014/02/sampling-from-a-torus.html)
    xvec = np.random.random(n) * 2 * np.pi
    yvec = np.random.random(n) * (1/np.pi)
    fx = (1 + (r/R)*np.cos(xvec)) / (2*np.pi)
    return xvec[yvec < fx]

def directed_torus(n=2000, c=2, a=1, flow_type = 'whirlpool', noise=None, seed=None, use_guide_points = False):
    """
    Sample `n` data points on a torus. Modified from [tadasets.shapes — TaDAsets 0.1.0 documentation](https://tadasets.scikit-tda.org/en/latest/_modules/tadasets/shapes.html#torus)
    Uses rejection sampling.

    In addition to the points, returns a "flow" vector at each point.

    Parameters
    -----------
    n : int
        Number of data points in shape.
    c : float
        Distance from center to center of tube.
    a : float
        Radius of tube.
    flow_type, in ['whirlpool']

    ambient : int, default=None
        Embed the torus into a space with ambient dimension equal to `ambient`. The torus is randomly rotated in this high dimensional space.
    seed : int, default=None
        Seed for random state.
    """

    assert a <= c, "That's not a torus"

    np.random.seed(seed)
    theta = rejection_sample_for_torus(n-2, a, c)
    phi = np.random.random((len(theta))) * 2.0 * np.pi

    X = np.zeros((len(theta), 3))
    X[:, 0] = (c + a * np.cos(theta)) * np.cos(phi)
    X[:, 1] = (c + a * np.cos(theta)) * np.sin(phi)
    X[:, 2] = a * np.sin(theta)

    if use_guide_points:
        X = np.vstack([[[0,-c-a,0],[0,c-a,0],[0,c,a]],X])

    if noise:
        X += noise * np.random.randn(*X.shape)

    if flow_type == 'whirlpool':
        flows = whirlpool(X)
    else:
        raise NotImplementedError

    return X, flows, phi

# Cell
import tadasets
def directed_sphere(n=2000, r=1, flow_type = 'whirlpool', noise=None):
    X = tadasets.sphere(n, r, noise)
    labels = angle_x(X)
    if flow_type == 'whirlpool':
        flows = whirlpool(X)
    else:
        raise NotImplementedError
    return X, flows, labels

# Cell

import scvelo as scv
import numpy as np

def add_labels(clusters):
    cluster_set = set(clusters)
    d = {cluster: i for i, cluster in enumerate(cluster_set)}
    labels = np.array([d[cluster] for cluster in clusters])
    return labels

def pancreas_rnavelo_load_data():
    # load data
    adata = scv.datasets.pancreas()

    #preprocess data and calculate rna velocity
    scv.pp.filter_and_normalize(adata)
    scv.pp.moments(adata)
    scv.tl.velocity(adata, mode='stochastic')

    return adata

def pancreas_rnavelo():
    # load preprocessed data
    adata = pancreas_rnavelo_load_data()

    # set datapoints (X) and flows
    X = torch.tensor(adata.X.todense())
    flows = torch.tensor(adata.layers["velocity"])
    labels = add_labels(adata.obs["clusters"])

    return X, flows, labels

def pancreas_rnavelo_pcs():
    adata = pancreas_rnavelo_load_data()

    # calculate velocity pca (50 dimensions) and display pca plot (2 dimensions)
    scv.tl.velocity_graph(adata)
    scv.pl.velocity_embedding_stream(adata, basis='pca')

    X = torch.tensor(adata.obsm["X_pca"])
    flows = torch.tensor(adata.obsm["velocity_pca"])
    labels = add_labels(adata.obs["clusters"])

    return X, flows, labels

# Cell

def d_rnavelo_load_data():
    # load data
    adata = scv.datasets.dentategyrus()

    #preprocess data and calculate rna velocity
    scv.pp.filter_and_normalize(adata)
    scv.pp.moments(adata)
    scv.tl.velocity(adata, mode='stochastic')

    return adata

def d_rnavelo():
    # load preprocessed data
    adata = d_rnavelo_load_data()

    # set datapoints (X) and flows
    X = torch.tensor(adata.X.todense())
    flows = torch.tensor(adata.layers["velocity"])
    labels = add_labels(adata.obs["clusters"])

    return X, flows, labels

def d_rnavelo_pcs():
    adata = d_rnavelo_load_data()

    # calculate velocity pca (50 dimensions) and display pca plot (2 dimensions)
    scv.tl.velocity_graph(adata)
    scv.pl.velocity_embedding_stream(adata, basis='pca')

    X = torch.tensor(adata.obsm["X_pca"])
    flows = torch.tensor(adata.obsm["velocity_pca"])
    labels = add_labels(adata.obs["clusters"])

    return X, flows, labels

# Cell
import matplotlib.pyplot as plt


def plot_directed_2d(X, flows, labels=None, mask_prob=0.5, cmap="viridis", ax=None):
    num_nodes = X.shape[0]
    alpha_points, alpha_arrows = (0.1, 1) if labels is None else (1, 0.1)
    if ax is None:
        fig = plt.figure()
        ax = fig.add_subplot()
    ax.scatter(X[:, 0], X[:, 1], marker=".", c=labels, cmap=cmap, alpha=alpha_points)
    mask = np.random.rand(num_nodes) > mask_prob
    ax.quiver(X[mask, 0], X[mask, 1], flows[mask, 0], flows[mask, 1], alpha=alpha_arrows)
    ax.set_aspect("equal")
    if ax is None:
        plt.show()


# Cell
def plot_origin_3d(ax, xlim, ylim, zlim):
    ax.plot(xlim, [0, 0], [0, 0], color="k", alpha=0.5)
    ax.plot([0, 0], ylim, [0, 0], color="k", alpha=0.5)
    ax.plot([0, 0], [0, 0], zlim, color="k", alpha=0.5)


def plot_directed_3d(X, flow, labels=None, mask_prob=0.5, cmap="viridis", origin=False, ax=None):
    num_nodes = X.shape[0]
    alpha_points, alpha_arrows = (0.1, 1) if labels is None else (1, 0.1)
    mask = np.random.rand(num_nodes) > mask_prob
    if ax is None:
        fig = plt.figure()
        ax = fig.add_subplot(projection="3d")
    if origin:
        plot_origin_3d(
            ax,
            xlim=[X[:, 0].min(), X[:, 0].max()],
            ylim=[X[:, 1].min(), X[:, 1].max()],
            zlim=[X[:, 2].min(), X[:, 2].max()],
        )
    ax.scatter(X[:, 0], X[:, 1], X[:, 2], marker=".", c=labels, cmap=cmap, alpha=alpha_points)
    ax.quiver(
        X[mask, 0],
        X[mask, 1],
        X[mask, 2],
        flow[mask, 0],
        flow[mask, 1],
        flow[mask, 2],
        alpha=alpha_arrows,
        length=0.5,
    )
    if ax is None:
        plt.show()


# Cell
# For plotting 2D and 3D graphs
import plotly.express as px
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def plot_3d(
    X,
    distribution=None,
    title="",
    lim=None,
    use_plotly=False,
    colorbar=False,
    cmap="viridis",
):
    if distribution is None:
        distribution = np.zeros(len(X))
    if lim is None:
        lim = np.max(np.linalg.norm(X, axis=1))
    if use_plotly:
        d = {"x": X[:, 0], "y": X[:, 1], "z": X[:, 2], "colors": distribution}
        df = pd.DataFrame(data=d)
        fig = px.scatter_3d(
            df,
            x="x",
            y="y",
            z="z",
            color="colors",
            title=title,
            range_x=[-lim, lim],
            range_y=[-lim, lim],
            range_z=[-lim, lim],
        )
        fig.show()
    else:
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(111, projection="3d")
        ax.axes.set_xlim3d(left=-lim, right=lim)
        ax.axes.set_ylim3d(bottom=-lim, top=lim)
        ax.axes.set_zlim3d(bottom=-lim, top=lim)
        im = ax.scatter(X[:, 0], X[:, 1], X[:, 2], c=distribution, cmap=cmap)
        ax.set_title(title)
        if colorbar:
            fig.colorbar(im, ax=ax)
        plt.show()


# Cell
import matplotlib.pyplot as plt
def display_flow_galary(func_set, ncol=4):
    nfunc = len(func_set)
    ncol = 4
    nrow = int(np.ceil(nfunc/ncol))
    fig = plt.figure(figsize=(4*ncol, 3*nrow))
    for i, func in enumerate(func_set):
        name, call = func
        ax = fig.add_subplot(nrow, ncol, i+1, projection="3d")
        X, flows, labels = call()
        plot_directed_3d(X, flows, labels, mask_prob=0.5, ax=ax)
        ax.set_title(name, y=1.0)

# Cell
def visualize_edge_index(edge_index, order_ind=None, cmap = "copper", ax=None):
    num_nodes = edge_index.max() + 1
    row, col = edge_index
    dense_adj = np.zeros((num_nodes, num_nodes))
    for r, c in zip(row, col):
        dense_adj[r,c] = 1
    if order_ind is not None:
        dense_adj = dense_adj[order_ind, :][:, order_ind]
    if ax is not None:
        ax.imshow(dense_adj, cmap=cmap)
    else:
        plt.imshow(dense_adj, cmap=cmap)
        plt.show()
